"""
schema_normalization.py
------------------------
Maps each dataset's raw, heterogeneous schema onto ONE common canonical
schema so that every downstream module (Claim Verification, Fusion Model,
etc.) can consume a single consistent interface regardless of which
original dataset a row came from.

Canonical schema (one row = one example):
    id            : str   - unique id, prefixed by dataset name
    dataset       : str   - source dataset identifier
    task          : str   - one of {fake_news, claim_verification,
                                     fact_checking, ai_text_detection,
                                     image_forensics}
    text          : str   - primary text field (article body / claim / statement)
    text_secondary: str   - optional secondary text (e.g. evidence, headline)
    label_raw     : str   - original label string/value as given by the source
    label         : int   - normalized integer label (see label_mapping.py)
    metadata      : str   - JSON-encoded dict of any extra original fields
    image_path    : str   - populated only for image_forensics rows; else ""
"""

import json
import pandas as pd

CANONICAL_COLUMNS = [
    "id", "dataset", "task", "text", "text_secondary",
    "label_raw", "label", "metadata", "image_path",
]

# Columns produced by the normalize_* functions below, BEFORE label_mapping.py
# adds the integer `label` column. Kept separate from CANONICAL_COLUMNS so
# normalization doesn't fail trying to select a column that doesn't exist yet.
PRE_LABEL_COLUMNS = [c for c in CANONICAL_COLUMNS if c != "label"]


def _make_ids(dataset: str, n: int) -> list:
    return [f"{dataset}_{i:07d}" for i in range(n)]


def normalize_fake_real_news(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns expected: title, text, subject, date, label ('Fake'/'True')."""
    out = pd.DataFrame()
    out["text"] = df["text"]
    out["text_secondary"] = df.get("title", "")
    out["label_raw"] = df["label"]
    extra_cols = [c for c in df.columns if c not in ("text", "title", "label")]
    out["metadata"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    out["metadata"] = out["metadata"].apply(json.dumps)
    out["dataset"] = "fake_real_news"
    out["task"] = "fake_news"
    out["image_path"] = ""
    out["id"] = _make_ids("fake_real_news", len(out))
    return out[["id"] + [c for c in PRE_LABEL_COLUMNS if c != "id"]]


def normalize_claim_verification(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns expected (FEVER): claim, label, evidence (optional)."""
    out = pd.DataFrame()
    out["text"] = df["claim"]
    out["text_secondary"] = df.get("evidence_text", "")
    out["label_raw"] = df["label"]
    extra_cols = [c for c in df.columns if c not in ("claim", "label", "evidence_text")]
    out["metadata"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    out["metadata"] = out["metadata"].apply(json.dumps)
    out["dataset"] = "fever"
    out["task"] = "claim_verification"
    out["image_path"] = ""
    out["id"] = _make_ids("fever", len(out))
    return out[["id"] + [c for c in PRE_LABEL_COLUMNS if c != "id"]]


def normalize_fact_checking(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns expected (LIAR): statement, label, subject, speaker, context..."""
    out = pd.DataFrame()
    out["text"] = df["statement"]
    out["text_secondary"] = df.get("context", "")
    out["label_raw"] = df["label"]
    extra_cols = [c for c in df.columns if c not in ("statement", "label", "context")]
    out["metadata"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    out["metadata"] = out["metadata"].apply(json.dumps)
    out["dataset"] = "liar"
    out["task"] = "fact_checking"
    out["image_path"] = ""
    out["id"] = _make_ids("liar", len(out))
    return out[["id"] + [c for c in PRE_LABEL_COLUMNS if c != "id"]]


def normalize_ai_text_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns expected: text, source ('human'/'machine')."""
    out = pd.DataFrame()
    out["text"] = df["text"]
    out["text_secondary"] = ""
    out["label_raw"] = df["source"]
    extra_cols = [c for c in df.columns if c not in ("text", "source")]
    out["metadata"] = df[extra_cols].to_dict(orient="records") if extra_cols else [{}] * len(df)
    out["metadata"] = out["metadata"].apply(json.dumps)
    out["dataset"] = "gpt2_output"
    out["task"] = "ai_text_detection"
    out["image_path"] = ""
    out["id"] = _make_ids("gpt2_output", len(out))
    return out[["id"] + [c for c in PRE_LABEL_COLUMNS if c != "id"]]


def normalize_image_forensics(df: pd.DataFrame) -> pd.DataFrame:
    """Input columns expected: image_path, label ('REAL'/'FAKE')."""
    out = pd.DataFrame()
    out["text"] = ""
    out["text_secondary"] = ""
    out["label_raw"] = df["label"]
    out["metadata"] = [{}] * len(df)
    out["metadata"] = out["metadata"].apply(json.dumps)
    out["dataset"] = "cifake"
    out["task"] = "image_forensics"
    out["image_path"] = df["image_path"]
    out["id"] = _make_ids("cifake", len(out))
    return out[["id"] + [c for c in PRE_LABEL_COLUMNS if c != "id"]]
