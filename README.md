# Multimodal Neuro-Symbolic Misinformation Verification Platform
## Phase 1 — Data Engineering

This repository contains the **data engineering foundation** for a larger
research platform. It downloads, cleans, validates, analyzes, and splits
five public datasets covering fake news, claim verification, fact
checking, image forensics, and AI-generated text detection — producing a
clean, canonical, reusable dataset layer for future project phases.

**Scope of this phase (and only this phase):** dataset selection,
acquisition, cleaning, EDA, and splitting. No models, embeddings,
knowledge graphs, APIs, or frontends are built here — see
`future_modules/` for where those will live.

## Quick Start

```bash
pip install -r requirements.txt
bash scripts/run_pipeline.sh
```

Two of the five datasets (ISOT Fake/Real News, CIFAKE) require a free
Kaggle account and API token — the pipeline will detect this and print
exact manual-download instructions. See **`docs/datasets.md`** for the
full checklist.

## Project Structure

```
misinfo-verification-platform/
├── config/config.yaml           # all paths, dataset URLs, label maps, split ratios
├── data/
│   ├── raw/                     # untouched downloaded files, one folder per dataset
│   ├── interim/                 # scratch space for intermediate steps
│   ├── processed/               # cleaned, canonical-schema .parquet per dataset
│   └── splits/                  # train/val/test .parquet per dataset
├── src/
│   ├── download/                # per-dataset + orchestrator download scripts
│   ├── cleaning/                # text cleaning, dedup, missing values,
│   │                             # schema normalization, label mapping, validators
│   ├── eda/                     # EDA report generator
│   ├── splitting/                # reproducible train/val/test split logic
│   └── utils/                   # shared logging + I/O helpers
├── reports/
│   ├── eda/eda_report.md        # generated EDA report
│   └── figures/                 # generated plots
├── docs/                        # full documentation (see below)
├── tests/                       # unit tests for cleaning modules
├── scripts/run_pipeline.sh      # runs download -> clean -> EDA -> split
└── future_modules/              # empty placeholders for later phases:
    claim_verification/ knowledge_graph/ image_forensics/
    ai_text_detection/ fusion_model/ backend/ frontend/
```

## Documentation

- **`docs/datasets.md`** — every dataset: justification, size, schema, license, manual-download steps
- **`docs/preprocessing.md`** — exact cleaning pipeline, step by step
- **`docs/assumptions_and_limitations.md`** — assumptions made and known limitations
- **`docs/pipeline_usage.md`** — how to run each stage, expected outputs

## Datasets at a Glance

| Dataset | Task | Rows (approx) | Auto-downloadable |
|---|---|---|---|
| ISOT Fake and Real News | fake_news | ~44.9K | No (Kaggle) |
| FEVER | claim_verification | ~225K | Yes |
| LIAR | fact_checking | ~12.8K | Yes |
| CIFAKE | image_forensics | 120K images | No (Kaggle) |
| GPT-2 Output Dataset | ai_text_detection | ~500K | Yes |

## Testing

```bash
pytest tests/ -v
```

The full pipeline (download → clean → EDA → split) has been smoke-tested
end-to-end against structurally-equivalent synthetic data standing in for
each dataset's real schema; all cleaning/EDA/splitting logic runs
successfully and produces valid output. Re-run against your real
downloads to validate on production data.
