"""Run the real RAG pipeline against a golden dataset."""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path

from src.modules.evaluation.domain.dataset import DatasetManager
from src.modules.evaluation.domain.models import (
    BatchEvaluationResponse,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationRunConfig,
    GoldenDatasetSample,
    MetricResult,
)
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.reports.reporter import EvaluationReporter
from src.modules.rag.application import RAGPipelineService
from src.modules.rag.orchestration.state.rag_state import Citation, get_retrieval_docs


class RAGPipelineEvaluationRunner:
    """Run end-to-end RAG benchmark and persist reports."""

    def __init__(
        self,
        pipeline: RAGPipelineService,
        evaluator: DeepEvalEvaluationService,
        dataset_manager: DatasetManager | None = None,
        reporter: EvaluationReporter | None = None,
    ):
        self.pipeline = pipeline
        self.evaluator = evaluator
        self.dataset_manager = dataset_manager or DatasetManager()
        self.reporter = reporter or EvaluationReporter()

    async def run(
        self, config: EvaluationRunConfig
    ) -> tuple[BatchEvaluationResponse, dict[str, Path]]:
        """Execute the benchmark and write JSON/Markdown reports."""
        dataset = self.dataset_manager.load_file(config.dataset_path)
        samples = dataset.samples[: config.max_samples] if config.max_samples else dataset.samples
        started = time.time()
        started_at = datetime.utcnow()
        results = []
        failed = 0

        sem = asyncio.Semaphore(5)  # Restrict to 5 concurrent pipeline runs and evaluations

        async def _process_sample(sample: GoldenDatasetSample) -> tuple[EvaluationResponse, bool]:
            async with sem:
                try:
                    state = await self.pipeline.run(
                        query=sample.query,
                        user_id=config.user_id,
                        conversation_id=None,
                    )
                    eval_request = self._request_from_state(sample, state, config)
                    res = await self.evaluator.evaluate(eval_request)
                    return res, False
                except Exception as exc:
                    res = self._failure_result(sample, exc, config)
                    return res, True

        tasks = [_process_sample(s) for s in samples]
        raw_results = await asyncio.gather(*tasks)

        for res, is_fail in raw_results:
            results.append(res)
            if is_fail:
                failed += 1

        report = BatchEvaluationResponse(
            batch_id=str(uuid.uuid4()),
            total_queries=len(samples),
            successful_evaluations=len(results) - failed,
            failed_evaluations=failed,
            results=results,
            aggregated_scores=DeepEvalEvaluationService._aggregate(results),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            total_duration_seconds=time.time() - started,
        )
        paths = self.reporter.write(report, output_dir=config.output_dir, run_name=config.run_name)
        return report, paths

    def _request_from_state(
        self,
        sample: GoldenDatasetSample,
        state: dict,
        config: EvaluationRunConfig,
    ) -> EvaluationRequest:
        docs = get_retrieval_docs(state)
        generation_metadata = self._report_generation_metadata(state.get("generation_metadata", {}))
        compressed_contexts = generation_metadata.pop("_compressed_contexts_for_eval", [])
        contexts = compressed_contexts or [doc.content for doc in docs if doc.content]
        actual_citations = self._extract_actual_citations(state)

        return EvaluationRequest(
            query=sample.query,
            answer=state.get("final_response") or state.get("generated_response") or "",
            contexts=contexts,
            expected_answer=sample.expected_answer,
            reference_contexts=sample.reference_contexts,
            expected_citations=sample.expected_citations or sample.expected_context_ids,
            actual_citations=actual_citations,
            should_refuse=sample.should_refuse,
            retrieval_k=config.retrieval_k,
            metrics=config.metrics,
            metadata={
                "sample_id": sample.id,
                "tags": sample.tags,
                "expected_context_ids": sample.expected_context_ids,
                "retrieved_context_ids": self._retrieved_context_ids(docs),
                "quality_agent_output": state.get("quality_agent_output", {}),
                "generation_metadata": generation_metadata,
                "agent_results": [
                    result.model_dump() if hasattr(result, "model_dump") else result
                    for result in state.get("agent_results", [])
                ],
            },
        )

    @staticmethod
    def _report_generation_metadata(metadata: dict) -> dict:
        """Remove bulky context payloads while preserving compression diagnostics."""
        report_metadata = dict(metadata or {})
        compressed_contexts = report_metadata.pop("compressed_contexts", []) or []
        report_metadata["_compressed_contexts_for_eval"] = compressed_contexts
        if compressed_contexts:
            report_metadata["compressed_context_count"] = len(compressed_contexts)
            report_metadata["compressed_context_total_chars"] = sum(
                len(context) for context in compressed_contexts
            )
        return report_metadata

    def _failure_result(
        self,
        sample: GoldenDatasetSample,
        exc: Exception,
        config: EvaluationRunConfig,
    ) -> EvaluationResponse:
        return EvaluationResponse(
            evaluation_id=str(uuid.uuid4()),
            sample_id=sample.id,
            query=sample.query,
            answer=f"Evaluation pipeline failed: {exc}",
            results=[
                MetricResult(
                    metric=metric.canonical,
                    score=0.0,
                    threshold=config.threshold,
                    passed=False,
                    error=str(exc),
                )
                for metric in config.metrics
            ],
            overall_score=0.0,
            passed=False,
            metadata={"sample_id": sample.id, "pipeline_error": str(exc)},
        )

    @staticmethod
    def _retrieved_context_ids(docs: list) -> list[str]:
        """Return one rank-preserving identifier per retrieved context."""
        ids: list[str] = []
        for doc in docs:
            document_id = str(doc.doc_id)
            if doc.chunk_index is not None:
                ids.append(f"{document_id}:{doc.chunk_index}")
            else:
                ids.append(document_id)
        return ids

    @staticmethod
    def _extract_actual_citations(state: dict) -> list[str]:
        citations = state.get("final_citations") or []
        actual = []
        for citation in citations:
            if isinstance(citation, Citation):
                document_id = citation.document_id
                chunk_index = citation.chunk_index
            else:
                document_id = citation.get("document_id")
                chunk_index = citation.get("chunk_index")
            if document_id:
                actual.append(str(document_id))
                if chunk_index is not None:
                    actual.append(f"{document_id}:{chunk_index}")
        return actual
