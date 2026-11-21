"""Tests for kira.admin.repository."""

from types import SimpleNamespace
from uuid import uuid4

from kira.admin.repository import SqlAlchemyAdminDashboardRepository


def test_admin_quality_flattens_nested_sources_and_counts_review_once():
    message = SimpleNamespace(
        id=uuid4(),
        conversation_id=uuid4(),
        created_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00"),
        content="Câu trả lời",
        sources=[{"citations": [{"similarity": 0.8}, {"rerank_score": 0.6}]}],
        meta_data={"quality": {"quality_score": 0.6}},
    )

    quality = SqlAlchemyAdminDashboardRepository._quality([message])

    assert quality["answers_with_sources"] == 1
    assert quality["avg_source_score"] == 0.7
    assert quality["low_quality_count"] == 1
    assert quality["recent_reviews"][0]["source_count"] == 2
