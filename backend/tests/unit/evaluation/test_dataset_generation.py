"""Tests for kira.evaluation.dataset_generation."""

from uuid import uuid4

import pytest

from kira.evaluation.dataset_generation import (
    DatasetGenerationConfig,
    IngestedChunkDatasetGenerator,
)


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
