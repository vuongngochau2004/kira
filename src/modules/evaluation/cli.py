"""Command line entry point for RAG benchmark runs."""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.modules.evaluation.domain.models import (
    DEFAULT_METRICS,
    EvaluationMetric,
    EvaluationRunConfig,
)
from src.modules.evaluation.domain.service import DeepEvalEvaluationService
from src.modules.evaluation.runners import RAGPipelineEvaluationRunner
from src.modules.rag.composition import create_default_rag_pipeline_service
from src.shared.adapters.llm.glm_adapter import GLMAdapter


def _parse_metrics(raw: str | None) -> list[EvaluationMetric]:
    if not raw:
        return DEFAULT_METRICS.copy()
    values = []
    for item in raw.split(","):
        name = item.strip()
        if not name:
            continue
        values.append(EvaluationMetric(name))
    return values


async def _run(args: argparse.Namespace) -> int:
    user_id = args.user_id
    if not user_id:
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[3]
        user_id_path = project_root / "dataset" / "user_id.txt"
        if user_id_path.exists():
            user_id = user_id_path.read_text().strip()
            print(f"WARNING: user-id parameter was empty. Loaded auto user_id from {user_id_path}: {user_id}")

    config = EvaluationRunConfig(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        user_id=user_id,
        metrics=_parse_metrics(args.metrics),
        threshold=args.threshold,
        retrieval_k=args.retrieval_k,
        max_samples=args.max_samples,
        run_name=args.run_name,
    )

    pipeline = create_default_rag_pipeline_service()
    evaluator = DeepEvalEvaluationService(
        judge_llm=GLMAdapter(),
        threshold=config.threshold,
    )
    runner = RAGPipelineEvaluationRunner(pipeline=pipeline, evaluator=evaluator)
    report, paths = await runner.run(config)

    print("DeepEval RAG benchmark completed")
    print(f"Batch ID: {report.batch_id}")
    print(f"Samples: {report.successful_evaluations}/{report.total_queries} successful")
    print(f"Overall: {report.aggregated_scores.get('overall_score', 0.0):.3f}")
    print(f"Pass rate: {report.aggregated_scores.get('pass_rate', 0.0):.3f}")
    print(f"JSON report: {paths['json']}")
    print(f"Markdown report: {paths['markdown']}")
    return 0 if report.aggregated_scores.get("pass_rate", 0.0) >= args.min_pass_rate else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DeepEval benchmark for the RAG pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a golden dataset through the real RAG pipeline.")
    run.add_argument("--dataset", required=True, help="Path to golden dataset JSON.")
    run.add_argument(
        "--user-id", required=True, help="User ID whose document index should be queried."
    )
    run.add_argument(
        "--output-dir", default="reports/evaluation", help="Directory for JSON/Markdown reports."
    )
    run.add_argument("--run-name", default=None, help="Optional report file stem.")
    run.add_argument(
        "--metrics", default=None, help="Comma-separated metric names. Defaults to all."
    )
    run.add_argument("--threshold", type=float, default=0.7, help="Metric pass threshold.")
    run.add_argument(
        "--retrieval-k",
        type=int,
        default=5,
        help="Top-k cutoff for deterministic retrieval metrics.",
    )
    run.add_argument(
        "--min-pass-rate", type=float, default=0.0, help="Exit non-zero below this pass rate."
    )
    run.add_argument(
        "--max-samples", type=int, default=None, help="Limit number of samples for a smoke run."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return asyncio.run(_run(args))
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
