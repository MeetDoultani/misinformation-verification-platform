# Dataset Manager / Registry

`src/registry/dataset_manager.py` centralizes everything the pipeline
needs to know about a dataset, so download/clean/EDA/profiling/splitting
scripts don't each duplicate config-parsing and path-building logic.

## Core objects

**`DatasetSpec`** -- a typed, dataclass view of one entry in
`config/datasets.yaml` (name, modality, task, source, dataset_version,
raw_subdir, label_map, plus anything dataset-specific like `kaggle_slug`
or `urls` in an `extra` dict).

**`DatasetManager`** -- holds a `dict[str, DatasetSpec]` and exposes:

```python
manager = DatasetManager.from_config(cfg)

manager.list_keys()                  # ['fake_real_news', 'claim_verification', ...]
manager.get("fact_checking")         # -> DatasetSpec
manager.by_modality("claim")         # -> ['claim_verification', 'fact_checking']
manager.by_task("fact_checking")     # -> ['fact_checking']

manager.raw_dir("fact_checking")     # -> Path(.../data/raw/fact_checking)
manager.processed_path("fact_checking")  # -> Path(.../data/processed/fact_checking.parquet)
manager.splits_dir("fact_checking")  # -> Path(.../data/splits/fact_checking)
manager.lineage_path("fact_checking")    # -> Path(.../data/processed/_lineage/fact_checking.lineage.json)
manager.profiling_path("fact_checking")  # -> Path(.../reports/profiling/fact_checking_profile.md)

manager.status("fact_checking")      # -> {"downloaded": bool, "cleaned": bool, "split": bool}
manager.status_report()              # -> {key: status_dict, ...} for every dataset

manager.register("new_dataset", DatasetSpec(...))  # add a dataset at runtime (e.g. in tests)
```

## Why this exists

Before this abstraction, every script (`download_*.py`,
`clean_datasets.py`, `generate_eda_report.py`, `split_datasets.py`) read
`cfg["datasets"][key][...]` directly and rebuilt paths like
`project_path(cfg["paths"]["processed_dir"]) / f"{key}.parquet"`
independently. That meant:
- Adding a field to a dataset definition required updating N call sites.
- Path-building logic could silently drift between scripts.
- There was no single place to ask "what state is dataset X in?"

Now every script does `manager = DatasetManager.from_config(cfg)` once
and asks the manager for paths/specs, so path logic and status-checking
live in exactly one place.

## Extending the registry

Adding a 6th dataset requires:
1. An entry in `config/datasets.yaml`.
2. A loader + normalizer pair registered in `DATASET_PIPELINE` in
   `src/cleaning/clean_datasets.py` (see `docs/canonical_schema.md`).
3. (If gated) a downloader class following the pattern in
   `src/download/download_*.py`, added to `DOWNLOADER_CLASSES` in
   `src/download/run_all_downloads.py`.

Nothing in `DatasetManager` itself, nor in the EDA, profiling, or
splitting scripts, needs to change -- they all iterate over
`manager.list_keys()` generically.
