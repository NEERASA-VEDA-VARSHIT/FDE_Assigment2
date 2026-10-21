"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Master CLI Orchestrator
Executes: INGEST -> VALIDATE -> TRANSFORM -> METRICS -> EXPORT.
Features structured file & console logging, failure contract enforcement,
execution timing, and SHA-256 output verification.
"""

import hashlib
import sys
import time
from pathlib import Path

# Ensure both Assignment2b and repo root are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

for p in [str(BASE_DIR), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from pipeline.config import DEFAULT_DATASET, OUTPUT_DIR, setup_logging
    from pipeline.ingest import load_cmapss_dataset
    from pipeline.metrics import run_metrics
    from pipeline.transform import run_transform
    from pipeline.validate import run_validation
except ImportError:
    from Assignment2b.pipeline.config import DEFAULT_DATASET, OUTPUT_DIR, setup_logging
    from Assignment2b.pipeline.ingest import load_cmapss_dataset
    from Assignment2b.pipeline.metrics import run_metrics
    from Assignment2b.pipeline.transform import run_transform
    from Assignment2b.pipeline.validate import run_validation


def compute_file_sha256(filepath):
    """Calculates SHA-256 hexadecimal digest for deterministic output verification."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def execute_pipeline(dataset_id=DEFAULT_DATASET):
    """
    Executes the full dependable data foundations pipeline.
    """
    start_time = time.time()
    logger = setup_logging()

    logger.info("=============================================================")
    logger.info(f"NASA C-MAPSS DEPENDABLE FDE PIPELINE STARTING ({dataset_id})")
    logger.info("=============================================================")

    # 1. Ingestion Stage
    data_bundle = load_cmapss_dataset(dataset_id=dataset_id, logger=logger)

    # 2. Validation Stage
    validation_report = run_validation(data_bundle, logger=logger)
    if validation_report["overall_status"] == "FAIL":
        logger.error("Validation gate encountered critical failure! Halting execution.")
        raise RuntimeError("Pipeline aborted due to critical validation failure.")

    # 3. Transformation Stage
    canonical_df = run_transform(data_bundle, logger=logger)

    # 4. Metrics Computation Stage
    metrics_df = run_metrics(canonical_df, data_bundle, logger=logger)

    duration = time.time() - start_time

    # Checksum computation
    val_hash = compute_file_sha256(OUTPUT_DIR / "validation_report.json")
    final_hash = compute_file_sha256(OUTPUT_DIR / "final_output.csv")
    metrics_hash = compute_file_sha256(OUTPUT_DIR / "metrics.csv")

    logger.info("=============================================================")
    logger.info(f"PIPELINE RUN COMPLETED SUCCESSFULLY in {duration:.2f} seconds")
    logger.info("=============================================================")
    logger.info("GENERATED OUTPUT ARTIFACTS & SHA-256 CHECKSUMS:")
    logger.info(
        f"  - validation_report.json    [{val_hash[:16]}...] ({Path(OUTPUT_DIR / 'validation_report.json').stat().st_size:,} bytes)"
    )
    logger.info(
        f"  - final_output.csv          [{final_hash[:16]}...] ({Path(OUTPUT_DIR / 'final_output.csv').stat().st_size:,} bytes)"
    )
    logger.info(
        f"  - metrics.csv               [{metrics_hash[:16]}...] ({Path(OUTPUT_DIR / 'metrics.csv').stat().st_size:,} bytes)"
    )
    logger.info(
        "  [Idempotence Note] Identical SHA-256 digests prove deterministic repeatability; they do not prove analytical correctness."
    )

    return {
        "status": "SUCCESS",
        "duration_sec": duration,
        "dataset_id": dataset_id,
        "hashes": {"validation_report": val_hash, "final_output": final_hash, "metrics": metrics_hash},
    }


if __name__ == "__main__":
    execute_pipeline()
