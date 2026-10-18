import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.modules.evaluation.domain.legal_dataset import (
    LegalGoldenDataset,
    LegalGoldenSample,
    category_counts,
    coverage_warnings,
    load_legal_dataset,
)

EXAMPLE = Path("docs/examples/evaluation/legal_golden_example.json")


def _sample(**overrides) -> dict:
    sample = {
        "id": "s1",
        "query": "Hiện nay quy định về quy hoạch đất thế nào?",
        "today": "2026-10-15",
        "category": "current",
        "expected_mode": "single",
        "expected_dates": ["2026-10-15"],
        "expected_provisions": [{"provision_key": "1/2099/QH99#D3.K1", "valid_from": "2026-07-01"}],
    }
    sample.update(overrides)
    return sample


def test_valid_sample_parses_dates_and_versions() -> None:
    sample = LegalGoldenSample.model_validate(_sample())
    assert sample.expected_dates[0].isoformat() == "2026-10-15"
    assert sample.expected_provisions[0].valid_from is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected_dates": ["2026-10-15", "2026-10-16"]},
        {
            "category": "compare",
            "expected_mode": "compare",
            "expected_dates": ["2026-07-01", "2026-06-30"],
        },
        {"category": "compare", "expected_mode": "single"},
        {"expected_provisions": [{"provision_key": "Điều 3 Luật Đất đai"}]},
        {"expected_provisions": []},
        {"category": "no_answer", "should_refuse": True},
        {"should_refuse": True},
        {"category": "unknown"},
    ],
)
def test_inconsistent_samples_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        LegalGoldenSample.model_validate(_sample(**overrides))


def test_no_answer_sample_without_provisions_is_valid() -> None:
    sample = LegalGoldenSample.model_validate(
        _sample(category="no_answer", should_refuse=True, expected_provisions=[])
    )
    assert sample.should_refuse


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        LegalGoldenDataset.model_validate(
            {"dataset_id": "d", "name": "n", "samples": [_sample(), _sample()]}
        )


def test_coverage_warnings_name_missing_categories() -> None:
    dataset = LegalGoldenDataset.model_validate(
        {"dataset_id": "d", "name": "n", "samples": [_sample()]}
    )
    warnings = coverage_warnings(dataset)
    assert any("50" in warning for warning in warnings)
    assert any("compare" in warning for warning in warnings)
    assert category_counts(dataset)["current"] == 1


def test_example_dataset_is_valid_and_covers_every_category() -> None:
    dataset = load_legal_dataset(EXAMPLE)
    assert set(category_counts(dataset)) == {"current", "past", "compare", "guide", "no_answer"}
    assert all(count >= 1 for count in category_counts(dataset).values())


def test_validator_script_exit_codes(tmp_path: Path) -> None:
    import subprocess
    import sys

    ok = subprocess.run(
        [sys.executable, "scripts/validate_legal_eval_dataset.py", str(EXAMPLE)],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "compare" in ok.stdout

    broken = tmp_path / "broken.json"
    broken.write_text(
        json.dumps({"dataset_id": "d", "name": "n", "samples": [_sample(expected_provisions=[])]}),
        encoding="utf-8",
    )
    bad = subprocess.run(
        [sys.executable, "scripts/validate_legal_eval_dataset.py", str(broken)],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
