"""
dataset_manager.py
-------------------
Central Dataset Registry / Manager for the pipeline.

Rather than every script (download, clean, EDA, split) reaching directly
into a raw config dict with string keys, they go through a single
`DatasetManager` object. This gives:

  - One place that knows about every dataset and its current state
    (downloaded? cleaned? split?) instead of duplicated path-building logic
    scattered across scripts.
  - A typed `DatasetSpec` instead of untyped dict access (fewer KeyError
    surprises, easier to extend with new fields).
  - A single extension point: adding a dataset means adding one entry to
    config/datasets.yaml (+ a loader/normalizer pair) and it is
    automatically picked up everywhere via the registry.

Usage:
    manager = DatasetManager.from_config(cfg)
    manager.list_keys()                        -> ['fake_real_news', ...]
    manager.get("fever_dataset_key")            -> DatasetSpec
    manager.raw_dir("fact_checking")            -> Path(.../data/raw/fact_checking)
    manager.processed_path("fact_checking")     -> Path(.../data/processed/fact_checking.parquet)
    manager.status("fact_checking")             -> {"downloaded": True, "cleaned": False, "split": False}
    manager.by_modality("claim")                -> ['claim_verification', 'fact_checking']
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from src.utils.io_utils import project_path


@dataclass
class DatasetSpec:
    """Typed view of one entry in config/datasets.yaml."""
    key: str
    name: str
    modality: str            # "article" | "claim" | "image"
    task: str                # fake_news | claim_verification | fact_checking | ai_text_detection | image_forensics
    source: str               # "kaggle" | "url"
    dataset_version: str
    raw_subdir: str
    label_map: dict
    expected_files: Optional[list] = None
    kaggle_slug: Optional[str] = None
    extra: dict = field(default_factory=dict)   # anything else (urls, base_url, files, etc.)

    @classmethod
    def from_dict(cls, key: str, d: dict) -> "DatasetSpec":
        known = {"name", "modality", "task", "source", "dataset_version",
                 "raw_subdir", "label_map", "expected_files", "kaggle_slug"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(
            key=key,
            name=d["name"],
            modality=d["modality"],
            task=d["task"],
            source=d["source"],
            dataset_version=d.get("dataset_version", "unknown"),
            raw_subdir=d["raw_subdir"],
            label_map=d.get("label_map", {}),
            expected_files=d.get("expected_files"),
            kaggle_slug=d.get("kaggle_slug"),
            extra=extra,
        )


class DatasetManager:
    """Registry of all DatasetSpecs, plus path/status helpers built on top of it."""

    def __init__(self, specs: dict, cfg: dict):
        self._specs: dict[str, DatasetSpec] = specs
        self._cfg = cfg

    @classmethod
    def from_config(cls, cfg: dict) -> "DatasetManager":
        specs = {
            key: DatasetSpec.from_dict(key, d)
            for key, d in cfg["datasets"].items()
        }
        return cls(specs, cfg)

    # -- registry access -----------------------------------------------

    def list_keys(self) -> list:
        return list(self._specs.keys())

    def get(self, key: str) -> DatasetSpec:
        if key not in self._specs:
            raise KeyError(f"Unknown dataset '{key}'. Known datasets: {self.list_keys()}")
        return self._specs[key]

    def by_modality(self, modality: str) -> list:
        return [k for k, s in self._specs.items() if s.modality == modality]

    def by_task(self, task: str) -> list:
        return [k for k, s in self._specs.items() if s.task == task]

    def register(self, key: str, spec: DatasetSpec) -> None:
        """Register a dataset programmatically (e.g. in tests, or a future phase adding a 6th dataset)."""
        self._specs[key] = spec

    # -- path helpers -----------------------------------------------

    def raw_dir(self, key: str) -> Path:
        return project_path(self.get(key).raw_subdir)

    def processed_path(self, key: str) -> Path:
        return project_path(self._cfg["paths"]["processed_dir"]) / f"{key}.parquet"

    def lineage_path(self, key: str) -> Path:
        return project_path(self._cfg["paths"]["lineage_dir"]) / f"{key}.lineage.json"

    def splits_dir(self, key: str) -> Path:
        return project_path(self._cfg["paths"]["splits_dir"]) / key

    def profiling_path(self, key: str) -> Path:
        return project_path(self._cfg["paths"]["profiling_dir"]) / f"{key}_profile.md"

    # -- status -----------------------------------------------

    def status(self, key: str) -> dict:
        """Report where a dataset currently sits in the pipeline (download -> clean -> split)."""
        spec = self.get(key)
        raw_dir = self.raw_dir(key)

        if spec.expected_files:
            downloaded = all((raw_dir / f).exists() and (raw_dir / f).stat().st_size > 0
                              for f in spec.expected_files)
        elif spec.modality == "image":
            downloaded = any(raw_dir.rglob("*.jpg")) or any(raw_dir.rglob("*.png"))
        else:
            real_files = [p for p in raw_dir.iterdir() if not p.name.startswith(".")] if raw_dir.exists() else []
            downloaded = len(real_files) > 0

        cleaned = self.processed_path(key).exists()
        split_dir = self.splits_dir(key)
        is_split = split_dir.exists() and (split_dir / "train.parquet").exists()

        return {
            "downloaded": downloaded,
            "cleaned": cleaned,
            "split": is_split,
        }

    def status_report(self) -> dict:
        return {key: self.status(key) for key in self.list_keys()}
