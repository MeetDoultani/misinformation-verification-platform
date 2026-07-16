"""
download_claim_verification.py
-------------------------------
Dataset: FEVER (Fact Extraction and VERification)
Publicly downloadable without authentication directly from fever.ai.
Note: fever.ai occasionally changes hosting; if URLs 404, see the manual
fallback instructions printed by this script.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.download.base_downloader import BaseDownloader, ManualDownloadRequired
from src.utils.io_utils import load_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ClaimVerificationDownloader(BaseDownloader):
    def __init__(self, cfg: dict):
        ds_cfg = cfg["datasets"]["claim_verification"]
        super().__init__(name=ds_cfg["name"], raw_subdir=ds_cfg["raw_subdir"])
        self.urls = ds_cfg["urls"]

    def _manual_instructions(self) -> str:
        return f"""
Dataset: {self.name}
Official page: https://fever.ai/dataset/fever.html

The automated download failed (the host may have changed its file layout).

Manual fallback:
  1. Visit https://fever.ai/dataset/fever.html
  2. Download the "train", "paper_dev" (validation) and "paper_test" JSONL splits.
  3. Place them into: {self.raw_dir}/
       - train.jsonl
       - paper_dev.jsonl
       - paper_test.jsonl

No account or authentication is required for FEVER; this is typically a
transient hosting/URL issue rather than a gated-access issue.
""".strip()

    def download(self):
        expected = [f"{split}.jsonl" for split in self.urls.keys()]
        # normalize expected filenames to match what we save
        try:
            for split, url in self.urls.items():
                fname = "paper_dev.jsonl" if split == "val" else f"{split}.jsonl"
                self.http_download(url, fname)
        except Exception as e:
            logger.error(f"[{self.name}] Automated download failed: {e}")
            self.report_manual_download(self._manual_instructions())


if __name__ == "__main__":
    cfg = load_config()
    downloader = ClaimVerificationDownloader(cfg)
    try:
        downloader.download()
    except ManualDownloadRequired:
        sys.exit(1)
