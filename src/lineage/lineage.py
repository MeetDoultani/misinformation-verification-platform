"""
lineage.py
----------
Dataset lineage/version tracking, applied at the end of the cleaning
pipeline (after label mapping, before validation/save).

Two complementary outputs:
  1. Row-level stamping: every processed row carries `schema_version`,
     `dataset_version`, `pipeline_version`, and `ingested_at`, so a row
     pulled out of `data/processed/*.parquet` on its own is still
     self-describing (which schema, which pipeline run, which upstream
     dataset snapshot produced it).
  2. A per-dataset manifest (`data/processed/_lineage/<key>.lineage.json`)
     recording dataset-level provenance: source location, dataset_version,
     row counts at each cleaning stage (so you can see how many rows were
     dropped by deduplication vs missing-value handling vs label mapping),
     and the final label distribution. This is the audit trail future
     phases (and anyone reviewing data quality) can check without
     re-running the pipeline.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.schema.canonical_schema import CANONICAL_SCHEMA_VERSION
from src.utils.io_utils import ensure_dir


def stamp_lineage_columns(df: pd.DataFrame, dataset_version: str, pipeline_version: str) -> pd.DataFrame:
    """Add lineage columns to every row. Idempotent: overwrites if already present."""
    df = df.copy()
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df["schema_version"] = CANONICAL_SCHEMA_VERSION
    df["dataset_version"] = dataset_version
    df["pipeline_version"] = pipeline_version
    df["ingested_at"] = ingested_at
    return df


class LineageTracker:
    """
    Accumulates row-count checkpoints through the cleaning pipeline for one
    dataset, then writes them out as a JSON manifest alongside the summary
    stats needed to audit what happened to the raw data.

    Usage:
        tracker = LineageTracker(key, spec, cfg)
        tracker.checkpoint("raw_loaded", len(raw_df))
        ... cleaning steps ...
        tracker.checkpoint("after_dedup", len(df))
        ...
        tracker.finalize(df, out_path)
    """

    def __init__(self, key: str, spec, cfg: dict):
        self.key = key
        self.spec = spec
        self.cfg = cfg
        self.checkpoints = []
        self.started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def checkpoint(self, stage: str, n_rows: int) -> None:
        self.checkpoints.append({"stage": stage, "n_rows": int(n_rows)})

    def finalize(self, final_df: pd.DataFrame, manifest_path: Path) -> dict:
        label_counts = (
            final_df["label"].value_counts().to_dict() if "label" in final_df.columns else {}
        )
        manifest = {
            "dataset_key": self.key,
            "dataset_name": self.spec.name,
            "modality": self.spec.modality,
            "task": self.spec.task,
            "source": self.spec.source,
            "dataset_version": self.spec.dataset_version,
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "pipeline_version": self.cfg["pipeline_version"],
            "pipeline_run_started_at": self.started_at,
            "pipeline_run_finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "row_count_checkpoints": self.checkpoints,
            "final_row_count": int(len(final_df)),
            "final_label_distribution": {str(k): int(v) for k, v in label_counts.items()},
        }
        ensure_dir(manifest_path.parent)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest
