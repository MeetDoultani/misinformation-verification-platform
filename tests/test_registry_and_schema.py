"""
test_registry_and_schema.py
----------------------------
Unit tests for the DatasetManager registry, canonical schema dataclasses,
and lineage stamping added in the Phase 1 revision.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.utils.io_utils import load_config
from src.registry.dataset_manager import DatasetManager, DatasetSpec
from src.schema.canonical_schema import (
    ArticleRecord, ClaimRecord, ImageRecord, CANONICAL_COLUMNS, CANONICAL_SCHEMA_VERSION,
)
from src.lineage.lineage import stamp_lineage_columns, LineageTracker


def test_load_config_merges_three_files():
    cfg = load_config()
    assert "paths" in cfg and "datasets" in cfg and "cleaning" in cfg and "splitting" in cfg
    assert "pipeline_version" in cfg
    assert len(cfg["datasets"]) == 5


def test_dataset_manager_lists_all_datasets():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    assert set(manager.list_keys()) == {
        "fake_real_news", "claim_verification", "fact_checking",
        "image_forensics", "ai_text_detection",
    }


def test_dataset_manager_modality_grouping():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    assert set(manager.by_modality("article")) == {"fake_real_news", "ai_text_detection"}
    assert set(manager.by_modality("claim")) == {"claim_verification", "fact_checking"}
    assert set(manager.by_modality("image")) == {"image_forensics"}


def test_dataset_manager_get_returns_typed_spec():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    spec = manager.get("fact_checking")
    assert isinstance(spec, DatasetSpec)
    assert spec.modality == "claim"
    assert spec.label_map["true"] == 5


def test_dataset_manager_unknown_key_raises():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    try:
        manager.get("nonexistent_dataset")
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_dataset_manager_register_new_dataset():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    new_spec = DatasetSpec(
        key="test_ds", name="Test Dataset", modality="claim", task="test_task",
        source="url", dataset_version="v1", raw_subdir="data/raw/test_ds", label_map={},
    )
    manager.register("test_ds", new_spec)
    assert "test_ds" in manager.list_keys()
    assert manager.get("test_ds").name == "Test Dataset"


def test_article_record_to_row_shape():
    rec = ArticleRecord(id="a1", dataset="fake_real_news", task="fake_news",
                         label_raw="Fake", metadata={"subject": "politics"},
                         body="some body text", headline="a headline")
    row = rec.to_row()
    assert row["modality"] == "article"
    assert row["text"] == "some body text"
    assert row["text_secondary"] == "a headline"
    assert row["image_path"] == ""


def test_claim_record_to_row_shape():
    rec = ClaimRecord(id="c1", dataset="liar", task="fact_checking",
                       label_raw="true", metadata={}, claim_text="a claim",
                       evidence_or_context="some context")
    row = rec.to_row()
    assert row["modality"] == "claim"
    assert row["text"] == "a claim"
    assert row["text_secondary"] == "some context"


def test_image_record_to_row_shape():
    rec = ImageRecord(id="i1", dataset="cifake", task="image_forensics",
                       label_raw="REAL", metadata={}, image_path="/path/to/img.jpg")
    row = rec.to_row()
    assert row["modality"] == "image"
    assert row["image_path"] == "/path/to/img.jpg"
    assert row["text"] == ""


def test_stamp_lineage_columns():
    df = pd.DataFrame({"text": ["a", "b"], "label": [0, 1]})
    stamped = stamp_lineage_columns(df, dataset_version="v1.0", pipeline_version="1.1.0")
    assert stamped["schema_version"].iloc[0] == CANONICAL_SCHEMA_VERSION
    assert stamped["dataset_version"].iloc[0] == "v1.0"
    assert stamped["pipeline_version"].iloc[0] == "1.1.0"
    assert "ingested_at" in stamped.columns


def test_lineage_tracker_checkpoints_and_manifest(tmp_path):
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    spec = manager.get("fact_checking")
    tracker = LineageTracker("fact_checking", spec, cfg)
    tracker.checkpoint("raw_loaded", 100)
    tracker.checkpoint("after_dedup", 95)

    df = pd.DataFrame({"label": [0, 1, 0, 1, 1]})
    manifest_path = tmp_path / "fact_checking.lineage.json"
    manifest = tracker.finalize(df, manifest_path)

    assert manifest_path.exists()
    assert manifest["dataset_key"] == "fact_checking"
    assert manifest["final_row_count"] == 5
    assert len(manifest["row_count_checkpoints"]) == 2
    assert manifest["final_label_distribution"]["1"] == 3


def test_canonical_columns_include_lineage_fields():
    for col in ("schema_version", "dataset_version", "pipeline_version", "ingested_at", "modality"):
        assert col in CANONICAL_COLUMNS
