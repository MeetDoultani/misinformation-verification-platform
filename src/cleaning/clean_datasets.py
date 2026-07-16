"""
clean_datasets.py
------------------
Main cleaning orchestrator. For each of the 5 datasets:
  1. Load raw files (format differs per dataset: CSV, JSONL, TSV, image folders).
  2. Normalize to the canonical schema (schema_normalization.py).
  3. Clean text (text_cleaning.py).
  4. Handle missing values (missing_values.py).
  5. Remove duplicates (deduplication.py).
  6. Apply label mapping (label_mapping.py).
  7. Validate (validators.py).
  8. Save to data/processed/<dataset>.parquet

If a dataset's raw files are not found, this script logs a clear warning
and SKIPS that dataset (it does not crash the whole run), so the user can
clean whatever datasets they've already downloaded.
"""

import sys
import json
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.io_utils import load_config, save_dataframe, project_path
from src.utils.logging_utils import get_logger
from src.cleaning import schema_normalization as norm
from src.cleaning.text_cleaning import clean_text_column
from src.cleaning.missing_values import drop_rows_missing_required, missing_value_report
from src.cleaning.deduplication import drop_exact_duplicates, drop_near_duplicates
from src.cleaning.label_mapping import apply_label_map
from src.cleaning.validators import run_all_validations, validate_text_length, ValidationError

logger = get_logger(__name__)


def _clean_common(df: pd.DataFrame, cfg: dict, is_image: bool = False) -> pd.DataFrame:
    """Shared cleaning steps applied after schema normalization, for all tasks."""
    cleaning_cfg = cfg["cleaning"]

    if not is_image:
        df["text"] = clean_text_column(df["text"])
        df = drop_rows_missing_required(df, required_cols=["text", "label_raw"])
        df = drop_exact_duplicates(df, subset=["text"])
        df = drop_near_duplicates(df, text_col="text")
        validate_text_length(df, cleaning_cfg["min_text_length"], cleaning_cfg["max_text_length"])
    else:
        df = drop_rows_missing_required(df, required_cols=["image_path", "label_raw"])
        df = drop_exact_duplicates(df, subset=["image_path"])

    return df.reset_index(drop=True)


# --------------------------------------------------------------------------
# Loaders: raw file -> raw DataFrame (dataset-specific schema, NOT canonical)
# --------------------------------------------------------------------------

def load_raw_fake_real_news(raw_dir: Path) -> pd.DataFrame:
    fake_path, true_path = raw_dir / "Fake.csv", raw_dir / "True.csv"
    if not (fake_path.exists() and true_path.exists()):
        raise FileNotFoundError(f"Expected Fake.csv and True.csv in {raw_dir}")
    fake = pd.read_csv(fake_path)
    true = pd.read_csv(true_path)
    fake["label"] = "Fake"
    true["label"] = "True"
    return pd.concat([fake, true], ignore_index=True)


def load_raw_claim_verification(raw_dir: Path) -> pd.DataFrame:
    train_path = raw_dir / "train.jsonl"
    if not train_path.exists():
        raise FileNotFoundError(f"Expected train.jsonl in {raw_dir}")
    records = []
    with open(train_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


def load_raw_fact_checking(raw_dir: Path) -> pd.DataFrame:
    train_path = raw_dir / "train.tsv"
    if not train_path.exists():
        raise FileNotFoundError(f"Expected train.tsv in {raw_dir}")
    # LIAR dataset has no header row; columns per the official README
    cols = [
        "id", "label", "statement", "subject", "speaker", "speaker_job",
        "state_info", "party", "barely_true_c", "false_c", "half_true_c",
        "mostly_true_c", "pants_fire_c", "context",
    ]
    df = pd.read_csv(train_path, sep="\t", header=None, names=cols)
    return df


def load_raw_ai_text_detection(raw_dir: Path) -> pd.DataFrame:
    human_path = raw_dir / "webtext.train.jsonl"
    machine_path = raw_dir / "small-117M.train.jsonl"
    if not (human_path.exists() and machine_path.exists()):
        raise FileNotFoundError(f"Expected webtext.train.jsonl and small-117M.train.jsonl in {raw_dir}")

    def _load(path, source):
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    records.append({"text": d.get("text", ""), "source": source})
        return records

    rows = _load(human_path, "human") + _load(machine_path, "machine")
    return pd.DataFrame(rows)


def load_raw_image_forensics(raw_dir: Path) -> pd.DataFrame:
    records = []
    for label_name in ("REAL", "FAKE"):
        for split in ("train", "test"):
            folder = raw_dir / split / label_name
            if folder.exists():
                for img_path in folder.glob("*"):
                    if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        records.append({"image_path": str(img_path), "label": label_name})
    if not records:
        raise FileNotFoundError(f"No images found under {raw_dir}/{{train,test}}/{{REAL,FAKE}}")
    return pd.DataFrame(records)


# --------------------------------------------------------------------------
# Per-dataset pipeline
# --------------------------------------------------------------------------

DATASET_PIPELINE = {
    "fake_real_news": (load_raw_fake_real_news, norm.normalize_fake_real_news, False),
    "claim_verification": (load_raw_claim_verification, norm.normalize_claim_verification, False),
    "fact_checking": (load_raw_fact_checking, norm.normalize_fact_checking, False),
    "ai_text_detection": (load_raw_ai_text_detection, norm.normalize_ai_text_detection, False),
    "image_forensics": (load_raw_image_forensics, norm.normalize_image_forensics, True),
}


def clean_one_dataset(key: str, cfg: dict) -> pd.DataFrame:
    ds_cfg = cfg["datasets"][key]
    raw_dir = project_path(ds_cfg["raw_subdir"])
    loader, normalizer, is_image = DATASET_PIPELINE[key]

    logger.info(f"--- Cleaning dataset: {key} ---")
    raw_df = loader(raw_dir)
    logger.info(f"[{key}] Loaded {len(raw_df)} raw rows.")

    df = normalizer(raw_df)
    df = _clean_common(df, cfg, is_image=is_image)
    df = apply_label_map(df, ds_cfg["label_map"])
    df = df[df["label"] != -1].reset_index(drop=True)  # drop unmapped labels

    allowed_labels = set(ds_cfg["label_map"].values())
    try:
        run_all_validations(df, allowed_labels)
    except ValidationError as e:
        logger.error(f"[{key}] Validation failed: {e}")
        raise

    out_path = project_path(cfg["paths"]["processed_dir"]) / f"{key}.parquet"
    save_dataframe(df, out_path)
    logger.info(f"[{key}] Saved {len(df)} cleaned rows -> {out_path}")

    miss_report = missing_value_report(df)
    logger.info(f"[{key}] Post-clean missing-value report:\n{miss_report.to_string(index=False)}")

    return df


def main():
    cfg = load_config()
    summary = {}
    for key in DATASET_PIPELINE:
        try:
            df = clean_one_dataset(key, cfg)
            summary[key] = f"OK ({len(df)} rows)"
        except FileNotFoundError as e:
            summary[key] = f"SKIPPED - raw files not found ({e})"
            logger.warning(f"[{key}] Skipping: {e}")
        except Exception as e:
            summary[key] = f"FAILED - {e}"
            logger.error(f"[{key}] Failed: {e}")

    print("\n" + "#" * 78)
    print("CLEANING SUMMARY")
    print("#" * 78)
    for k, v in summary.items():
        print(f"  {k:22s}: {v}")
    print("#" * 78 + "\n")


if __name__ == "__main__":
    main()
