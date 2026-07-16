# Preprocessing Documentation

Every dataset flows through the same ordered pipeline
(`src/cleaning/clean_datasets.py`), applying shared, reusable steps so all
five datasets end up in one consistent, high-quality canonical format.

## Pipeline Order

```
raw files
   │
   ▼
1. Load  (dataset-specific loader: CSV / JSONL / TSV / image folder)
   │
   ▼
2. Schema Normalization  (src/cleaning/schema_normalization.py)
   → maps to canonical columns: id, dataset, task, text, text_secondary,
     label_raw, metadata, image_path
   │
   ▼
3. Text Cleaning  (src/cleaning/text_cleaning.py)      [text datasets only]
   → fix encoding, strip HTML/URLs, strip source boilerplate,
     remove control chars, normalize whitespace
   │
   ▼
4. Missing Value Handling  (src/cleaning/missing_values.py)
   → drop rows missing required fields (text/image_path + label_raw)
   │
   ▼
5. Deduplication  (src/cleaning/deduplication.py)
   → exact duplicate removal, then near-duplicate removal via a
     normalized (lowercase, punctuation-stripped) text key
   │
   ▼
6. Label Mapping  (src/cleaning/label_mapping.py)
   → maps label_raw -> canonical integer label per config.yaml;
     unmapped values get label = -1 and are dropped, with a warning
     naming the offending values (never silently discarded without a log)
   │
   ▼
7. Validation  (src/cleaning/validators.py)
   → schema completeness, no unexpected nulls in required columns,
     labels within the allowed set, (for images) file-integrity checks
   │
   ▼
data/processed/<dataset>.parquet
```

## Step-by-Step Detail

### 1. Loading
Each dataset has its own loader function in `clean_datasets.py`
(`load_raw_fake_real_news`, `load_raw_claim_verification`, etc.) because raw
formats genuinely differ (CSV pair, JSONL, headerless TSV, image folder
tree). Loaders raise `FileNotFoundError` with a clear message if the
expected raw files are absent — the orchestrator catches this and **skips**
that dataset rather than crashing the whole run, so partial pipelines
(e.g. only the 3 auto-downloadable datasets) still work end-to-end.

### 2. Schema Normalization
Maps every dataset onto one shared table shape so later modules (Claim
Verification, Fusion Model, etc.) don't need dataset-specific parsing
logic. Extra source-specific fields (e.g. LIAR's speaker/party info) are
preserved as a JSON blob in the `metadata` column rather than being
discarded, in case a later symbolic-reasoning component wants them.

### 3. Text Cleaning
Deliberately **conservative**: normalizes whitespace/encoding and strips
HTML/URLs/wire-service datelines, but does **not** lowercase, remove
stopwords, or stem. Rationale: downstream tasks (claim verification,
AI-text-detection) can be sensitive to case and punctuation as signal
(e.g. detecting AI-generated text often relies on subtle stylistic
patterns that aggressive normalization would destroy).

The Reuters-dateline stripping step exists specifically to prevent a
distribution artifact (real articles carry a wire-service prefix, fake
ones don't) from acting as a trivial shortcut/label-leak for any future
classifier.

### 4. Missing Value Handling
Rows missing their primary content (`text` for text datasets, `image_path`
for the image dataset) or their raw label are dropped — these rows carry
no usable signal. Non-critical metadata fields are allowed to remain
missing (tracked in the EDA report) rather than dropping otherwise-valid
rows over optional fields.

### 5. Deduplication
Two passes:
- **Exact**: identical `text` (or `image_path`) values.
- **Near-duplicate**: text lowercased with all punctuation/whitespace
  stripped, catching re-published articles that differ only in
  capitalization or spacing (common in scraped news corpora).

### 6. Label Mapping
All label vocabularies (`Fake`/`True`, `SUPPORTS`/`REFUTES`/`NOT ENOUGH
INFO`, 6-way LIAR scale, `REAL`/`FAKE`, `human`/`machine`) are mapped to
small integer codes defined centrally in `config/config.yaml`, so every
processed dataset carries both the original string (`label_raw`, for
auditability) and the canonical integer (`label`, for modeling).

### 7. Validation
`run_all_validations()` is the final gate before a dataset is written to
`data/processed/`. It checks: all canonical columns present, no nulls in
required columns, and all labels within the dataset's allowed set. For
images specifically, `validate_image_files()` opens every file with PIL
to catch corrupt/truncated images before they reach later phases.

## Idempotency & Reproducibility
- Downloads skip files that already exist and are non-empty.
- Cleaning re-derives `data/processed/` from `data/raw/` deterministically —
  safe to re-run at any time.
- Splitting uses a fixed `random_seed` (default 42, in `config.yaml`), so
  re-running produces byte-identical splits given the same processed data.
