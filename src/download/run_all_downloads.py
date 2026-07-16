"""
run_all_downloads.py
---------------------
Orchestrates all dataset downloaders. Does NOT stop the whole pipeline if
one dataset requires manual intervention -- it collects the outcome for
each dataset and prints a consolidated summary at the end, so the user
gets a single actionable checklist rather than five separate failures.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.io_utils import load_config
from src.utils.logging_utils import get_logger
from src.download.base_downloader import ManualDownloadRequired
from src.download.download_fake_real_news import FakeRealNewsDownloader
from src.download.download_claim_verification import ClaimVerificationDownloader
from src.download.download_fact_checking import FactCheckingDownloader
from src.download.download_image_forensics import ImageForensicsDownloader
from src.download.download_ai_text_detection import AiTextDetectionDownloader

logger = get_logger(__name__)


def main():
    cfg = load_config()
    downloaders = [
        FakeRealNewsDownloader(cfg),
        ClaimVerificationDownloader(cfg),
        FactCheckingDownloader(cfg),
        ImageForensicsDownloader(cfg),
        AiTextDetectionDownloader(cfg),
    ]

    results = {}
    for d in downloaders:
        try:
            d.download()
            results[d.name] = "OK"
        except ManualDownloadRequired:
            results[d.name] = "MANUAL ACTION REQUIRED (see instructions above)"
        except Exception as e:
            results[d.name] = f"FAILED: {e}"

    print("\n" + "#" * 78)
    print("DOWNLOAD SUMMARY")
    print("#" * 78)
    for name, status in results.items():
        print(f"  [{status:45s}] {name}")
    print("#" * 78 + "\n")

    if any("MANUAL" in s or "FAILED" in s for s in results.values()):
        print("Some datasets need your attention before cleaning/EDA can run "
              "on the full corpus. Re-run this script after placing files "
              "manually -- it will automatically detect and skip datasets "
              "that are already present.\n")


if __name__ == "__main__":
    main()
