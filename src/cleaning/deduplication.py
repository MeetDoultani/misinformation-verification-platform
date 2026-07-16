"""
deduplication.py
-----------------
Reusable duplicate-detection and removal utilities.
Provides both exact-match and near-duplicate (normalized) dedup, since news
corpora commonly contain re-published or lightly-edited copies of the same
article.
"""

import re
import pandas as pd
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize_for_dedup(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return _NORMALIZE_RE.sub("", text.lower())


def drop_exact_duplicates(df: pd.DataFrame, subset: list) -> pd.DataFrame:
    """Drop exact duplicate rows based on the given columns."""
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)
    after = len(df)
    logger.info(f"Exact dedup on {subset}: removed {before - after} rows ({before} -> {after}).")
    return df


def drop_near_duplicates(df: pd.DataFrame, text_col: str) -> pd.DataFrame:
    """
    Drop near-duplicates by comparing a normalized (lowercased,
    punctuation/whitespace-stripped) version of the text column. Catches
    cases that differ only by capitalization, punctuation, or spacing.
    """
    before = len(df)
    norm_col = "_dedup_key"
    df[norm_col] = df[text_col].apply(_normalize_for_dedup)
    df = df.drop_duplicates(subset=[norm_col], keep="first").reset_index(drop=True)
    df = df.drop(columns=[norm_col])
    after = len(df)
    logger.info(f"Near-dedup on normalized '{text_col}': removed {before - after} rows ({before} -> {after}).")
    return df


def duplicate_report(df: pd.DataFrame, text_col: str) -> dict:
    """Compute duplicate statistics without mutating the DataFrame (for EDA)."""
    exact_dupes = df.duplicated(subset=[text_col]).sum()
    norm_series = df[text_col].apply(_normalize_for_dedup)
    near_dupes = norm_series.duplicated().sum()
    return {
        "total_rows": len(df),
        "exact_duplicate_rows": int(exact_dupes),
        "near_duplicate_rows": int(near_dupes),
        "exact_duplicate_pct": float(round(100 * exact_dupes / max(len(df), 1), 2)),
        "near_duplicate_pct": float(round(100 * near_dupes / max(len(df), 1), 2)),
    }
