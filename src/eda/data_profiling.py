"""
data_profiling.py
------------------
Richer data-quality profiling, complementary to `generate_eda_report.py`.
Where the basic EDA report answers "what does this dataset look like"
(size, class balance, missing values, length distribution), this module
answers "is this dataset trustworthy and free of subtle quality issues" --
the questions you'd want answered before training anything on it:

  - Per-column cardinality / uniqueness (helps spot near-constant or
    accidentally-leaky columns in `metadata`).
  - Label-conditioned text length statistics: do fake/real (or
    supports/refutes/etc.) examples differ systematically in length? A
    large gap is a red flag for a trivial shortcut a classifier could
    exploit instead of learning real signal.
  - Outlier detection on text length via IQR, flagging rows that are
    unusually short/long for manual spot-checking.
  - Language distribution (via langdetect) -- flags contamination by
    non-target-language rows.
  - Bigram statistics in addition to unigrams (basic EDA only covers
    unigrams).
  - For images: file size and resolution distribution, format counts,
    and integrity (corrupt/valid/missing) via `validators.validate_image_files`.

This is intentionally a lightweight, dependency-free-beyond-requirements.txt
implementation. For a future phase wanting even deeper profiling (e.g.
full column-interaction analysis, automated anomaly detection), consider
swapping in `ydata-profiling` or `great_expectations` -- both would slot
in here as an alternative profiler using the same processed parquet inputs;
that integration is deliberately not done in this phase to avoid pulling in
a heavyweight dependency for a data-engineering-only deliverable.
"""

import sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.io_utils import load_config, load_dataframe
from src.utils.logging_utils import get_logger
from src.registry.dataset_manager import DatasetManager
from src.cleaning.validators import validate_image_files

logger = get_logger(__name__)

try:
    from langdetect import detect, DetectorFactory, LangDetectException
    DetectorFactory.seed = 42
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False


