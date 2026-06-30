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
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from src.modules.evaluation.domain.models import GoldenDataset, GoldenDatasetSample
from src.shared.infrastructure.llm.client import LLMProvider, chat_async


class IngestedChunkPort(Protocol):
    async def list_completed_chunks(self, user_id: uuid.UUID) -> list[dict[str, Any]]: ...


DEFAULT_SYSTEM_PROMPT = """Bạn là chuyên gia tạo bộ dữ liệu đánh giá RAG cho văn bản pháp quy đại học.
Nhiệm vụ của bạn là tạo câu hỏi kiểm thử CHỈ dựa trên ngữ cảnh được cung cấp.

Quy tắc bắt buộc:
- Không dùng kiến thức ngoài ngữ cảnh.
- Câu hỏi phải trả lời được trực tiếp từ ngữ cảnh.
- expected_answer phải chính xác, ngắn gọn, không suy diễn.
- answer_evidence phải là một đoạn trích NGUYÊN VĂN, liên tục, sao chép y hệt từ ngữ cảnh.
- Không được tự sửa lỗi OCR/chính tả trong answer_evidence.
- Tránh tình trạng mất cân bằng (skewed) dữ liệu: Không lạm dụng loại câu hỏi "fact" và độ khó "easy".
- Yêu cầu đối với question_type:
  + fact: câu hỏi tra cứu thông tin thực tế đơn giản, trực tiếp.
  + definition: định nghĩa, giải thích khái niệm hoặc thuật ngữ.
  + condition: điều kiện áp dụng, đối tượng áp dụng, điều khoản loại trừ.
  + procedure: quy trình, trình tự thực hiện, các bước thực hiện một công việc.
  + responsibility: quyền hạn, nghĩa vụ, trách nhiệm của các bên liên quan.
  + summary: tóm tắt ý chính hoặc tổng hợp thông tin từ nhiều câu/ý trong ngữ cảnh.
- Yêu cầu đối với difficulty:
  + easy: câu hỏi đơn giản, có thể trả lời trực tiếp bằng một câu ngắn gọn có sẵn trong văn bản.
  + medium: câu hỏi đòi hỏi tư duy tổng hợp thông tin từ nhiều câu, so sánh, hoặc quy trình nhiều bước, điều kiện ràng buộc phức tạp trong ngữ cảnh.
- Nếu ngữ cảnh không đủ rõ để tạo câu hỏi chất lượng, trả về {"samples": []}.
- Trả về JSON hợp lệ, không markdown, không giải thích ngoài JSON.
"""


