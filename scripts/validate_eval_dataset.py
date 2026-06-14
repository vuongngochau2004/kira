"""Validate generated RAG evaluation datasets before running benchmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a RAG evaluation dataset JSON file.")
    parser.add_argument("dataset")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = Path(args.dataset)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    samples = dataset.get("samples", [])

    issues: list[str] = []
    answerable = 0
    no_answer = 0

    for sample in samples:
        sample_id = sample.get("id", "<missing-id>")
        contexts = sample.get("reference_contexts") or []
        context = "\n".join(contexts)
        should_refuse = bool(sample.get("should_refuse"))

        if should_refuse:
            no_answer += 1
            if sample.get("expected_answer") is None:
                issues.append(f"{sample_id}: no-answer sample has expected_answer=null")
            if contexts:
                issues.append(f"{sample_id}: no-answer sample should not have reference_contexts")
            continue

        answerable += 1
        if not sample.get("expected_answer"):
            issues.append(f"{sample_id}: answerable sample is missing expected_answer")
        if not context.strip():
            issues.append(f"{sample_id}: answerable sample is missing reference_contexts")

        evidence = (sample.get("metadata") or {}).get("answer_evidence") or ""
        if len(evidence.strip()) < 20:
            issues.append(f"{sample_id}: answer_evidence is missing or too short")
        elif evidence not in context:
            issues.append(f"{sample_id}: answer_evidence is not an exact substring of context")

    print(f"Dataset: {path}")
    print(f"Samples: {len(samples)}")
    print(f"Answerable: {answerable}")
    print(f"No-answer: {no_answer}")
    print(f"Issues: {len(issues)}")

    for issue in issues:
        print(f"- {issue}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
