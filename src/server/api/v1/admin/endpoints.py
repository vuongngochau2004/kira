"""Admin monitoring endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.config import settings
from src.shared.infrastructure.auth.dependencies import require_admin
from src.shared.infrastructure.persistence.database.models import (
    Conversation,
    Document,
    DocumentDeletionJob,
    Message,
    User,
)
from src.shared.infrastructure.persistence.database.session import get_session

router = APIRouter()


@router.get("/overview")
async def get_admin_overview(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return operational and quality signals for the admin dashboard."""
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)

    document_status = await _document_status_counts(db)
    recent_documents = await _recent_documents(db)
    failed_documents = await _failed_documents(db)
    deletion_jobs = await _deletion_job_summary(db)
    chat_summary = await _chat_summary(db, since_24h)
    quality_summary = await _quality_summary(db)
    system_health = await _system_health(db)

    total_documents = sum(document_status.values())
    failed_count = document_status.get("failed", 0)
    completed_count = document_status.get("completed", 0)
    processing_count = document_status.get("processing", 0)

    return {
        "generated_at": now.isoformat(),
        "admin": {
            "id": str(current_user.id),
            "email": current_user.email,
        },
        "system": system_health,
        "documents": {
            "total": total_documents,
            "completed": completed_count,
            "processing": processing_count,
            "failed": failed_count,
            "status_counts": document_status,
            "total_chunks": await _total_chunks(db),
            "recent": recent_documents,
            "failed_items": failed_documents,
            "deletion_jobs": deletion_jobs,
        },
        "retrieval": {
            "avg_source_score": quality_summary["avg_source_score"],
            "citation_coverage": quality_summary["citation_coverage"],
            "avg_sources_per_answer": quality_summary["avg_sources_per_answer"],
            "answers_with_sources": quality_summary["answers_with_sources"],
            "answers_sampled": quality_summary["answers_sampled"],
            "needs_review": quality_summary["needs_review"],
        },
        "answers": {
            "avg_quality_score": quality_summary["avg_quality_score"],
            "quality_gate_pass_rate": quality_summary["quality_gate_pass_rate"],
            "low_quality_count": quality_summary["low_quality_count"],
            "recent_reviews": quality_summary["recent_reviews"],
        },
        "activity": chat_summary,
    }


async def _document_status_counts(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(Document.status, func.count())
        .where(Document.deleted_at.is_(None))
        .group_by(Document.status)
    )
    return {status: count for status, count in result.all()}


async def _total_chunks(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(Document.chunk_count), 0))
        .where(Document.deleted_at.is_(None))
    )
    return int(result.scalar_one() or 0)


async def _recent_documents(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Document)
        .where(Document.deleted_at.is_(None))
        .order_by(desc(Document.updated_at))
        .limit(12)
    )
    return [_serialize_document(doc) for doc in result.scalars().all()]


async def _failed_documents(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Document)
        .where(Document.deleted_at.is_(None))
        .where(Document.status == "failed")
        .order_by(desc(Document.updated_at))
        .limit(10)
    )
    return [_serialize_document(doc) for doc in result.scalars().all()]


async def _deletion_job_summary(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(DocumentDeletionJob.status, func.count()).group_by(DocumentDeletionJob.status)
    )
    status_counts = {status: count for status, count in result.all()}

    latest_error_result = await db.execute(
        select(DocumentDeletionJob)
        .where(DocumentDeletionJob.last_error.is_not(None))
        .order_by(desc(DocumentDeletionJob.updated_at))
        .limit(1)
    )
    latest_error = latest_error_result.scalar_one_or_none()

    return {
        "status_counts": status_counts,
        "latest_error": latest_error.last_error if latest_error else None,
    }


async def _chat_summary(db: AsyncSession, since: datetime) -> dict[str, Any]:
    total_conversations = await _count(
        db,
        select(func.count()).select_from(Conversation).where(Conversation.deleted_at.is_(None)),
    )
    conversations_24h = await _count(
        db,
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.deleted_at.is_(None))
        .where(Conversation.created_at >= since),
    )
    messages_24h = await _count(
        db,
        select(func.count()).select_from(Message).where(Message.created_at >= since),
    )
    assistant_messages_24h = await _count(
        db,
        select(func.count())
        .select_from(Message)
        .where(Message.role == "assistant")
        .where(Message.created_at >= since),
    )

    return {
        "total_conversations": total_conversations,
        "conversations_24h": conversations_24h,
        "messages_24h": messages_24h,
        "assistant_messages_24h": assistant_messages_24h,
    }