def column_cardinality(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        n_unique = df[col].nunique(dropna=True)
        rows.append({
            "column": col,
            "n_unique": int(n_unique),
            "pct_unique": round(100 * n_unique / max(len(df), 1), 2),
            "dtype": str(df[col].dtype),
        })
    return pd.DataFrame(rows)


def label_conditioned_length_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Word-count stats broken down per label -- surfaces length-based label leakage."""
    tmp = df.copy()
    tmp["_word_count"] = tmp["text"].str.split().apply(len)
    grouped = tmp.groupby("label")["_word_count"].agg(["count", "mean", "median", "std"]).reset_index()
    grouped.columns = ["label", "count", "mean_words", "median_words", "std_words"]
    return grouped.round(1)


def length_outliers(df: pd.DataFrame, iqr_multiplier: float = 3.0) -> dict:
    """IQR-based outlier detection on word count. Wide multiplier (3x) to
    flag only genuinely extreme rows, not normal variation."""
    word_counts = df["text"].str.split().apply(len)
    q1, q3 = word_counts.quantile(0.25), word_counts.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - iqr_multiplier * iqr, q3 + iqr_multiplier * iqr
    n_low = int((word_counts < lower).sum())
    n_high = int((word_counts > upper).sum())
    return {
        "lower_bound_words": max(0, round(lower)),
        "upper_bound_words": round(upper),
        "n_outliers_short": n_low,
        "n_outliers_long": n_high,
        "pct_outliers": round(100 * (n_low + n_high) / max(len(df), 1), 2),
    }


def language_distribution(df: pd.DataFrame, sample_n: int = 500) -> dict:
    if not _LANGDETECT_AVAILABLE:
        return {"note": "langdetect not installed; language profiling skipped"}
    sample = df["text"].dropna().sample(min(sample_n, len(df)), random_state=42)
    counts = Counter()
    for text in sample:
        text = str(text)
        if len(text) < 10:
            continue
        try:
            counts[detect(text)] += 1
        except LangDetectException:
            counts["unknown"] += 1
    total = sum(counts.values()) or 1
    return {lang: f"{n} ({round(100*n/total, 1)}%)" for lang, n in counts.most_common(5)}


def bigram_stats(df: pd.DataFrame, sample_n: int = 10000, top_k: int = 15) -> list:
    sample = df["text"].dropna().sample(min(sample_n, len(df)), random_state=42)
    counter = Counter()
    for text in sample:
        tokens = [t.lower() for t in str(text).split() if t.isalpha()]
        bigrams = zip(tokens, tokens[1:])
        counter.update(" ".join(b) for b in bigrams)
    return counter.most_common(top_k)


def image_profile(df: pd.DataFrame) -> dict:
    from PIL import Image
    integrity = validate_image_files(df, image_path_col="image_path")

    sizes, formats, file_sizes_kb = [], Counter(), []
    sample_paths = df["image_path"].sample(min(500, len(df)), random_state=42)
    for p in sample_paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            with Image.open(path) as img:
                sizes.append(img.size)
                formats[img.format] += 1
            file_sizes_kb.append(path.stat().st_size / 1024)
        except Exception:
            continue

    widths = [s[0] for s in sizes]
    heights = [s[1] for s in sizes]
    return {
        "integrity": integrity,
        "format_distribution": dict(formats),
        "resolution": {
            "width_mean": round(float(np.mean(widths)), 1) if widths else None,
            "height_mean": round(float(np.mean(heights)), 1) if heights else None,
            "width_min_max": (min(widths), max(widths)) if widths else None,
            "height_min_max": (min(heights), max(heights)) if heights else None,
        },
        "file_size_kb": {
            "mean": round(float(np.mean(file_sizes_kb)), 2) if file_sizes_kb else None,
            "median": round(float(np.median(file_sizes_kb)), 2) if file_sizes_kb else None,
        },
        "sampled_n": len(sizes),
    }


def profile_one_dataset(key: str, manager: DatasetManager) -> str:
    processed_path = manager.processed_path(key)
    lines = [f"\n## {key}\n"]

    if not processed_path.exists():
        lines.append(f"_Skipped: {processed_path} not found. Run cleaning first._\n")
        return "\n".join(lines)

    df = load_dataframe(processed_path)
    spec = manager.get(key)
    lines.append(f"- **Modality:** {spec.modality} | **Task:** {spec.task} | **Dataset version:** {spec.dataset_version}")

    card = column_cardinality(df)
    lines.append(f"\n**Column cardinality:**\n\n{card.to_markdown(index=False)}\n")

    if spec.modality != "image":
        length_stats = label_conditioned_length_stats(df)
        lines.append(f"**Word count by label (label-leakage check):**\n\n{length_stats.to_markdown(index=False)}\n")

        outliers = length_outliers(df)
        lines.append(f"**Length outliers (IQR method):** {outliers}\n")

        lang_dist = language_distribution(df)
        lines.append(f"**Language distribution (sampled):** {lang_dist}\n")

        bigrams = bigram_stats(df)
        bigram_str = ", ".join(f"{b} ({c})" for b, c in bigrams)
        lines.append(f"**Top bigrams:** {bigram_str}\n")
    else:
        img_prof = image_profile(df)
        lines.append(f"**Image integrity:** {img_prof['integrity']}\n")
        lines.append(f"**Format distribution (sampled):** {img_prof['format_distribution']}\n")
        lines.append(f"**Resolution (sampled, n={img_prof['sampled_n']}):** {img_prof['resolution']}\n")
        lines.append(f"**File size KB (sampled):** {img_prof['file_size_kb']}\n")

    return "\n".join(lines)


def main():
    cfg = load_config()
    manager = DatasetManager.from_config(cfg)
    profiling_dir = Path(cfg["paths"]["profiling_dir"])
    if not profiling_dir.is_absolute():
        from src.utils.io_utils import project_path
        profiling_dir = project_path(cfg["paths"]["profiling_dir"])
    profiling_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# Data Profiling Report\n",
        "Deeper quality checks beyond `reports/eda/eda_report.md`: label-conditioned "
        "length stats (leakage check), outlier detection, language distribution, "
        "bigrams, and (for images) resolution/format/integrity profiling.\n",
        "Auto-generated by `src/eda/data_profiling.py`.\n",
    ]
    for key in manager.list_keys():
        report_lines.append(profile_one_dataset(key, manager))

    out_path = profiling_dir / "profiling_report.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    logger.info(f"Profiling report written to {out_path}")


if __name__ == "__main__":
    main()
