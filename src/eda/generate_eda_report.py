"""
generate_eda_report.py
-----------------------
Generates a per-dataset and combined EDA report from the cleaned
data/processed/*.parquet files:
  - dataset sizes
  - class distribution
  - missing values
  - duplicate statistics (recomputed post-clean, should be ~0)
  - text length distribution (chars, words)
  - basic vocabulary statistics (unique tokens, top terms)
  - saves plots to reports/figures/ and a markdown summary to reports/eda/
"""

import sys
from pathlib import Path
from collections import Counter

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.io_utils import load_config, project_path, load_dataframe
from src.utils.logging_utils import get_logger
from src.cleaning.deduplication import duplicate_report
from src.cleaning.missing_values import missing_value_report
from src.cleaning.label_mapping import label_distribution

logger = get_logger(__name__)

STOPWORDS = set("""the a an and or of to in is are was were be been being this that
these those it its for on with as at by from but not no so if then than
""".split())


def text_length_stats(df: pd.DataFrame) -> dict:
    lengths_chars = df["text"].str.len()
    lengths_words = df["text"].str.split().apply(len)
    return {
        "char_len_mean": float(round(lengths_chars.mean(), 1)),
        "char_len_median": int(lengths_chars.median()),
        "char_len_min": int(lengths_chars.min()),
        "char_len_max": int(lengths_chars.max()),
        "word_len_mean": float(round(lengths_words.mean(), 1)),
        "word_len_median": int(lengths_words.median()),
    }, lengths_words


def vocab_stats(df: pd.DataFrame, sample_n: int = 20000) -> dict:
    sample = df["text"].sample(min(sample_n, len(df)), random_state=42)
    counter = Counter()
    for text in sample:
        tokens = [t.lower() for t in str(text).split() if t.isalpha() and t.lower() not in STOPWORDS]
        counter.update(tokens)
    top_terms = counter.most_common(15)
    return {
        "unique_tokens_in_sample": len(counter),
        "top_terms": top_terms,
    }


def plot_length_distribution(word_lengths: pd.Series, dataset_key: str, out_dir: Path):
    plt.figure(figsize=(7, 4))
    word_lengths.clip(upper=word_lengths.quantile(0.99)).hist(bins=50)
    plt.title(f"{dataset_key}: word count distribution (clipped at 99th pct)")
    plt.xlabel("words per example")
    plt.ylabel("frequency")
    plt.tight_layout()
    out_path = out_dir / f"{dataset_key}_word_length_hist.png"
    plt.savefig(out_path, dpi=120)
    plt.close()
    return out_path


def plot_class_distribution(dist_df: pd.DataFrame, dataset_key: str, out_dir: Path):
    plt.figure(figsize=(6, 4))
    plt.bar(dist_df["label"].astype(str), dist_df["count"])
    plt.title(f"{dataset_key}: class distribution")
    plt.xlabel("label")
    plt.ylabel("count")
    plt.tight_layout()
    out_path = out_dir / f"{dataset_key}_class_distribution.png"
    plt.savefig(out_path, dpi=120)
    plt.close()
    return out_path


def eda_for_dataset(key: str, cfg: dict, report_lines: list, figures_dir: Path):
    processed_path = project_path(cfg["paths"]["processed_dir"]) / f"{key}.parquet"
    if not processed_path.exists():
        report_lines.append(f"\n## {key}\n\n_Skipped: {processed_path} not found. Run cleaning first._\n")
        return

    df = load_dataframe(processed_path)
    is_image = key == "image_forensics"

    report_lines.append(f"\n## {key}\n")
    report_lines.append(f"- **Rows:** {len(df)}")

    dist = label_distribution(df)
    report_lines.append(f"- **Class distribution:**\n\n{dist.to_markdown(index=False)}\n")
    fig_path = plot_class_distribution(dist, key, figures_dir)
    report_lines.append(f"  ![class distribution]({fig_path.relative_to(figures_dir.parents[1])})\n")

    miss = missing_value_report(df)
    report_lines.append(f"- **Missing values (post-clean, should be near zero for required fields):**\n\n{miss.to_markdown(index=False)}\n")

    if not is_image:
        dupe = duplicate_report(df, "text")
        report_lines.append(f"- **Duplicate stats (post-clean):** {dupe}")

        stats, word_lengths = text_length_stats(df)
        report_lines.append(f"- **Text length stats:** {stats}")
        fig_path2 = plot_length_distribution(word_lengths, key, figures_dir)
        report_lines.append(f"  ![word length distribution]({fig_path2.relative_to(figures_dir.parents[1])})\n")

        vocab = vocab_stats(df)
        top_terms_str = ", ".join(f"{w} ({c})" for w, c in vocab["top_terms"])
        report_lines.append(f"- **Vocabulary:** {vocab['unique_tokens_in_sample']} unique tokens in sample.")
        report_lines.append(f"  Top terms: {top_terms_str}")
    else:
        report_lines.append("- Text stats N/A (image dataset). Image integrity is checked via `validate_image_files`.")


def main():
    cfg = load_config()
    figures_dir = project_path(cfg["paths"]["figures_dir"])
    figures_dir.mkdir(parents=True, exist_ok=True)
    eda_dir = project_path(cfg["paths"]["eda_dir"])
    eda_dir.mkdir(parents=True, exist_ok=True)

    report_lines = ["# EDA Report\n", "Auto-generated by `src/eda/generate_eda_report.py`.\n"]

    for key in cfg["datasets"]:
        eda_for_dataset(key, cfg, report_lines, figures_dir)

    out_path = eda_dir / "eda_report.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    logger.info(f"EDA report written to {out_path}")


if __name__ == "__main__":
    main()
