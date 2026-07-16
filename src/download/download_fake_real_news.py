"""
download_fake_real_news.py
---------------------------
Dataset: ISOT Fake and Real News Dataset (Kaggle)
This dataset is GATED behind a Kaggle account / API token, so it cannot be
fetched automatically in a clean-room environment. This script:
  1. Checks if the required files already exist locally.
  2. If not, tries the Kaggle CLI (works only if the user has configured
     ~/.kaggle/kaggle.json).
  3. If that fails, prints precise manual-download instructions and stops.
"""

import sys
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.download.base_downloader import BaseDownloader, ManualDownloadRequired
from src.utils.io_utils import load_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class FakeRealNewsDownloader(BaseDownloader):
    def __init__(self, cfg: dict):
        ds_cfg = cfg["datasets"]["fake_real_news"]
        super().__init__(name=ds_cfg["name"], raw_subdir=ds_cfg["raw_subdir"])
        self.kaggle_slug = ds_cfg["kaggle_slug"]
        self.expected_files = ds_cfg["expected_files"]

    def _manual_instructions(self) -> str:
        return f"""
Dataset: {self.name}
Kaggle page: https://www.kaggle.com/datasets/{self.kaggle_slug}

Prerequisites:
  1. Create a free Kaggle account (if you don't have one): https://www.kaggle.com
  2. Go to https://www.kaggle.com/settings/account -> "API" section -> "Create New Token".
     This downloads a file called kaggle.json.
  3. Place kaggle.json at: ~/.kaggle/kaggle.json  (chmod 600 ~/.kaggle/kaggle.json)
  4. Install the CLI: pip install kaggle

Automated retry (after completing the above):
  kaggle datasets download -d {self.kaggle_slug} -p {self.raw_dir} --unzip

Manual fallback (no CLI):
  1. Visit the Kaggle page above and click "Download".
  2. Unzip the archive.
  3. Place the following files directly into: {self.raw_dir}/
       - Fake.csv
       - True.csv

Once the files are in place, re-run this script or the pipeline; it will
detect them automatically and skip the download step.
""".strip()

    def download(self):
        status = self.check_status(self.expected_files)
        if all(status.values()):
            logger.info(f"[{self.name}] All expected files already present. Skipping.")
            return

        logger.info(f"[{self.name}] Attempting Kaggle CLI download...")
        try:
            subprocess.run(
                ["kaggle", "datasets", "download", "-d", self.kaggle_slug,
                 "-p", str(self.raw_dir), "--unzip"],
                check=True, capture_output=True, text=True,
            )
            status = self.check_status(self.expected_files)
            if all(status.values()):
                logger.info(f"[{self.name}] Kaggle CLI download succeeded.")
                return
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"[{self.name}] Kaggle CLI unavailable or failed: {e}")

        # Fall through to manual instructions
        self.report_manual_download(self._manual_instructions())


if __name__ == "__main__":
    cfg = load_config()
    downloader = FakeRealNewsDownloader(cfg)
    try:
        downloader.download()
    except ManualDownloadRequired:
        sys.exit(1)
