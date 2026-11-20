"""Validate generated RAG evaluation datasets before running benchmarks."""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    warnings: list[str] = []
    answerable = 0
    no_answer = 0
    documents: set[str] = set()
    question_types: Counter[str] = Counter()

    for sample in samples:
        sample_id = sample.get("id", "<missing-id>")
        contexts = sample.get("reference_contexts") or []
        context = "\n".join(contexts)
        should_refuse = bool(sample.get("should_refuse"))

        if should_refuse:
            no_answer += 1
            if sample.get("expected_answer") is None:
                warnings.append(f"{sample_id}: no-answer sample has expected_answer=null")
            if contexts:
                issues.append(f"{sample_id}: no-answer sample should not have reference_contexts")
            continue

        answerable += 1
        metadata = sample.get("metadata") or {}
        document_id = metadata.get("document_id")
        if document_id:
            documents.add(str(document_id))
        for tag in sample.get("tags") or []:
            if tag not in {"llm-generated", "answerable", "no-answer", "refusal", "easy", "medium"}:
                question_types[str(tag)] += 1
        if not sample.get("expected_answer"):
            issues.append(f"{sample_id}: answerable sample is missing expected_answer")
        if not context.strip():
            issues.append(f"{sample_id}: answerable sample is missing reference_contexts")

        evidence = metadata.get("answer_evidence") or ""
        if len(evidence.strip()) < 20:
            issues.append(f"{sample_id}: answer_evidence is missing or too short")
        elif evidence not in context:
            issues.append(f"{sample_id}: answer_evidence is not an exact substring of context")

    if len(samples) < 100:
        warnings.append("dataset has fewer than 100 samples; use it only as a smoke test")
    if len(documents) < 20:
        warnings.append("answerable samples cover fewer than 20 documents")
    if no_answer < max(5, len(samples) // 10):
        warnings.append("no-answer/refusal samples are low relative to dataset size")

    print(f"Dataset: {path}")
    print(f"Samples: {len(samples)}")
    print(f"Answerable: {answerable}")
    print(f"No-answer: {no_answer}")
    print(f"Documents covered by answerable samples: {len(documents)}")
    print(f"Question types: {dict(sorted(question_types.items()))}")
    print(f"Warnings: {len(warnings)}")
    print(f"Issues: {len(issues)}")

    for warning in warnings:
        print(f"- warning: {warning}")
    for issue in issues:
        print(f"- {issue}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
