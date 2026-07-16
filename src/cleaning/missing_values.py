"""
missing_values.py
------------------
Reusable missing-value detection and handling. Strategy is deliberately
explicit per-column rather than a single blanket dropna(), since different
datasets/columns warrant different treatment (e.g. a missing 'subject' in
a news article is tolerable, a missing 'text' is not).
"""

import pandas as pd
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def missing_value_report(df: pd.DataFrame) -> pd.DataFrame:
    """Return a per-column summary of missing/empty values."""
    report = []
    for col in df.columns:
        n_null = df[col].isna().sum()
        n_empty_str = 0
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            n_empty_str = (df[col].astype(str).str.strip() == "").sum()
        report.append({
            "column": col,
            "n_missing_null": int(n_null),
            "n_missing_empty_string": int(n_empty_str),
            "pct_missing": round(100 * (n_null + n_empty_str) / max(len(df), 1), 2),
        })
    return pd.DataFrame(report).sort_values("pct_missing", ascending=False).reset_index(drop=True)


def drop_rows_missing_required(df: pd.DataFrame, required_cols: list) -> pd.DataFrame:
    """
    Drop rows where any required column is null OR an empty/whitespace string.
    Required columns are typically the primary text field and the label.
    """
    before = len(df)
    mask = pd.Series(True, index=df.index)
    for col in required_cols:
        not_null = df[col].notna()
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            not_empty = df[col].astype(str).str.strip() != ""
            mask &= (not_null & not_empty)
        else:
            mask &= not_null
    df = df[mask].reset_index(drop=True)
    after = len(df)
    logger.info(f"Dropped {before - after} rows missing required columns {required_cols} ({before} -> {after}).")
    return df


def fill_optional_missing(df: pd.DataFrame, fill_values: dict) -> pd.DataFrame:
    """
    Fill non-critical missing columns with sensible defaults, e.g.
    {'subject': 'unknown', 'author': 'unknown'}. Keeps rows instead of
    dropping them when the missing field is not essential for the label.
    """
    for col, default in fill_values.items():
        if col in df.columns:
            n_filled = df[col].isna().sum()
            df[col] = df[col].fillna(default)
            if n_filled:
                logger.info(f"Filled {n_filled} missing values in '{col}' with '{default}'.")
    return df
