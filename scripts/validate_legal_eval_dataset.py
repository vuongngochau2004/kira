"""Validate a legal QA golden dataset: python scripts/validate_legal_eval_dataset.py PATH."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError  # noqa: E402

from src.modules.evaluation.domain.legal_dataset import (  # noqa: E402
    LEGAL_CATEGORIES,
    category_counts,
    coverage_warnings,
    load_legal_dataset,
)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python scripts/validate_legal_eval_dataset.py PATH")
        return 2
    try:
        dataset = load_legal_dataset(argv[0])
    except ValidationError as exc:
        print(f"INVALID dataset {argv[0]}:\n{exc}")
        return 1
    counts = category_counts(dataset)
    print(f"Dataset {dataset.dataset_id}: {len(dataset.samples)} samples")
    for category in LEGAL_CATEGORIES:
        print(f"  {category:<10} {counts.get(category, 0)}")
    for warning in coverage_warnings(dataset):
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
