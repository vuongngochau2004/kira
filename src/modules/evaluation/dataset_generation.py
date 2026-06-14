"""Generate evaluation datasets from ingested document chunks.

This module intentionally reads chunks from the application database after the
normal upload/processing pipeline has run. That keeps the generated benchmark
aligned with the exact OCR, cleaning, and chunking behavior used by production
RAG.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from src.modules.evaluation.domain.models import GoldenDataset, GoldenDatasetSample
from src.shared.infrastructure.llm.client import LLMProvider, chat_async
from src.shared.infrastructure.persistence.database.models import Document, DocumentChunk
from src.shared.infrastructure.persistence.database.session import async_session_factory


DEFAULT_SYSTEM_PROMPT = """Bạn là chuyên gia tạo bộ dữ liệu đánh giá RAG cho văn bản pháp quy đại học.
Nhiệm vụ của bạn là tạo câu hỏi kiểm thử CHỈ dựa trên context được cung cấp.

Quy tắc bắt buộc:
- Không dùng kiến thức ngoài context.
- Câu hỏi phải trả lời được trực tiếp từ context.
- expected_answer phải chính xác, ngắn gọn, không suy diễn.
- answer_evidence phải là một đoạn trích ngắn có thật trong context.
- Ưu tiên câu hỏi về điều kiện, phạm vi áp dụng, trách nhiệm, quy trình, mốc thời gian, tiêu chí.
- Nếu context không đủ rõ để tạo câu hỏi chất lượng, trả về {"samples": []}.
- Trả về JSON hợp lệ, không markdown, không giải thích ngoài JSON.
"""


USER_PROMPT_TEMPLATE = """Tạo tối đa {questions_per_chunk} mẫu đánh giá RAG từ context dưới đây.

Thông tin nguồn:
- document_id: {document_id}
- filename: {filename}
- chunk_index: {chunk_index}

Context:
\"\"\"
{context}
\"\"\"

