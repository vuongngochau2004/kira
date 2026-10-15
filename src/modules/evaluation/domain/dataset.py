"""Golden dataset loading and saving."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.modules.evaluation.domain.models import GoldenDataset


class DatasetManager:
    """Manage golden datasets stored as JSON files."""

    def __init__(self, datasets_dir: str | Path = "data/evaluation"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def load_file(self, path: str | Path) -> GoldenDataset:
        """Load a dataset by exact file path."""
        with Path(path).open("r", encoding="utf-8") as file:
            return GoldenDataset.model_validate(json.load(file))

    def save_dataset(self, dataset: GoldenDataset) -> Path:
        """Save a dataset to the managed directory."""
        dataset.updated_at = datetime.utcnow()
        path = self.datasets_dir / f"{dataset.dataset_id}.json"
        with path.open("w", encoding="utf-8") as file:
            json.dump(dataset.model_dump(mode="json"), file, ensure_ascii=False, indent=2)
        return path

    def list_datasets(self) -> list[GoldenDataset]:
        """List all datasets in the managed directory."""
        datasets = []
        for path in sorted(self.datasets_dir.glob("*.json")):
            try:
                datasets.append(self.load_file(path))
            except Exception:
                continue
        return datasets


_dataset_manager: DatasetManager | None = None


def get_dataset_manager() -> DatasetManager:
    """Return the default dataset manager singleton."""
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager()
    return _dataset_manager


__all__ = ["DatasetManager", "get_dataset_manager"]
