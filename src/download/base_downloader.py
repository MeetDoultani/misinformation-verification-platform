"""
base_downloader.py
-------------------
Reusable base class for dataset downloaders. Subclasses implement the
`download()` method. This class provides shared behavior: directory setup,
resumable HTTP downloads with progress bars, and a standard way to report
"manual action required" for gated datasets (e.g. Kaggle).
"""

from pathlib import Path
import sys
import requests
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.logging_utils import get_logger
from src.utils.io_utils import ensure_dir, dataset_status

logger = get_logger(__name__)


class ManualDownloadRequired(Exception):
    """Raised when a dataset cannot be fetched automatically."""
    pass


class BaseDownloader:
    def __init__(self, name: str, raw_subdir: str):
        self.name = name
        self.raw_dir = ensure_dir(Path(raw_subdir))

    def http_download(self, url: str, dest_filename: str, chunk_size: int = 8192) -> Path:
        """
        Stream-download a file with a progress bar. Skips download if the
        file already exists and is non-empty (idempotent / resumable runs).
        """
        dest_path = self.raw_dir / dest_filename
        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.info(f"[{self.name}] {dest_filename} already exists, skipping download.")
            return dest_path

        logger.info(f"[{self.name}] Downloading {url} -> {dest_path}")
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                with open(dest_path, "wb") as f, tqdm(
                    total=total, unit="B", unit_scale=True, desc=dest_filename
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.name}] Download failed for {url}: {e}")
            if dest_path.exists():
                dest_path.unlink()  # remove partial file
            raise

        return dest_path

    def report_manual_download(self, instructions: str):
        """
        Standard way to halt and hand control back to the user for gated
        datasets. Prints clear, numbered instructions and raises so the
        orchestrator (run_pipeline.sh) stops instead of silently continuing.
        """
        logger.warning(f"[{self.name}] MANUAL DOWNLOAD REQUIRED")
        print("\n" + "=" * 78)
        print(f"MANUAL ACTION REQUIRED: {self.name}")
        print("=" * 78)
        print(instructions)
        print("=" * 78 + "\n")
        raise ManualDownloadRequired(f"{self.name} requires manual download. See instructions above.")

    def check_status(self, expected_files: list) -> dict:
        return dataset_status(self.raw_dir, expected_files)

    def download(self):
        raise NotImplementedError("Subclasses must implement download()")
