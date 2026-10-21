"""
FlashEats Dependable Pipeline - Main Orchestrator
Executes the full FDE data pipeline:
  RAW INPUTS → INGEST → VALIDATE → TRANSFORM → METRICS → EXPORT
Ensures idempotent execution, failure contract enforcement, and reproducible outputs.
"""

import hashlib
import subprocess
import sys
import time
from pathlib import Path

import requests

# Add project root to sys.path so pipeline package can be imported directly
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from pipeline.config import API_SCRIPT_PATH, HEALTH_ENDPOINT, OUTPUT_DIR, RAW_DIR, setup_logging
    from pipeline.ingest import IngestionError, run_ingestion
    from pipeline.metrics import run_metrics
    from pipeline.transform import run_transform
    from pipeline.validate import run_validation
except ImportError:
    from flasheats.pipeline.config import API_SCRIPT_PATH, HEALTH_ENDPOINT, OUTPUT_DIR, RAW_DIR, setup_logging
    from flasheats.pipeline.ingest import IngestionError, run_ingestion
    from flasheats.pipeline.metrics import run_metrics
    from flasheats.pipeline.transform import run_transform
    from flasheats.pipeline.validate import run_validation


def compute_file_sha256(filepath):
    """Computes SHA-256 hash of a file for idempotence verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def ensure_mock_api_running(logger):
    """Checks if mock API is active; if not, launches it in a subprocess."""
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=1)
        if r.status_code == 200:
            logger.info("Mock Dispatch API is already running and healthy.")
            return None
    except Exception:
        pass

    logger.info(f"Starting Mock Dispatch API server from {API_SCRIPT_PATH}...")
    proc = subprocess.Popen(
        [sys.executable, str(API_SCRIPT_PATH)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    # Verify health
    for _ in range(5):
        try:
            r = requests.get(HEALTH_ENDPOINT, timeout=2)
            if r.status_code == 200:
                logger.info("Mock Dispatch API server launched successfully (health: 200 OK).")
                return proc
        except Exception:
            time.sleep(1)

    logger.error("Failed to connect to Mock Dispatch API after launch.")
    return proc


def main():
    logger = setup_logging()
    logger.info("=============================================================")
    logger.info("FLASHEATS DEPENDABLE FDE PIPELINE STARTING")
    logger.info("=============================================================")

    api_proc = ensure_mock_api_running(logger)

    try:
        # STEP 1: INGESTION
        start_time = time.time()
        data_bundle = run_ingestion(logger=logger)

        # STEP 2: VALIDATION
        validation_report = run_validation(data_bundle, logger=logger)

        # Check if validation raised any critical pipeline-blocking failures
        # (Note: Freshness live-ETA failure is scoped to use-case, not batch pipeline halt)
        if not validation_report["summary"]["can_proceed_to_transform"]:
            logger.error("Pipeline execution halted by Validation Gate policy.")
            sys.exit(1)

        # STEP 3: TRANSFORMATION & ORDER-LEVEL MODELING
        canonical_df = run_transform(data_bundle, logger=logger)

        # STEP 4: GOVERNED METRICS
        metrics_df = run_metrics(canonical_df, data_bundle["orders"], data_bundle["outcomes"], logger=logger)

        elapsed = time.time() - start_time
        logger.info("=============================================================")
        logger.info(f"PIPELINE RUN COMPLETED SUCCESSFULLY in {elapsed:.2f} seconds")
        logger.info("=============================================================")

        # Print Output Manifest & Checksums
        logger.info("GENERATED OUTPUT ARTIFACTS & SHA-256 CHECKSUMS:")
        generated_files = [
            OUTPUT_DIR / "validation_report.json",
            OUTPUT_DIR / "final_output.csv",
            OUTPUT_DIR / "metrics.csv",
        ]

        checksums = {}
        for f in generated_files:
            if f.exists():
                h = compute_file_sha256(f)
                checksums[f.name] = h
                logger.info(f"  - {f.name:25s} [{h[:16]}...] ({f.stat().st_size:,} bytes)")
            else:
                logger.warning(f"  - Missing expected output file: {f}")

        logger.info("Raw API Pages Preserved:")
        raw_pages = list(RAW_DIR.glob("page_*.json"))
        logger.info(f"  - Preserved {len(raw_pages)} raw response pages in {RAW_DIR}")

        return checksums

    except IngestionError as ie:
        logger.error(f"PIPELINE INGESTION ERROR: {ie}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"UNHANDLED PIPELINE EXCEPTION: {e}")
        sys.exit(1)
    finally:
        if api_proc:
            api_proc.terminate()
            logger.info("Mock API process terminated.")


if __name__ == "__main__":
    main()
