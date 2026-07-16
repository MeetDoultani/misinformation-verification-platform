"""
split_datasets.py
------------------
Creates reproducible train/validation/test splits for each cleaned dataset.

Ratios: 80% train / 10% val / 10% test (configurable in config.yaml).
This ratio is chosen because:
  - Datasets here range from ~10K (LIAR) to ~500K+ (GPT-2 output) rows;
    an 80/10/10 split leaves a statistically meaningful validation and
    test set even for the smaller datasets, while maximizing training
    data for the larger ones.
  - 10% test is enough to get stable accuracy/F1 estimates (thousands of
    examples even for LIAR) without starving the training set.
  - Stratification on `label` keeps class balance consistent across splits,
    which matters because several datasets (e.g. LIAR's 6-way labels) are
    not perfectly balanced.

A fixed random_seed (default 42, set in config.yaml) makes every split
reproducible across machines and reruns.
"""

import sys
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.io_utils import load_config, project_path, save_dataframe, load_dataframe
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def stratified_split(df: pd.DataFrame, train_ratio: float, val_ratio: float,
                      test_ratio: float, seed: int, stratify: bool):
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"

    strat_col = df["label"] if stratify else None
    train_df, temp_df = train_test_split(
        df, train_size=train_ratio, random_state=seed, stratify=strat_col
    )

    remaining_ratio = val_ratio + test_ratio
    strat_col_temp = temp_df["label"] if stratify else None
    val_df, test_df = train_test_split(
        temp_df, train_size=val_ratio / remaining_ratio, random_state=seed, stratify=strat_col_temp
    )

    return (train_df.reset_index(drop=True),
            val_df.reset_index(drop=True),
            test_df.reset_index(drop=True))


def split_one_dataset(key: str, cfg: dict):
    processed_path = project_path(cfg["paths"]["processed_dir"]) / f"{key}.parquet"
    if not processed_path.exists():
        logger.warning(f"[{key}] {processed_path} not found, skipping split. Run cleaning first.")
        return

    df = load_dataframe(processed_path)
    split_cfg = cfg["splitting"]

    # Guard: stratification requires every class to have >= 2 members
    can_stratify = split_cfg["stratify"] and df["label"].value_counts().min() >= 2
    if split_cfg["stratify"] and not can_stratify:
        logger.warning(f"[{key}] Some classes have <2 examples; disabling stratification for this dataset.")

    train_df, val_df, test_df = stratified_split(
        df,
        train_ratio=split_cfg["train_ratio"],
        val_ratio=split_cfg["val_ratio"],
        test_ratio=split_cfg["test_ratio"],
        seed=split_cfg["random_seed"],
        stratify=can_stratify,
    )

    splits_dir = project_path(cfg["paths"]["splits_dir"]) / key
    save_dataframe(train_df, splits_dir / "train.parquet")
    save_dataframe(val_df, splits_dir / "val.parquet")
    save_dataframe(test_df, splits_dir / "test.parquet")

    logger.info(
        f"[{key}] Split -> train={len(train_df)} val={len(val_df)} test={len(test_df)} "
        f"(seed={split_cfg['random_seed']}) saved to {splits_dir}"
    )


def main():
    cfg = load_config()
    for key in cfg["datasets"]:
        split_one_dataset(key, cfg)


if __name__ == "__main__":
    main()
