#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh
# Runs the full Phase 1 Data Engineering pipeline end to end:
#   download -> clean -> EDA -> split
# Each stage is independent and idempotent; if a stage reports datasets
# needing manual action, this script still proceeds to clean/split whatever
# IS available, then reminds you at the end what's still missing.
# =============================================================================
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=============================================================="
echo " STAGE 1/4: Download"
echo "=============================================================="
python src/download/run_all_downloads.py

echo
echo "=============================================================="
echo " STAGE 2/4: Cleaning"
echo "=============================================================="
python src/cleaning/clean_datasets.py

echo
echo "=============================================================="
echo " STAGE 3/4: EDA"
echo "=============================================================="
python src/eda/generate_eda_report.py

echo
echo "=============================================================="
echo " STAGE 4/4: Splitting"
echo "=============================================================="
python src/splitting/split_datasets.py

echo
echo "=============================================================="
echo " PIPELINE COMPLETE"
echo " - Processed data:  data/processed/"
echo " - Splits:          data/splits/"
echo " - EDA report:      reports/eda/eda_report.md"
echo " - Figures:         reports/figures/"
echo "=============================================================="
