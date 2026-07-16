"""
label_mapping.py
-----------------
Applies the label_map defined in config.yaml to the `label_raw` column,
producing a normalized integer `label` column, and flags any values that
don't match the expected mapping (rather than silently coercing to NaN).
"""

import pandas as pd
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def apply_label_map(df: pd.DataFrame, label_map: dict, raw_col: str = "label_raw") -> pd.DataFrame:
    """
    Map raw string/whatever labels to canonical integers using label_map.
    Rows whose raw label is not found in label_map get label = -1 and are
    logged, so they can be inspected/dropped explicitly rather than
    disappearing silently.
    """
    df = df.copy()

    def _lookup(raw_value):
        # try exact match, then case-insensitive/stripped match
        if raw_value in label_map:
            return label_map[raw_value]
        if isinstance(raw_value, str):
            for k, v in label_map.items():
                if isinstance(k, str) and k.strip().lower() == raw_value.strip().lower():
                    return v
        return -1

    df["label"] = df[raw_col].apply(_lookup)
    n_unmapped = (df["label"] == -1).sum()
    if n_unmapped:
        unmapped_values = df.loc[df["label"] == -1, raw_col].unique()[:10]
        logger.warning(
            f"{n_unmapped} rows had unmapped labels. Sample unmapped values: {list(unmapped_values)}"
        )
    return df


def label_distribution(df: pd.DataFrame, label_col: str = "label") -> pd.DataFrame:
    """Return counts and percentages per label value, for EDA / sanity checks."""
    counts = df[label_col].value_counts(dropna=False)
    pct = (counts / len(df) * 100).round(2)
    return pd.DataFrame({"count": counts, "pct": pct}).reset_index().rename(columns={"index": label_col})
