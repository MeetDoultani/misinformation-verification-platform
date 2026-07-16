"""
text_cleaning.py
-----------------
Reusable, dataset-agnostic text cleaning functions. Every function takes and
returns a string (or pd.Series where noted), so they compose cleanly and can
be unit tested in isolation (see tests/test_cleaning.py).

Design principle: cleaning is CONSERVATIVE. We normalize whitespace, fix
encoding artifacts, and strip boilerplate/HTML -- we do NOT lowercase,
remove stopwords, or stem, since downstream modules (claim verification,
AI-text detection) may need case and punctuation as signal.
"""

import re
import ftfy
import pandas as pd

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def fix_encoding(text: str) -> str:
    """Repair mojibake / encoding artifacts (e.g. â€™ -> ')."""
    if not isinstance(text, str):
        return text
    return ftfy.fix_text(text)


def strip_html(text: str) -> str:
    if not isinstance(text, str):
        return text
    return _HTML_TAG_RE.sub(" ", text)


def strip_urls(text: str) -> str:
    if not isinstance(text, str):
        return text
    return _URL_RE.sub(" ", text)


def remove_control_chars(text: str) -> str:
    if not isinstance(text, str):
        return text
    return _CONTROL_CHARS_RE.sub("", text)


def normalize_whitespace(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def strip_source_boilerplate(text: str) -> str:
    """
    Some news corpora (e.g. Reuters-sourced articles in ISOT) prefix articles
    with a dateline like 'WASHINGTON (Reuters) - '. This is a distribution
    artifact, not signal, and can leak the label (real articles often carry
    a wire-service dateline, fake ones usually don't) -- so we strip it to
    avoid an easy shortcut for future classifiers.
    """
    if not isinstance(text, str):
        return text
    return re.sub(r"^[A-Z .,\'-]{3,40}\(Reuters\)\s*-\s*", "", text)


def clean_text(text: str, strip_urls_flag: bool = True) -> str:
    """Full conservative cleaning pipeline for a single string."""
    if not isinstance(text, str):
        return ""
    text = fix_encoding(text)
    text = strip_html(text)
    if strip_urls_flag:
        text = strip_urls(text)
    text = strip_source_boilerplate(text)
    text = remove_control_chars(text)
    text = normalize_whitespace(text)
    return text


def clean_text_column(series: pd.Series, strip_urls_flag: bool = True) -> pd.Series:
    """Vectorized helper to clean an entire DataFrame column of text."""
    return series.apply(lambda t: clean_text(t, strip_urls_flag=strip_urls_flag))
