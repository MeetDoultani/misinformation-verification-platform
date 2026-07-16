"""
validators.py
--------------
Post-cleaning validation checks. Raises AssertionError with a clear message
if a processed dataset does not meet the minimum quality bar, so problems
are caught before EDA/splitting rather than propagating downstream.
"""

import pandas as pd
from pathlib import Path
from PIL import Image
from src.utils.logging_utils import get_logger
from src.cleaning.schema_normalization import CANONICAL_COLUMNS

logger = get_logger(__name__)


class ValidationError(Exception):
    pass


def validate_schema(df: pd.DataFrame) -> None:
    missing_cols = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing canonical columns: {missing_cols}")


def validate_no_nulls_in_required(df: pd.DataFrame, required_cols: list) -> None:
    for col in required_cols:
        n_null = df[col].isna().sum()
        if n_null > 0:
            raise ValidationError(f"Column '{col}' has {n_null} null values after cleaning.")


def validate_labels(df: pd.DataFrame, allowed_labels: set) -> None:
    bad = set(df["label"].unique()) - allowed_labels
    if bad:
        raise ValidationError(f"Found labels outside the allowed set {allowed_labels}: {bad}")


def validate_text_length(df: pd.DataFrame, min_len: int = 3, max_len: int = 100_000) -> dict:
    """Returns counts of rows outside bounds rather than hard-failing (informational)."""
    lengths = df["text"].str.len()
    too_short = (lengths < min_len).sum()
    too_long = (lengths > max_len).sum()
    if too_short:
        logger.warning(f"{too_short} rows have text shorter than {min_len} chars.")
    if too_long:
        logger.warning(f"{too_long} rows have text longer than {max_len} chars (consider truncation).")
    return {"too_short": int(too_short), "too_long": int(too_long)}


def validate_image_files(df: pd.DataFrame, image_path_col: str = "image_path") -> dict:
    """
    For image_forensics rows: verify each file exists and opens as a valid
    image. Returns a dict of {valid, corrupt, missing} counts. Does not
    load full-resolution pixel data into memory beyond PIL's verify() check.
    """
    valid, corrupt, missing = 0, 0, 0
    for p in df[image_path_col]:
        if not p:
            continue
        path = Path(p)
        if not path.exists():
            missing += 1
            continue
        try:
            with Image.open(path) as img:
                img.verify()
            valid += 1
        except Exception:
            corrupt += 1
    result = {"valid": valid, "corrupt": corrupt, "missing": missing}
    logger.info(f"Image validation: {result}")
    return result


def run_all_validations(df: pd.DataFrame, allowed_labels: set, required_cols=None) -> None:
    """Convenience wrapper: run the standard validation suite on a processed dataset."""
    required_cols = required_cols or ["id", "dataset", "task", "label"]
    validate_schema(df)
    validate_no_nulls_in_required(df, required_cols)
    validate_labels(df, allowed_labels)
    logger.info(f"All validations passed for dataset with {len(df)} rows.")
