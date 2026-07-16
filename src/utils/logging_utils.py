"""
logging_utils.py
-----------------
Centralized logger factory so every script in the pipeline logs consistently
to both the console and a per-run log file under reports/.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).resolve().parents[2] / "reports" / "logs"


def get_logger(name: str, log_to_file: bool = True) -> logging.Logger:
    """
    Create (or fetch) a logger with a standard format.

    Args:
        name: usually __name__ of the calling module.
        log_to_file: if True, also writes to reports/logs/<name>_<timestamp>.log

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        # Already configured (avoid duplicate handlers on repeated calls)
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = name.replace(".", "_")
        file_handler = logging.FileHandler(LOG_DIR / f"{safe_name}_{timestamp}.log")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger
