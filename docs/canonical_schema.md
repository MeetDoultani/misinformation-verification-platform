# Canonical Schema

Every one of the 5 source datasets is normalized onto one of three typed
records, defined in `src/schema/canonical_schema.py`, before being
flattened into the physical storage table (`data/processed/*.parquet`).

## Why three types instead of one

Articles, claims, and images are genuinely different shapes of data.
Forcing them into one over-generic table with the same field names for
everything would make the field names lie (what does "headline" mean for
a claim? what does "evidence" mean for a news article?). Instead:

| Modality | Used by | Type-specific fields |
|---|---|---|
| **Article** | `fake_real_news`, `ai_text_detection` | `body`, `headline` |
| **Claim** | `claim_verification` (FEVER), `fact_checking` (LIAR) | `claim_text`, `evidence_or_context` |
| **Image** | `image_forensics` (CIFAKE) | `image_path` |

All three share a `BaseRecord`: `id`, `dataset`, `task`, `label_raw`,
`metadata` (a dict of anything source-specific that doesn't fit elsewhere,
e.g. LIAR's speaker/party fields).

## Physical storage shape

Even though the three types are logically distinct, `to_row()` flattens
each of them into **one shared physical column set**, because the future
Fusion Model needs to query across modalities without three different
loaders:

```
id, dataset, task, modality,
text, text_secondary, image_path,
label_raw, label,
metadata,
schema_version, dataset_version, pipeline_version, ingested_at
```

- `text` / `text_secondary` hold `body`/`headline` for articles or
  `claim_text`/`evidence_or_context` for claims; both are empty strings
  (not null) for images.
- `image_path` is populated only for the image modality.
- `modality` (`article` | `claim` | `image`) lets any downstream reader
  filter/query by data type without inspecting `task`.
- The last four columns are lineage/version metadata -- see
  `docs/lineage.md`.

## Adding a new modality or dataset

1. Add a dataclass to `src/schema/canonical_schema.py` if it's a genuinely
   new modality (e.g. `VideoRecord`), or reuse `ArticleRecord`/`ClaimRecord`/
   `ImageRecord` if the new dataset fits an existing shape.
2. Write a `normalize_<dataset>()` function in
   `src/cleaning/schema_normalization.py` that builds a list of records
   and calls `_records_to_df()`.
3. Add an entry to `config/datasets.yaml` with the right `modality`.
4. Register the loader/normalizer pair in `DATASET_PIPELINE` inside
   `src/cleaning/clean_datasets.py`.

No other file needs to change -- the `DatasetManager`, EDA, profiling, and
splitting scripts all iterate generically over whatever is registered.

## Schema versioning

`CANONICAL_SCHEMA_VERSION` (currently `"1.0"`) is stamped into every row.
Bump it whenever you add/remove/rename a canonical column or change what
a field means -- this lets a future consumer detect "this parquet file
was written against an older schema" rather than silently assuming
compatibility.
