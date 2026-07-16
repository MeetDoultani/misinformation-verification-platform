"""
test_cleaning.py
-----------------
Unit tests for the reusable cleaning modules. Run with: pytest tests/
These use small synthetic DataFrames so they run in milliseconds and do not
depend on any downloaded dataset.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.cleaning.text_cleaning import clean_text, strip_urls, strip_html, normalize_whitespace
from src.cleaning.deduplication import drop_exact_duplicates, drop_near_duplicates
from src.cleaning.missing_values import drop_rows_missing_required, missing_value_report
from src.cleaning.label_mapping import apply_label_map


def test_strip_html():
    assert strip_html("<p>Hello <b>World</b></p>") == " Hello  World  "


def test_strip_urls():
    text = "Check this out https://example.com/page and www.test.com too"
    result = strip_urls(text)
    assert "http" not in result and "www." not in result


def test_normalize_whitespace():
    assert normalize_whitespace("Hello    World\n\n\n\nBye") == "Hello World\n\nBye"


def test_clean_text_full_pipeline():
    raw = "WASHINGTON (Reuters) - The   president said <b>hello</b> https://x.com today.  "
    cleaned = clean_text(raw)
    assert "Reuters" not in cleaned
    assert "<b>" not in cleaned
    assert "http" not in cleaned
    assert cleaned == cleaned.strip()


def test_drop_exact_duplicates():
    df = pd.DataFrame({"text": ["a", "a", "b", "c", "c"]})
    out = drop_exact_duplicates(df, subset=["text"])
    assert len(out) == 3


def test_drop_near_duplicates():
    df = pd.DataFrame({"text": ["Hello World!", "hello   world", "Goodbye"]})
    out = drop_near_duplicates(df, text_col="text")
    assert len(out) == 2


def test_drop_rows_missing_required():
    # "ok" and "fine" are valid; "" is empty-string-missing; None is null-missing.
    # Both should be dropped, leaving 2 valid rows.
    df = pd.DataFrame({"text": ["ok", "", None, "fine"], "label_raw": ["a", "b", "c", "d"]})
    out = drop_rows_missing_required(df, required_cols=["text"])
    assert len(out) == 2
    assert set(out["text"]) == {"ok", "fine"}


def test_missing_value_report_shape():
    df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "", "z"]})
    report = missing_value_report(df)
    assert set(report["column"]) == {"a", "b"}


def test_apply_label_map_unmapped_flagged():
    df = pd.DataFrame({"label_raw": ["Fake", "True", "Unknown"]})
    out = apply_label_map(df, {"Fake": 0, "True": 1})
    assert list(out["label"]) == [0, 1, -1]