Schema JSON bắt buộc:
{{
  "samples": [
    {{
      "query": "câu hỏi tiếng Việt",
      "expected_answer": "câu trả lời chuẩn dựa trên context",
      "answer_evidence": "đoạn bằng chứng ngắn trích từ context",
      "question_type": "fact|condition|procedure|definition|responsibility|summary",
      "difficulty": "easy|medium"
    }}
  ]
}}
"""


@dataclass(frozen=True)
class SourceChunk:
    """Chunk selected from the ingested corpus."""

    document_id: str
    filename: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]


@dataclass
class DatasetGenerationConfig:
    """Configuration for synthetic dataset generation."""

    user_id: str
    output_path: str = "data/evaluation/generated_dataset.json"
    dataset_id: str = "generated-rag-eval"
    name: str = "Generated RAG evaluation dataset"
    description: str = "LLM-generated from chunks produced by the app ingestion pipeline."
    max_documents: int = 40
    chunks_per_document: int = 2
    questions_per_chunk: int = 2
    no_answer_count: int = 10
    min_chunk_chars: int = 600
    max_context_chars: int = 3500
    llm_provider: str | None = None
    llm_model: str | None = None
    temperature: float = 0.1
    timeout: float = 90.0


class IngestedChunkDatasetGenerator:
    """Generate a golden dataset from chunks already stored by the app."""

    def __init__(self, config: DatasetGenerationConfig):
        self.config = config

    async def generate(self) -> GoldenDataset:
        """Generate and save a dataset."""
        chunks = await self._load_sampled_chunks()
        samples: list[GoldenDatasetSample] = []

        for source in chunks:
            generated = await self._generate_samples_for_chunk(source)
            samples.extend(generated)

        samples.extend(self._build_no_answer_samples(chunks))

        dataset = GoldenDataset(
            dataset_id=self.config.dataset_id,
            name=self.config.name,
            description=self.config.description,
            samples=samples,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(dataset.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dataset

    async def _load_sampled_chunks(self) -> list[SourceChunk]:
        """Load chunks from DB and sample evenly across documents."""
        user_uuid = uuid.UUID(self.config.user_id)

        async with async_session_factory() as session:
            result = await session.execute(
                select(Document, DocumentChunk)
                .join(DocumentChunk, DocumentChunk.document_id == Document.id)
                .where(Document.user_id == user_uuid)
                .where(Document.deleted_at.is_(None))
                .where(Document.status == "completed")
                .order_by(Document.created_at.desc(), Document.filename, DocumentChunk.chunk_index)
            )
            rows = result.all()

        by_document: dict[str, list[SourceChunk]] = defaultdict(list)
        for document, chunk in rows:
            content = (chunk.content or "").strip()
            if len(content) < self.config.min_chunk_chars:
                continue
            source = SourceChunk(
                document_id=str(document.id),
                filename=document.filename,
                chunk_index=chunk.chunk_index,
                content=content,
                metadata=chunk.meta_data or {},
            )
            by_document[str(document.id)].append(source)

        sampled: list[SourceChunk] = []
        for _, doc_chunks in list(by_document.items())[: self.config.max_documents]:
            sampled.extend(
                self._pick_representative_chunks(doc_chunks, self.config.chunks_per_document)
            )

        return sampled

    @staticmethod
    def _pick_representative_chunks(chunks: list[SourceChunk], count: int) -> list[SourceChunk]:
        """Pick chunks spread across a document instead of only from the beginning."""
        if len(chunks) <= count:
            return chunks
        if count <= 1:
            return [chunks[len(chunks) // 2]]

        positions = [round(i * (len(chunks) - 1) / (count - 1)) for i in range(count)]
        seen: set[int] = set()
        picked = []
        for pos in positions:
            if pos in seen:
                continue
            seen.add(pos)
            picked.append(chunks[pos])
        return picked

    async def _generate_samples_for_chunk(self, source: SourceChunk) -> list[GoldenDatasetSample]:
        """Call LLM to generate answerable samples for one chunk."""
        prompt = USER_PROMPT_TEMPLATE.format(
            questions_per_chunk=self.config.questions_per_chunk,
            document_id=source.document_id,
            filename=source.filename,
            chunk_index=source.chunk_index,
            context=source.content[: self.config.max_context_chars],
        )

        provider = LLMProvider(self.config.llm_provider) if self.config.llm_provider else None
        response = await chat_async(
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            provider=provider,
            model=self.config.llm_model,
            temperature=self.config.temperature,
            max_tokens=1800,
            timeout=self.config.timeout,
        )
        payload = self._parse_json(response.get("content", ""))
        raw_samples = payload.get("samples", []) if isinstance(payload, dict) else []

        samples = []
        for index, raw in enumerate(raw_samples):
            query = str(raw.get("query", "")).strip()
            expected_answer = str(raw.get("expected_answer", "")).strip()
            if not query or not expected_answer:
                continue

            question_type = str(raw.get("question_type", "fact")).strip() or "fact"
            difficulty = str(raw.get("difficulty", "easy")).strip() or "easy"
            sample_id = self._sample_id(source, index, question_type)

            samples.append(
                GoldenDatasetSample(
                    id=sample_id,
                    query=query,
                    expected_answer=expected_answer,
                    reference_contexts=[source.content],
                    expected_context_ids=[f"{source.document_id}:{source.chunk_index}"],
                    expected_citations=[source.document_id],
                    should_refuse=False,
                    tags=[
                        "llm-generated",
                        "answerable",
                        question_type,
                        difficulty,
                    ],
                    metadata={
                        "source_file": source.filename,
                        "document_id": source.document_id,
                        "chunk_index": source.chunk_index,
                        "answer_evidence": str(raw.get("answer_evidence", "")).strip(),
                        "generation_method": "ingested-chunk-llm",
                    },
                )
            )

        return samples

    def _build_no_answer_samples(self, chunks: list[SourceChunk]) -> list[GoldenDatasetSample]:
        """Create refusal cases that should not be answerable from the corpus."""
        templates = [
            "Các văn bản này có quy định mức học phí cho năm 2099 là bao nhiêu không?",
            "Có văn bản nào nêu lịch nghỉ Tết năm 2099 của Trường Đại học Bách khoa không?",
            "Các tài liệu này có công bố danh sách mật khẩu tài khoản sinh viên không?",
            "Có quy định nào trong các tài liệu này yêu cầu sinh viên mua một mẫu laptop cụ thể không?",
            "Các văn bản này có nêu điểm chuẩn tuyển sinh năm 2099 không?",
        ]
        samples = []
        for index in range(self.config.no_answer_count):
            query = templates[index % len(templates)]
            sample_id = f"no_answer_{index + 1:03d}"
            samples.append(
                GoldenDatasetSample(
                    id=sample_id,
                    query=query,
                    expected_answer=None,
                    reference_contexts=[],
                    expected_context_ids=[],
                    expected_citations=[],
                    should_refuse=True,
                    tags=["llm-generated", "no-answer", "refusal"],
                    metadata={
                        "generation_method": "deterministic-no-answer",
                        "sampled_corpus_size": len(chunks),
                    },
                )
            )
        return samples

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """Parse a JSON object from an LLM response."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if not match:
                return {"samples": []}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {"samples": []}

    @staticmethod
    def _sample_id(source: SourceChunk, index: int, question_type: str) -> str:
        """Build stable-ish sample IDs from source identity."""
        filename_slug = re.sub(r"[^a-zA-Z0-9]+", "_", Path(source.filename).stem).strip("_")
        filename_slug = filename_slug[:40] or "document"
        return f"{filename_slug}_chunk_{source.chunk_index:04d}_{question_type}_{index + 1}"


async def generate_dataset(config: DatasetGenerationConfig) -> GoldenDataset:
    """Convenience async entry point."""
    return await IngestedChunkDatasetGenerator(config).generate()


def generate_dataset_sync(config: DatasetGenerationConfig) -> GoldenDataset:
    """Sync entry point for scripts."""
    return asyncio.run(generate_dataset(config))


__all__ = [
    "DatasetGenerationConfig",
    "IngestedChunkDatasetGenerator",
    "generate_dataset",
    "generate_dataset_sync",
]
