# Pipeline Usage Guide

## Setup

```bash
cd misinfo-verification-platform
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

## Run the Full Pipeline

```bash
bash scripts/run_pipeline.sh
```

This runs, in order: downloads → cleaning → EDA → splitting, stopping to
print instructions if a gated dataset needs manual action (it will still
process whatever datasets succeeded).

## Run Stages Individually

```bash
# 1. Download all datasets (auto where possible, prints instructions for gated ones)
python src/download/run_all_downloads.py

# 2. Clean + normalize all datasets into data/processed/*.parquet
python src/cleaning/clean_datasets.py

# 3. Generate the EDA report (reports/eda/eda_report.md + reports/figures/*.png)
python src/eda/generate_eda_report.py

# 4. Create reproducible train/val/test splits (data/splits/<dataset>/{train,val,test}.parquet)
python src/splitting/split_datasets.py
```

## Run Tests

```bash
pytest tests/ -v
```

## Expected Outputs Per Script

| Script | Output |
|---|---|
| `src/download/run_all_downloads.py` | Populated `data/raw/<dataset>/` folders; console summary of OK / manual-action-needed / failed per dataset |
| `src/cleaning/clean_datasets.py` | `data/processed/<dataset>.parquet`, one file per dataset, in the canonical schema |
| `src/eda/generate_eda_report.py` | `reports/eda/eda_report.md`, `reports/figures/*.png` |
| `src/splitting/split_datasets.py` | `data/splits/<dataset>/{train,val,test}.parquet` |

## Where Future Modules Plug In

```
future_modules/
├── claim_verification/   ← consumes data/splits/{claim_verification,fact_checking}/
├── knowledge_graph/      ← consumes data/processed/claim_verification.parquet (evidence/metadata)
├── image_forensics/      ← consumes data/splits/image_forensics/
├── ai_text_detection/    ← consumes data/splits/ai_text_detection/
├── fusion_model/         ← consumes outputs of the above four modules
├── backend/               ← serves the platform via API (not built in this phase)
└── frontend/              ← user-facing UI (not built in this phase)
```

Each `future_modules/<name>/` folder is currently an empty placeholder
(with a `.gitkeep`) reserved for later phases — nothing beyond the data
layer has been implemented here, per the phase scope.

## Re-running After Adding Manually-Downloaded Files
Every script in this pipeline is idempotent and re-checks the filesystem
before doing work — so after placing `Fake.csv`/`True.csv` or the CIFAKE
image folders manually, simply re-run:

```bash
python src/cleaning/clean_datasets.py
python src/eda/generate_eda_report.py
python src/splitting/split_datasets.py
```
