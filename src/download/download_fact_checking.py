"""
download_fact_checking.py
--------------------------
Dataset: LIAR (Wang, 2017) - short statements labeled with a 6-way
truthfulness scale, sourced from PolitiFact.
Publicly downloadable without authentication.
"""

import sys
import zipfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.download.base_downloader import BaseDownloader, ManualDownloadRequired
from src.utils.io_utils import load_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FactCheckingDownloader(BaseDownloader):
    def __init__(self, cfg: dict):
        ds_cfg = cfg["datasets"]["fact_checking"]
        super().__init__(name=ds_cfg["name"], raw_subdir=ds_cfg["raw_subdir"])
        self.url = ds_cfg["url"]

    def _manual_instructions(self) -> str:
        return f"""
Dataset: {self.name}
Official page: https://www.cs.ucsb.edu/~william/data/liar_dataset.zip
Paper/context: https://arxiv.org/abs/1705.00648

Manual fallback:
  1. Visit the URL above directly in a browser (no login required).
  2. Download liar_dataset.zip.
  3. Unzip it and place train.tsv, valid.tsv, test.tsv into:
       {self.raw_dir}/
""".strip()

    def download(self):
        try:
            zip_path = self.http_download(self.url, "liar_dataset.zip")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(self.raw_dir)
            logger.info(f"[{self.name}] Extracted liar_dataset.zip into {self.raw_dir}")
        except Exception as e:
            logger.error(f"[{self.name}] Automated download failed: {e}")
            self.report_manual_download(self._manual_instructions())


if __name__ == "__main__":
    cfg = load_config()
    downloader = FactCheckingDownloader(cfg)
    try:
        downloader.download()
    except ManualDownloadRequired:
        sys.exit(1)
