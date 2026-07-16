"""
io_utils.py
-----------
Shared filesystem / config helpers used across download, cleaning, EDA and
splitting scripts. Keeping these in one place avoids duplicated path logic
and makes the pipeline portable across machines.
"""

import json
import yaml
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load the global YAML config relative to the project root."""
    full_path = PROJECT_ROOT / config_path
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def project_path(relative_path: str) -> Path:
    """Resolve a path relative to the project root, creating parent dirs if needed."""
    p = PROJECT_ROOT / relative_path
    return p


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> list:
    """Read a .jsonl file into a list of dicts. Skips malformed lines with a warning."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[WARN] Skipping malformed JSON line {i} in {path}")
    return records


def write_jsonl(records: list, path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def save_dataframe(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    """Save a DataFrame as CSV or Parquet based on file extension."""
    ensure_dir(path.parent)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=index)
    else:
        df.to_csv(path, index=index)


def load_dataframe(path: Path) -> pd.DataFrame:
    """Load a CSV, Parquet, or JSONL file into a DataFrame based on extension."""
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    elif path.suffix == ".jsonl":
        return pd.DataFrame(read_jsonl(path))
    else:
        return pd.read_csv(path)


def dataset_status(raw_dir: Path, expected_files: list) -> dict:
    """
    Check whether the expected raw files for a dataset are present on disk.
    Used by download scripts to decide whether to skip / warn / instruct the user.
    """
    status = {}
    for fname in expected_files:
        fpath = raw_dir / fname
        status[fname] = fpath.exists() and fpath.stat().st_size > 0
    return status
