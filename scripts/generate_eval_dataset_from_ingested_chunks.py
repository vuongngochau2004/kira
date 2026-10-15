"""Generate a DeepEval-compatible golden dataset from ingested chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.evaluation.dataset_generation import (  # noqa: E402
    DatasetGenerationConfig,
    generate_dataset_sync,
)
from src.modules.evaluation.composition import ingested_chunk_repository  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use LLM to generate evaluation dataset from chunks already ingested by the app.",
    )
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--output", default="data/evaluation/generated_dataset.json")
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Optional path for dataset summary JSON. Defaults to <output>.summary.json.",
    )
    parser.add_argument("--dataset-id", default="generated-rag-eval")
    parser.add_argument("--name", default="Generated RAG evaluation dataset")
    parser.add_argument("--max-documents", type=int, default=40)
    parser.add_argument("--chunks-per-document", type=int, default=2)
    parser.add_argument("--questions-per-chunk", type=int, default=2)
    parser.add_argument("--no-answer-count", type=int, default=10)
    parser.add_argument("--min-chunk-chars", type=int, default=600)
    parser.add_argument("--max-context-chars", type=int, default=3500)
    parser.add_argument("--llm-provider", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--timeout", type=float, default=90.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset = generate_dataset_sync(
        DatasetGenerationConfig(
            user_id=args.user_id,
            output_path=args.output,
            summary_output_path=args.summary_output,
            dataset_id=args.dataset_id,
            name=args.name,
            max_documents=args.max_documents,
            chunks_per_document=args.chunks_per_document,
            questions_per_chunk=args.questions_per_chunk,
            no_answer_count=args.no_answer_count,
            min_chunk_chars=args.min_chunk_chars,
            max_context_chars=args.max_context_chars,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            timeout=args.timeout,
        ),
        repository=ingested_chunk_repository(),
    )
    print(f"Generated {len(dataset.samples)} samples")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
