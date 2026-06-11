"""Golden dataset management for RAGAS evaluation."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.evaluation import GoldenDataset, GoldenDatasetSample

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manager for golden datasets used in evaluation."""

    def __init__(self, datasets_dir: str | None = None):
        """Initialize dataset manager.

        Args:
            datasets_dir: Directory to store datasets (default: data/golden_datasets/)
        """
        self.datasets_dir = Path(datasets_dir or "data/golden_datasets")
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def save_dataset(
        self,
        dataset: GoldenDataset,
        user_id: str | None = None,
    ) -> GoldenDataset:
        """Save dataset to disk.

        Args:
            dataset: Dataset to save
            user_id: Optional user ID for ownership

        Returns:
            Saved dataset
        """
        # Generate ID if not provided
        if not dataset.dataset_id:
            dataset.dataset_id = str(uuid.uuid4())

        # Set timestamps
        if not dataset.created_at:
            dataset.created_at = datetime.utcnow()
        dataset.updated_at = datetime.utcnow()

        # Save to file
        file_path = self.datasets_dir / f"{dataset.dataset_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"[DATASET] Saved dataset {dataset.dataset_id} to {file_path}")
        return dataset

    def load_dataset(self, dataset_id: str) -> GoldenDataset | None:
        """Load dataset from disk.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset or None if not found
        """
        file_path = self.datasets_dir / f"{dataset_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return GoldenDataset(**data)
        except Exception as e:
            logger.error(f"[DATASET] Failed to load {dataset_id}: {e}")
            return None

    def list_datasets(self) -> list[GoldenDataset]:
        """List all available datasets.

        Returns:
            List of datasets
        """
        datasets = []

        for file_path in self.datasets_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                datasets.append(GoldenDataset(**data))
            except Exception as e:
                logger.warning(f"[DATASET] Failed to load {file_path}: {e}")

        return datasets

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            True if deleted, False if not found
        """
        file_path = self.datasets_dir / f"{dataset_id}.json"

        if file_path.exists():
            file_path.unlink()
            logger.info(f"[DATASET] Deleted dataset {dataset_id}")
            return True

        return False


# Singleton instance
_dataset_manager: DatasetManager | None = None


def get_dataset_manager() -> DatasetManager:
    """Get or create dataset manager singleton."""
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager()
    return _dataset_manager


__all__ = [
    "DatasetManager",
    "get_dataset_manager",
]
