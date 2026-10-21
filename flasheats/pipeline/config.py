"""
FlashEats Dependable Pipeline - Central Configuration
"""

import logging
import sys
from pathlib import Path

# Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = BASE_DIR / "data" / "raw" / "dispatch"
OUTPUT_DIR = BASE_DIR / "outputs"

DB_PATH = DATABASE_DIR / "flasheats.db"
API_SCRIPT_PATH = BASE_DIR / "api" / "mock_dispatch_api.py"

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
DISPATCH_ORDERS_ENDPOINT = f"{API_BASE_URL}/dispatch/orders"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
DEFAULT_PAGE_SIZE = 50
MAX_API_RETRIES = 5
DEFAULT_RETRY_DELAY_SEC = 0.5


# Setup Logging
def setup_logging(log_filename="pipeline.log"):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = OUTPUT_DIR / log_filename

    logger = logging.getLogger("flasheats_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
