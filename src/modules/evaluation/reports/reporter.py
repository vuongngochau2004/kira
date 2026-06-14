"""Write evaluation reports to disk."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.modules.evaluation.domain.models import BatchEvaluationResponse


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

        lines.extend(["", "## Samples", ""])
        for result in report.results:
            sample_id = result.sample_id or result.evaluation_id
            lines.extend(
                [
                    f"### {sample_id}",
                    "",
                    f"- Passed: {'yes' if result.passed else 'no'}",
                    f"- Overall: {result.overall_score:.3f}",
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
