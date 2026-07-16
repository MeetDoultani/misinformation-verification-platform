# Dataset Lineage & Versioning

Every processed dataset carries two layers of provenance so that a row,
a file, or the whole pipeline run can be traced back to what produced it.

## 1. Row-level stamps

Every row in `data/processed/*.parquet` carries 4 lineage columns,
applied by `src/lineage/lineage.py:stamp_lineage_columns()`:

| Column | Meaning |
|---|---|
| `schema_version` | Which version of the canonical schema (`src/schema/canonical_schema.py`) this row was written against. |
| `dataset_version` | The pinned source-dataset version/snapshot identifier from `config/datasets.yaml` (e.g. `liar-2017-wang`). |
| `pipeline_version` | The pipeline code version from `config/preprocessing.yaml` (bump this when cleaning logic changes in a way that would change output for the same input). |
| `ingested_at` | UTC timestamp of when this row was processed. |

This makes every row self-describing even if it's extracted from the
parquet file in isolation (e.g. copied into a notebook) -- you can always
tell which schema/pipeline/source-snapshot produced it.

## 2. Per-dataset lineage manifests

`src/lineage/lineage.py:LineageTracker` accumulates row-count checkpoints
through the cleaning pipeline (`src/cleaning/clean_datasets.py`) and
writes a JSON manifest to `data/processed/_lineage/<dataset>.lineage.json`
when cleaning finishes. Example structure:

```json
{
  "dataset_key": "fact_checking",
  "dataset_name": "LIAR Dataset",
  "modality": "claim",
  "task": "fact_checking",
  "dataset_version": "liar-2017-wang",
  "schema_version": "1.0",
  "pipeline_version": "1.1.0",
  "pipeline_run_started_at": "...",
  "pipeline_run_finished_at": "...",
  "row_count_checkpoints": [
    {"stage": "raw_loaded", "n_rows": 12791},
    {"stage": "after_schema_normalization", "n_rows": 12791},
    {"stage": "after_missing_value_drop", "n_rows": 12750},
    {"stage": "after_exact_dedup", "n_rows": 12700},
    {"stage": "after_near_dedup", "n_rows": 12650},
    {"stage": "after_label_mapping", "n_rows": 12650}
  ],
  "final_row_count": 12650,
  "final_label_distribution": {"0": 2100, "1": 2110, ...}
}
```

**What this is for:** if a future modeling phase sees an unexpected class
imbalance or a smaller-than-expected dataset, the manifest answers "was
this always the case, or did a cleaning step drop more than expected?"
without re-running the pipeline -- the checkpoint trail shows exactly how
many rows were lost at each stage (missing values vs deduplication vs
unmapped labels).

## Why `dataset_version` is a pinned string, not an auto-detected hash

The 5 source datasets don't have official semantic versions or consistent
release tags (Kaggle snapshots and academic dataset releases rarely do).
`dataset_version` in `config/datasets.yaml` is therefore a deliberately
chosen, human-readable identifier (e.g. `kaggle-snapshot-2023`,
`fever1.0-2018`) documenting when/what version this pipeline was last
verified against. If a source dataset is updated upstream, bump this
string manually so downstream consumers know the data may differ from a
previous run's lineage record.

## Bumping `pipeline_version`

Located in `config/preprocessing.yaml`. Bump it whenever a change to
`src/cleaning/*.py` would produce different output for the same raw
input (e.g. a new cleaning rule, a changed dedup threshold). This is
separate from `dataset_version` (which tracks the *source data*) and
`schema_version` (which tracks the *table shape*) so all three can be
diagnosed independently when auditing a discrepancy.
