"""SQLAlchemy read model for the admin dashboard."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.persistence.database.models import Conversation, Document, DocumentDeletionJob, Message


class SqlAlchemyAdminDashboardRepository:
    """Collect dashboard aggregates without leaking SQL into the HTTP layer."""

    def __init__(self, db: AsyncSession): self._db = db

    async def overview(self, now: datetime) -> dict[str, Any]:
        statuses = dict((await self._db.execute(select(Document.status, func.count()).where(Document.deleted_at.is_(None)).group_by(Document.status))).all())
        chunks = int((await self._db.execute(select(func.coalesce(func.sum(Document.chunk_count), 0)).where(Document.deleted_at.is_(None)))).scalar_one() or 0)
        recent = (await self._db.execute(select(Document).where(Document.deleted_at.is_(None)).order_by(desc(Document.updated_at)).limit(12))).scalars().all()
        failed = (await self._db.execute(select(Document).where(Document.deleted_at.is_(None), Document.status == "failed").order_by(desc(Document.updated_at)).limit(10))).scalars().all()
        jobs = dict((await self._db.execute(select(DocumentDeletionJob.status, func.count()).group_by(DocumentDeletionJob.status))).all())
        error = (await self._db.execute(select(DocumentDeletionJob).where(DocumentDeletionJob.last_error.is_not(None)).order_by(desc(DocumentDeletionJob.updated_at)).limit(1))).scalar_one_or_none()
        since = now - timedelta(hours=24)
        async def count(statement: Any) -> int: return int((await self._db.execute(statement)).scalar_one() or 0)
        activity = {
            "total_conversations": await count(select(func.count()).select_from(Conversation).where(Conversation.deleted_at.is_(None))),
            "conversations_24h": await count(select(func.count()).select_from(Conversation).where(Conversation.deleted_at.is_(None), Conversation.created_at >= since)),
            "messages_24h": await count(select(func.count()).select_from(Message).where(Message.created_at >= since)),
            "assistant_messages_24h": await count(select(func.count()).select_from(Message).where(Message.role == "assistant", Message.created_at >= since)),
        }
        messages = (await self._db.execute(select(Message).where(Message.role == "assistant").order_by(desc(Message.created_at)).limit(100))).scalars().all()
        quality = self._quality(messages)
        return {"generated_at": now.isoformat(), "documents": {"total": sum(statuses.values()), "completed": statuses.get("completed", 0), "processing": statuses.get("processing", 0), "failed": statuses.get("failed", 0), "status_counts": statuses, "total_chunks": chunks, "recent": [self._document(x) for x in recent], "failed_items": [self._document(x) for x in failed], "deletion_jobs": {"status_counts": jobs, "latest_error": error.last_error if error else None}}, "retrieval": {key: quality[key] for key in ("avg_source_score", "citation_coverage", "avg_sources_per_answer", "answers_with_sources", "answers_sampled", "needs_review")}, "answers": {key: quality[key] for key in ("avg_quality_score", "quality_gate_pass_rate", "low_quality_count", "recent_reviews")}, "activity": activity}

    @staticmethod
    def _document(doc: Document) -> dict[str, Any]: return {"id": str(doc.id), "filename": doc.filename, "file_type": doc.file_type, "file_size": doc.file_size, "status": doc.status, "error_message": doc.error_message, "chunk_count": doc.chunk_count, "created_at": doc.created_at.isoformat(), "updated_at": doc.updated_at.isoformat()}

    @staticmethod
    def _quality(messages: list[Message]) -> dict[str, Any]:
        counts: list[int] = []
        scores: list[float] = []
        quality: list[float] = []
        reviews: list[dict[str, Any]] = []
        for message in messages:
            sources = SqlAlchemyAdminDashboardRepository._flatten_sources(message.sources or [])
            source_count = len(sources)
            counts.append(source_count)
            score = SqlAlchemyAdminDashboardRepository._quality_score(message.meta_data or {})
            if score is not None:
                quality.append(score)
            needs_review = source_count == 0 or (score is not None and score < 0.7)
            if needs_review and len(reviews) < 8:
                reviews.append(
                    {"id": str(message.id), "conversation_id": str(message.conversation_id), "created_at": message.created_at.isoformat(), "reason": "Không có nguồn truy xuất" if source_count == 0 else "Điểm chất lượng thấp", "source_count": source_count, "quality_score": score, "preview": message.content[:220]}
                )
            for source in sources:
                source_score = SqlAlchemyAdminDashboardRepository._first_float(source, ("score", "relevance_score", "similarity", "rerank_score"))
                if source_score is not None:
                    scores.append(source_score)

        def average(values: list[int] | list[float]) -> float | None:
            return round(sum(values) / len(values), 3) if values else None

        n = len(messages)
        with_sources = sum(count > 0 for count in counts)
        low_quality = sum(
            count == 0 or (score is not None and score < 0.7)
            for count, score in zip(counts, [SqlAlchemyAdminDashboardRepository._quality_score(message.meta_data or {}) for message in messages])
        )
        return {"answers_sampled": n, "answers_with_sources": with_sources, "citation_coverage": round(with_sources / n, 3) if n else None, "avg_sources_per_answer": average(counts), "avg_source_score": average(scores), "avg_quality_score": average(quality), "quality_gate_pass_rate": round(sum(score >= 0.7 for score in quality) / len(quality), 3) if quality else None, "low_quality_count": low_quality, "needs_review": low_quality, "recent_reviews": reviews}

    @staticmethod
    def _flatten_sources(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [source for item in value for source in SqlAlchemyAdminDashboardRepository._flatten_sources(item)]
        if not isinstance(value, dict):
            return []
        nested = value.get("chunks") or value.get("sources") or value.get("citations")
        if isinstance(nested, list):
            flattened = SqlAlchemyAdminDashboardRepository._flatten_sources(nested)
            return flattened or [value]
        return [value]

    @staticmethod
    def _first_float(value: dict[str, Any], keys: tuple[str, ...]) -> float | None:
        for key in keys:
            try:
                if value.get(key) is not None:
                    return float(value[key])
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _quality_score(value: Any) -> float | None:
        if isinstance(value, dict):
            score = SqlAlchemyAdminDashboardRepository._first_float(value, ("quality_score", "final_quality", "overall_score", "score"))
            if score is not None:
                return score
            for nested in value.values():
                score = SqlAlchemyAdminDashboardRepository._quality_score(nested)
                if score is not None:
                    return score
        elif isinstance(value, list):
            for nested in value:
                score = SqlAlchemyAdminDashboardRepository._quality_score(nested)
                if score is not None:
                    return score
        return None
