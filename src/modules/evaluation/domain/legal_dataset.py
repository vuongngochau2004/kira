"""Golden dataset format for point-in-time legal QA evaluation."""

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

LegalCategory = Literal["current", "past", "compare", "guide", "no_answer"]
LEGAL_CATEGORIES: tuple[str, ...] = ("current", "past", "compare", "guide", "no_answer")
MIN_TOTAL_SAMPLES = 50
MIN_PER_CATEGORY = 5

_PROVISION_KEY = re.compile(r"[^#\s]+#D\d+[a-zđ]?(?:\.K\d+[a-zđ]?(?:\.[a-zđ])?)?")


class ExpectedProvision(BaseModel):
    """A provision the answer must cite; `valid_from` pins one version of it."""

    provision_key: str
    valid_from: date | None = None

    @model_validator(mode="after")
    def _check_key(self) -> "ExpectedProvision":
        if _PROVISION_KEY.fullmatch(self.provision_key) is None:
            raise ValueError(f"Invalid provision key: {self.provision_key}")
        return self


class LegalGoldenSample(BaseModel):
    id: str = Field(min_length=1)
    query: str = Field(min_length=3)
    today: date
    category: LegalCategory
    expected_mode: Literal["single", "compare"]
    expected_dates: list[date]
    expected_provisions: list[ExpectedProvision] = Field(default_factory=list)
    expected_answer: str | None = None
    should_refuse: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _check_consistency(self) -> "LegalGoldenSample":
        expected_count = 1 if self.expected_mode == "single" else 2
        if len(self.expected_dates) != expected_count:
            raise ValueError(f"{self.expected_mode} mode needs {expected_count} expected date(s)")
        if self.expected_mode == "compare" and self.expected_dates[0] >= self.expected_dates[1]:
            raise ValueError("Compare dates must be in increasing order")
        if (self.category == "compare") != (self.expected_mode == "compare"):
            raise ValueError("Category 'compare' and mode 'compare' must go together")
        if (self.category == "no_answer") != self.should_refuse:
            raise ValueError("Category 'no_answer' and should_refuse must go together")
        if self.should_refuse and self.expected_provisions:
            raise ValueError("A no-answer sample cannot expect provisions")
        if not self.should_refuse and not self.expected_provisions:
            raise ValueError("An answerable sample needs at least one expected provision")
        return self


class LegalGoldenDataset(BaseModel):
    dataset_id: str
    name: str
    description: str = ""
    samples: list[LegalGoldenSample]

    @model_validator(mode="after")
    def _unique_ids(self) -> "LegalGoldenDataset":
        duplicates = [i for i, n in Counter(s.id for s in self.samples).items() if n > 1]
        if duplicates:
            raise ValueError(f"Duplicate sample ids: {', '.join(sorted(duplicates))}")
        return self


def load_legal_dataset(path: str | Path) -> LegalGoldenDataset:
    with Path(path).open(encoding="utf-8") as file:
        return LegalGoldenDataset.model_validate(json.load(file))


def category_counts(dataset: LegalGoldenDataset) -> dict[str, int]:
    return dict(Counter(sample.category for sample in dataset.samples))


def coverage_warnings(dataset: LegalGoldenDataset) -> list[str]:
    warnings: list[str] = []
    if len(dataset.samples) < MIN_TOTAL_SAMPLES:
        warnings.append(
            f"Only {len(dataset.samples)} samples; the spec targets at least {MIN_TOTAL_SAMPLES}."
        )
    counts = category_counts(dataset)
    for category in LEGAL_CATEGORIES:
        if counts.get(category, 0) < MIN_PER_CATEGORY:
            warnings.append(
                f"Category '{category}' has {counts.get(category, 0)} samples "
                f"(target {MIN_PER_CATEGORY})."
            )
    return warnings
