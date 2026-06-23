"""Regression tests for the architecture refactor boundaries."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.modules.admin.infrastructure.dashboard_repository import SqlAlchemyAdminDashboardRepository
from src.modules.document.domain.services.extractor import extract_content
from src.modules.evaluation.dataset_generation import (
    DatasetGenerationConfig,
    IngestedChunkDatasetGenerator,
)
from src.modules.rag.application import RAGPipelineService
from src.modules.rag.orchestration.state.rag_state import AgentResult, AgentStatus


class FakeWorkflow:
    llm = None

    async def run(self, query, user_id, conversation_id=None):
        return {
            "final_response": "Không tìm thấy thông tin phù hợp.",
            "final_citations": [],
            "agent_results": [
                AgentResult(agent_name="RetrievalAgent", status=AgentStatus.COMPLETED, execution_time_ms=3)
            ],
        }

    async def run_stream(self, query, user_id, conversation_id=None):
        if False:
            yield {}


class FakeChunkRepository:
    async def list_completed_chunks(self, user_id):
        return [
            {
                "document_id": str(uuid4()),
                "filename": "quy-che.pdf",
                "chunk_index": 1,
                "content": "Nội dung " * 100,
                "metadata": {"page": 1},
            }
        ]


class FakeOCR:
    async def extract_text(self, image_bytes: bytes, language: str = "vi") -> str:
        assert image_bytes == b"fake-image"
        assert language == "vi"
        return "Văn bản đã OCR"

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_rag_result_metadata_is_json_serializable():
    result = await RAGPipelineService(FakeWorkflow()).execute("câu hỏi", "user-1")

    assert result.rejected is True
    assert result.metadata["agent_results"][0]["agent_name"] == "RetrievalAgent"
    json.dumps(result.metadata)


@pytest.mark.asyncio
async def test_dataset_generator_uses_injected_repository(tmp_path):
    config = DatasetGenerationConfig(
        user_id=str(uuid4()),
        output_path=str(tmp_path / "dataset.json"),
        no_answer_count=0,
    )
    generator = IngestedChunkDatasetGenerator(config, repository=FakeChunkRepository())

    chunks = await generator._load_sampled_chunks()

    assert len(chunks) == 1
    assert chunks[0].filename == "quy-che.pdf"


@pytest.mark.asyncio
async def test_image_extraction_uses_injected_ocr_port(tmp_path):
    image = tmp_path / "scan.png"
    image.write_bytes(b"fake-image")

    result = await extract_content(str(image), "png", ocr=FakeOCR())

    assert result.success is True
    assert result.text == "Văn bản đã OCR"
    assert result.metadata["extractor"] == "paddleocr"


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