async def _quality_summary(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(
        select(Message)
        .where(Message.role == "assistant")
        .order_by(desc(Message.created_at))
        .limit(100)
    )
    messages = result.scalars().all()

    answers_with_sources = 0
    source_counts: list[int] = []
    source_scores: list[float] = []
    quality_scores: list[float] = []
    low_quality_count = 0
    recent_reviews: list[dict[str, Any]] = []

    for message in messages:
        sources = message.sources or []
        flattened_sources = _flatten_sources(sources)
        source_count = len(flattened_sources)
        source_counts.append(source_count)
        if source_count > 0:
            answers_with_sources += 1

        for source in flattened_sources:
            score = _first_float(source, ("score", "relevance_score", "similarity", "rerank_score"))
            if score is not None:
                source_scores.append(score)

        quality_score = _extract_quality_score(message.meta_data or {})
        if quality_score is not None:
            quality_scores.append(quality_score)

        needs_review = source_count == 0 or (quality_score is not None and quality_score < 0.7)
        if needs_review:
            low_quality_count += 1
            if len(recent_reviews) < 8:
                recent_reviews.append(
                    {
                        "id": str(message.id),
                        "conversation_id": str(message.conversation_id),
                        "created_at": message.created_at.isoformat(),
                        "reason": "Không có nguồn truy xuất"
                        if source_count == 0
                        else "Điểm chất lượng thấp",
                        "source_count": source_count,
                        "quality_score": quality_score,
                        "preview": message.content[:220],
                    }
                )

    answers_sampled = len(messages)
    avg_source_score = _avg(source_scores)
    avg_quality_score = _avg(quality_scores)
    quality_gate_pass_rate = None
    if quality_scores:
        quality_gate_pass_rate = round(
            len([score for score in quality_scores if score >= 0.7]) / len(quality_scores),
            3,
        )

    return {
        "answers_sampled": answers_sampled,
        "answers_with_sources": answers_with_sources,
        "citation_coverage": round(answers_with_sources / answers_sampled, 3)
        if answers_sampled
        else None,
        "avg_sources_per_answer": _avg(source_counts),
        "avg_source_score": avg_source_score,
        "avg_quality_score": avg_quality_score,
        "quality_gate_pass_rate": quality_gate_pass_rate,
        "low_quality_count": low_quality_count,
        "needs_review": low_quality_count,
        "recent_reviews": recent_reviews,
    }


async def _system_health(db: AsyncSession) -> dict[str, Any]:
    services: list[dict[str, Any]] = []

    try:
        await db.execute(text("SELECT 1"))
        services.append({"name": "PostgreSQL", "status": "ok", "detail": settings.postgres_db})
    except Exception as exc:
        services.append({"name": "PostgreSQL", "status": "error", "detail": str(exc)})

    try:
        from src.shared.adapters.vector.qdrant_adapter import QdrantAdapter

        qdrant_ok = await QdrantAdapter().health_check()
        services.append(
            {
                "name": "Qdrant",
                "status": "ok" if qdrant_ok else "error",
                "detail": settings.qdrant_collection,
            }
        )
    except ImportError as exc:
        services.append(
            {
                "name": "Qdrant",
                "status": "missing",
                "detail": str(exc),
            }
        )

    configured_services = [
        ("Embedding API", settings.embedding_base_url),
        ("LLM", f"{settings.llm_provider}:{settings.glm_model if settings.llm_provider == 'glm' else settings.llm_provider}"),
        ("Redis/Celery", settings.celery_broker_url),
        ("MinIO", settings.minio_endpoint),
    ]
    services.extend(
        {"name": name, "status": "configured" if detail else "missing", "detail": detail}
        for name, detail in configured_services
    )

    has_error = any(service["status"] == "error" for service in services)
    has_missing = any(service["status"] == "missing" for service in services)
    overall = "error" if has_error else "degraded" if has_missing else "ok"

    return {"status": overall, "services": services}


async def _count(db: AsyncSession, statement: Any) -> int:
    result = await db.execute(statement)
    return int(result.scalar_one() or 0)


def _serialize_document(doc: Document) -> dict[str, Any]:
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "error_message": doc.error_message,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


def _flatten_sources(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        flattened: list[dict[str, Any]] = []
        for item in value:
            flattened.extend(_flatten_sources(item))
        return flattened
    if not isinstance(value, dict):
        return []

    nested = value.get("chunks") or value.get("sources") or value.get("citations")
    if isinstance(nested, list):
        nested_items = _flatten_sources(nested)
        return nested_items or [value]
    return [value]


def _first_float(value: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        raw_value = value.get(key)
        try:
            if raw_value is not None:
                return float(raw_value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_quality_score(value: Any) -> float | None:
    if isinstance(value, dict):
        for key in ("quality_score", "final_quality", "overall_score", "score"):
            try:
                if key in value and value[key] is not None:
                    return float(value[key])
            except (TypeError, ValueError):
                pass
        for nested_value in value.values():
            score = _extract_quality_score(nested_value)
            if score is not None:
                return score
    if isinstance(value, list):
        for item in value:
            score = _extract_quality_score(item)
            if score is not None:
                return score
    return None


def _avg(values: list[int] | list[float]) -> float | None:
    if not values:
        return None
    return round(float(sum(values)) / len(values), 3)


__all__ = ["router"]
