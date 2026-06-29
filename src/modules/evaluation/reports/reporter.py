"""Write evaluation reports to disk."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.modules.evaluation.domain.models import BatchEvaluationResponse


METRIC_DIAGNOSTICS = {
    "answer_relevancy": (
        "Generation answers the wrong question or omits key information.",
        "Review intent routing, answer prompt, and generation model.",
    ),
    "faithfulness": (
        "Generation makes claims not supported by retrieved context.",
        "Strengthen grounding instructions, citation use, or generation model.",
    ),
    "contextual_relevancy": (
        "Retrieved context contains too much irrelevant content.",
        "Tune chunking, embedding, reranking, or lower retrieval top-k.",
    ),
    "mrr": (
        "The first relevant chunk is ranked too low.",
        "Tune hybrid-search weights, reranker, or query rewriting.",
    ),
    "recall_at_k": (
        "Top-k retrieval misses required evidence.",
        "Increase top-k, improve chunk coverage, indexing, or query rewriting.",
    ),
    "citation_accuracy": (
        "Answer citations do not identify the expected evidence.",
        "Fix citation extraction, source-to-answer mapping, or citation formatting.",
    ),
    "refusal_correctness": (
        "The system answers without evidence or refuses answerable questions.",
        "Tune no-answer threshold and refusal policy/prompt.",
    ),
}


class EvaluationReporter:
    """Persist JSON and Markdown benchmark reports."""

    def write(
        self,
        report: BatchEvaluationResponse,
        output_dir: str | Path,
        run_name: str | None = None,
    ) -> dict[str, Path]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        slug = run_name or datetime.utcnow().strftime("rag-eval-%Y%m%d-%H%M%S")

        json_path = output_path / f"{slug}.json"
        md_path = output_path / f"{slug}.md"

        with json_path.open("w", encoding="utf-8") as file:
            json.dump(report.model_dump(mode="json"), file, ensure_ascii=False, indent=2)

        md_path.write_text(self._to_markdown(report), encoding="utf-8")
        return {"json": json_path, "markdown": md_path}

    def _to_markdown(self, report: BatchEvaluationResponse) -> str:
        lines = [
            "# RAG Evaluation Report",
            "",
            f"- Batch ID: `{report.batch_id}`",
            f"- Total samples: {report.total_queries}",
            f"- Successful: {report.successful_evaluations}",
            f"- Failed: {report.failed_evaluations}",
            f"- Duration: {report.total_duration_seconds:.2f}s",
            "",
            "## Aggregate Scores",
            "",
            "| Metric | Score |",
            "| --- | ---: |",
        ]
        for name, score in sorted(report.aggregated_scores.items()):
            lines.append(f"| {name} | {score:.3f} |")

        lines.extend(["", "## Improvement Guide", ""])
        lines.extend(
            [
                "| Metric | Low score means | Improve |",
                "| --- | --- | --- |",
            ]
        )
        for metric in sorted(
            name for name in report.aggregated_scores if name in METRIC_DIAGNOSTICS
        ):
            symptom, action = METRIC_DIAGNOSTICS[metric]
            lines.append(f"| {metric} | {symptom} | {action} |")

        lines.extend(self._failure_analysis_markdown(report))

        lines.extend(["", "## Samples", ""])
        for result in report.results:
            sample_id = result.sample_id or result.evaluation_id
            analysis = result.metadata.get("failure_analysis", {})
            categories = ", ".join(analysis.get("categories", [])) or "unknown"
            lines.extend(
                [
                    f"### {sample_id}",
                    "",
                    f"- Passed: {'yes' if result.passed else 'no'}",
                    f"- Overall: {result.overall_score:.3f}",
                    f"- Failure analysis: {categories}",
                    f"- Query: {result.query}",
                    "",
                    "| Metric | Score | Pass | Reason |",
                    "| --- | ---: | --- | --- |",
                ]
            )
            for metric in result.results:
                reason = (metric.reason or metric.error or "").replace("\n", " ")
                lines.append(
                    f"| {metric.metric.value} | {metric.score:.3f} | "
                    f"{'yes' if metric.passed else 'no'} | {reason} |"
                )
            lines.append("")
        return "\n".join(lines)

    def _failure_analysis_markdown(self, report: BatchEvaluationResponse) -> list[str]:
        """Summarize sample-level failure classes for faster debugging."""
        category_counts: dict[str, int] = {}
        retrieval_failed = 0
        generation_failed = 0
        examples: dict[str, list[str]] = {}

        for result in report.results:
            analysis = result.metadata.get("failure_analysis", {})
            categories = analysis.get("categories") or ["unknown"]
            if analysis.get("retrieval_failed"):
                retrieval_failed += 1
            if analysis.get("generation_failed"):
                generation_failed += 1

            sample_id = result.sample_id or result.evaluation_id
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
                examples.setdefault(category, [])
                if len(examples[category]) < 5:
                    examples[category].append(str(sample_id))

        lines = [
            "",
            "## Failure Analysis",
            "",
            f"- Retrieval failures: {retrieval_failed}",
            f"- Generation failures: {generation_failed}",
            "",
            "| Category | Samples | Example sample IDs |",
            "| --- | ---: | --- |",
        ]

        for category, count in sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0])
        ):
            sample_examples = ", ".join(examples.get(category, []))
            lines.append(f"| {category} | {count} | {sample_examples} |")

        lines.extend(
            [
                "",
                "Interpretation:",
                "- `retrieval_miss`: top-k did not retrieve expected evidence.",
                "- `retrieval_ranking`: expected evidence was retrieved but ranked too low.",
                "- `context_noise`: retrieved context is too noisy for the question.",
                "- `generation_answer`: retrieval is acceptable, but the answer is off-target or incomplete.",
                "- `generation_grounding`: answer contains unsupported claims.",
                "- `citation_mapping`: citations do not map to expected evidence.",
                "- `refusal_policy`: refusal/no-answer decision is wrong.",
            ]
        )
        return lines