USER_PROMPT_TEMPLATE = """Tạo đúng {questions_per_chunk} mẫu đánh giá RAG từ ngữ cảnh dưới đây.

Quy tắc phân bổ bắt buộc để tránh lệch dữ liệu (Skewed Dataset):
1. Đa dạng hóa loại câu hỏi: Trong {questions_per_chunk} câu hỏi được sinh ra, KHÔNG ĐƯỢC phép tất cả đều thuộc loại "fact". Hãy cố gắng sinh ít nhất 1 câu hỏi thuộc các nhóm phức tạp hơn như "condition", "procedure", hoặc "responsibility".
2. Cân bằng độ khó: Cố gắng sinh ít nhất 1 câu hỏi có độ khó "medium" (đòi hỏi liên kết thông tin hoặc tổng hợp điều kiện/quy trình) và 1 câu hỏi độ khó "easy". Tránh việc toàn bộ câu hỏi sinh ra đều là "easy".

Thông tin nguồn:
- document_id: {document_id}
- filename: {filename}
- chunk_index: {chunk_index}

Ngữ cảnh:
\"\"\"
{context}
\"\"\"

Lược đồ JSON bắt buộc:
{{
  "samples": [
    {{
      "query": "câu hỏi tiếng Việt tự nhiên, rõ ràng, cụ thể",
      "expected_answer": "câu trả lời chuẩn dựa trên ngữ cảnh",
      "answer_evidence": "đoạn bằng chứng ngắn trích từ ngữ cảnh",
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
    summary_output_path: str | None = None
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

    def __init__(
        self,
        config: DatasetGenerationConfig,
        repository: IngestedChunkPort,
    ):
        self.config = config
        self._repository = repository

    async def generate(self) -> GoldenDataset:
        """Generate and save a dataset."""
        chunks = await self._load_sampled_chunks()
        
        # Concurrency limit to avoid hitting LLM API rate limits (e.g. 5 concurrent calls)
        semaphore = asyncio.Semaphore(5)
        
        async def safe_worker(source: SourceChunk) -> list[GoldenDatasetSample]:
            async with semaphore:
                try:
                    return await self._generate_samples_for_chunk(source)
                except Exception as e:
                    print(f"Error generating samples for chunk {source.filename} [{source.chunk_index}]: {e}")
                    return []

        tasks = [safe_worker(source) for source in chunks]
        results_lists = await asyncio.gather(*tasks)
        
        samples: list[GoldenDatasetSample] = []
        for generated in results_lists:
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
        self._write_summary(dataset=dataset, chunks=chunks, output_path=output_path)
        return dataset

    async def _load_sampled_chunks(self) -> list[SourceChunk]:
        """Load chunks from DB and sample evenly across documents."""
        user_uuid = uuid.UUID(self.config.user_id)

        rows = await self._repository.list_completed_chunks(user_uuid)

        by_document: dict[str, list[SourceChunk]] = defaultdict(list)
        for row in rows:
            content = str(row["content"]).strip()
            if len(content) < self.config.min_chunk_chars:
                continue
            source = SourceChunk(
                document_id=str(row["document_id"]),
                filename=str(row["filename"]),
                chunk_index=int(row["chunk_index"]),
                content=content,
                metadata=dict(row["metadata"]),
            )
            by_document[source.document_id].append(source)

        sampled: list[SourceChunk] = []
        eligible_documents = self._stratified_documents(by_document)
        for doc_chunks in eligible_documents[: self.config.max_documents]:
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
            answer_evidence = str(raw.get("answer_evidence", "")).strip()
            if not query or not expected_answer:
                continue
            if not self._has_exact_evidence(source.content, answer_evidence):
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
                        "answer_evidence": answer_evidence,
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
            "Có văn bản nào quy định danh sách tài khoản và mật khẩu hệ thống nội bộ của giảng viên không?",
            "Các tài liệu này có nêu lịch thi chi tiết của học kỳ 3 năm 2099 không?",
            "Có quy định nào bắt buộc sinh viên sử dụng một thương hiệu điện thoại cụ thể không?",
            "Các văn bản này có công bố danh sách thông tin sức khỏe cá nhân của sinh viên không?",
            "Có tài liệu nào nêu quyết định bổ nhiệm hiệu trưởng cho năm 2099 không?",
            "Các văn bản này có quy định mức phạt tiền cho việc đi học muộn từng buổi không?",
            "Có quy định nào yêu cầu người học cung cấp mật khẩu email cá nhân cho nhà trường không?",
            "Các tài liệu này có nêu danh sách câu hỏi thi cuối kỳ của tất cả học phần không?",
            "Có văn bản nào quy định lịch nghỉ hè của toàn trường trong năm 2099 không?",
            "Các văn bản này có cho biết điểm rèn luyện cá nhân của từng sinh viên không?",
        ]
        samples = []
        for index in range(self.config.no_answer_count):
            query = templates[index % len(templates)]
            sample_id = f"no_answer_{index + 1:03d}"
            samples.append(
                GoldenDatasetSample(
                    id=sample_id,
                    query=query,
                    expected_answer="Không tìm thấy thông tin trong tài liệu được cung cấp.",
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

    def _write_summary(
        self,
        dataset: GoldenDataset,
        chunks: list[SourceChunk],
        output_path: Path,
    ) -> None:
        """Write a compact dataset summary for thesis reporting and QA."""
        summary_path = (
            Path(self.config.summary_output_path)
            if self.config.summary_output_path
            else output_path.with_suffix(".summary.json")
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        answerable = [sample for sample in dataset.samples if not sample.should_refuse]
        no_answer = [sample for sample in dataset.samples if sample.should_refuse]
        source_document_ids = {chunk.document_id for chunk in chunks}
        represented_document_ids = {
            str((sample.metadata or {}).get("document_id"))
            for sample in answerable
            if (sample.metadata or {}).get("document_id")
        }
        question_types = Counter(
            tag
            for sample in answerable
            for tag in sample.tags
            if tag
            not in {
                "llm-generated",
                "answerable",
                "no-answer",
                "refusal",
                "easy",
                "medium",
            }
        )
        difficulty = Counter(
            tag for sample in answerable for tag in sample.tags if tag in {"easy", "medium"}
        )

        summary = {
            "dataset_id": dataset.dataset_id,
            "name": dataset.name,
            "created_at": dataset.created_at.isoformat(),
            "generation_config": {
                "max_documents": self.config.max_documents,
                "chunks_per_document": self.config.chunks_per_document,
                "questions_per_chunk": self.config.questions_per_chunk,
                "no_answer_count": self.config.no_answer_count,
                "min_chunk_chars": self.config.min_chunk_chars,
                "max_context_chars": self.config.max_context_chars,
            },
            "corpus_sampling": {
                "sampled_documents": len(source_document_ids),
                "sampled_chunks": len(chunks),
                "documents_with_answerable_samples": len(represented_document_ids),
                "document_answerable_coverage": self._ratio(
                    len(represented_document_ids),
                    len(source_document_ids),
                ),
            },
            "samples": {
                "total": len(dataset.samples),
                "answerable": len(answerable),
                "no_answer": len(no_answer),
                "answerable_ratio": self._ratio(len(answerable), len(dataset.samples)),
                "no_answer_ratio": self._ratio(len(no_answer), len(dataset.samples)),
            },
            "question_types": dict(sorted(question_types.items())),
            "difficulty": dict(sorted(difficulty.items())),
            "source_documents": self._source_document_summary(chunks, answerable),
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def _stratified_documents(
        cls,
        by_document: dict[str, list[SourceChunk]],
    ) -> list[list[SourceChunk]]:
        """Select documents round-robin across filename-derived groups."""
        groups: dict[str, list[list[SourceChunk]]] = defaultdict(list)
        for doc_chunks in by_document.values():
            groups[cls._document_group_key(doc_chunks[0])].append(doc_chunks)

        for doc_chunks_group in groups.values():
            doc_chunks_group.sort(key=lambda chunks: chunks[0].filename.lower())

        ordered: list[list[SourceChunk]] = []
        group_names = sorted(groups)
        while True:
            before = len(ordered)
            for group_name in group_names:
                if groups[group_name]:
                    ordered.append(groups[group_name].pop(0))
            if len(ordered) == before:
                return ordered

    @staticmethod
    def _document_group_key(source: SourceChunk) -> str:
        """Infer a coarse document group from common filename conventions."""
        stem = Path(source.filename).stem.lower()
        normalized = re.sub(r"[^a-zA-ZÀ-ỹ0-9]+", " ", stem)
        tokens = [token for token in normalized.split() if token]
        for token in tokens[:4]:
            if token.isdigit():
                continue
            if re.fullmatch(r"\d{4}m\d+", token):
                return "legal-crawl"
            if len(token) >= 3:
                return token[:16]
        return "other"

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    @staticmethod
    def _source_document_summary(
        chunks: list[SourceChunk],
        answerable_samples: list[GoldenDatasetSample],
    ) -> list[dict[str, Any]]:
        chunks_by_document = Counter(chunk.document_id for chunk in chunks)
        filenames = {chunk.document_id: chunk.filename for chunk in chunks}
        samples_by_document = Counter(
            str((sample.metadata or {}).get("document_id"))
            for sample in answerable_samples
            if (sample.metadata or {}).get("document_id")
        )
        return [
            {
                "document_id": document_id,
                "filename": filenames[document_id],
                "sampled_chunks": chunks_by_document[document_id],
                "answerable_samples": samples_by_document[document_id],
            }
            for document_id in sorted(filenames, key=lambda doc_id: filenames[doc_id].lower())
        ]

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
    def _normalize_text(text: str) -> str:
        import unicodedata
        # Normalize unicode to NFC
        text = unicodedata.normalize("NFC", text)
        # Lowercase
        text = text.lower()
        # Clean whitespaces and newlines
        text = re.sub(r"\s+", " ", text).strip()
        # Remove basic punctuation
        text = re.sub(r"[.,;:!?'\"()\[\]\-]", "", text)
        return text

    @classmethod
    def _has_exact_evidence(cls, context: str, evidence: str) -> bool:
        """Return whether evidence is a useful substring of context (using fuzzy/normalized match)."""
        if len(evidence) < 20:
            return False
        
        # Exact match first
        if evidence in context:
            return True
            
        # Fallback to normalized match
        norm_context = cls._normalize_text(context)
        norm_evidence = cls._normalize_text(evidence)
        return norm_evidence in norm_context

    @staticmethod
    def _sample_id(source: SourceChunk, index: int, question_type: str) -> str:
        """Build stable-ish sample IDs from source identity."""
        filename_slug = re.sub(r"[^a-zA-Z0-9]+", "_", Path(source.filename).stem).strip("_")
        filename_slug = filename_slug[:40] or "document"
        return f"{filename_slug}_chunk_{source.chunk_index:04d}_{question_type}_{index + 1}"


async def generate_dataset(
    config: DatasetGenerationConfig, repository: IngestedChunkPort
) -> GoldenDataset:
    """Convenience async entry point."""
    return await IngestedChunkDatasetGenerator(config, repository=repository).generate()


def generate_dataset_sync(
    config: DatasetGenerationConfig, repository: IngestedChunkPort
) -> GoldenDataset:
    """Sync entry point for scripts."""
    return asyncio.run(generate_dataset(config, repository=repository))


__all__ = [
    "DatasetGenerationConfig",
    "IngestedChunkDatasetGenerator",
    "generate_dataset",
    "generate_dataset_sync",
]
