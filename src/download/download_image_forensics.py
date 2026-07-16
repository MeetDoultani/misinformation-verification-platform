"""
download_image_forensics.py
----------------------------
Dataset: CIFAKE - Real and AI-Generated Synthetic Images (Kaggle)
GATED behind a Kaggle account / API token. Mirrors the pattern used in
download_fake_real_news.py: try Kaggle CLI, else print manual instructions.
"""

import sys
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.download.base_downloader import BaseDownloader, ManualDownloadRequired
from src.utils.io_utils import load_config
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ImageForensicsDownloader(BaseDownloader):
    def __init__(self, cfg: dict):
        ds_cfg = cfg["datasets"]["image_forensics"]
        super().__init__(name=ds_cfg["name"], raw_subdir=ds_cfg["raw_subdir"])
        self.kaggle_slug = ds_cfg["kaggle_slug"]

    def _manual_instructions(self) -> str:
        return f"""
Dataset: {self.name}
Kaggle page: https://www.kaggle.com/datasets/{self.kaggle_slug}

Prerequisites (same as any Kaggle dataset):
  1. Create a free Kaggle account: https://www.kaggle.com
  2. Generate an API token: https://www.kaggle.com/settings/account -> "Create New Token"
  3. Place kaggle.json at ~/.kaggle/kaggle.json (chmod 600)
  4. pip install kaggle

Automated retry (after completing the above):
  kaggle datasets download -d {self.kaggle_slug} -p {self.raw_dir} --unzip

Manual fallback (no CLI):
  1. Visit the Kaggle page above and click "Download" (~ a few hundred MB, 120,000 images).
  2. Unzip the archive.
  3. Place the resulting folders directly into: {self.raw_dir}/
       - train/REAL/*.jpg
       - train/FAKE/*.jpg
       - test/REAL/*.jpg
       - test/FAKE/*.jpg

This pipeline treats image files as opaque binary assets: cleaning scripts
validate file integrity, size, and format, and build a metadata CSV mapping
file paths to labels. No pixel-level model work happens in this phase.
""".strip()

    def download(self):
        # For image datasets we check for the presence of the raw_subdir being non-empty
        existing = list(self.raw_dir.rglob("*.jpg")) + list(self.raw_dir.rglob("*.jpeg")) + list(self.raw_dir.rglob("*.png"))
        if existing:
            logger.info(f"[{self.name}] Found {len(existing)} existing image files. Skipping download.")
            return

        logger.info(f"[{self.name}] Attempting Kaggle CLI download...")
        try:
            subprocess.run(
                ["kaggle", "datasets", "download", "-d", self.kaggle_slug,
                 "-p", str(self.raw_dir), "--unzip"],
                check=True, capture_output=True, text=True,
            )
            existing = list(self.raw_dir.rglob("*.jpg")) + list(self.raw_dir.rglob("*.png"))
            if existing:
                logger.info(f"[{self.name}] Kaggle CLI download succeeded ({len(existing)} images).")
                return
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"[{self.name}] Kaggle CLI unavailable or failed: {e}")

        self.report_manual_download(self._manual_instructions())


if __name__ == "__main__":
    cfg = load_config()
    downloader = ImageForensicsDownloader(cfg)
    try:
        downloader.download()
    except ManualDownloadRequired:
        sys.exit(1)
