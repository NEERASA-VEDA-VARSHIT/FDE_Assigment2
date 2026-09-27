"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Automated Test Suite
Includes unit tests, integration tests, parser verification, and clean-room idempotence proof.
"""
import unittest
import hashlib
from pathlib import Path
import pandas as pd
import json

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

for p in [str(BASE_DIR), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from pipeline.config import BASE_DIR, OUTPUT_DIR, RAW_DIR, COLUMN_NAMES
    from pipeline.ingest import load_cmapss_dataset
    from pipeline.validate import run_validation
    from pipeline.transform import run_transform
    from pipeline.metrics import run_metrics
    from pipeline.run_pipeline import compute_file_sha256
except ImportError:
    from Assignment2b.pipeline.config import BASE_DIR, OUTPUT_DIR, RAW_DIR, COLUMN_NAMES
    from Assignment2b.pipeline.ingest import load_cmapss_dataset
    from Assignment2b.pipeline.validate import run_validation
    from Assignment2b.pipeline.transform import run_transform
    from Assignment2b.pipeline.metrics import run_metrics
    from Assignment2b.pipeline.run_pipeline import compute_file_sha256

class TestCMAPSSPipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Ingest FD001 data bundle for testing
        cls.data_bundle = load_cmapss_dataset("FD001", raw_dir=RAW_DIR)

    def test_01_ingestion_integrity_and_whitespace_parsing(self):
        """
        Verify ingestion loads required datasets, enforces 26-column schema without NaNs,
        and demonstrates the trailing-whitespace parser trap.
        """
        self.assertIn("train", self.data_bundle)
        self.assertIn("test", self.data_bundle)
        self.assertIn("rul", self.data_bundle)
        
        train = self.data_bundle["train"]
        test = self.data_bundle["test"]
        rul = self.data_bundle["rul"]
        
        # 1. Verify robust parser produces 26 columns without NaNs
        self.assertEqual(train.shape[1], 26)
        self.assertEqual(test.shape[1], 26)
        self.assertEqual(list(train.columns), COLUMN_NAMES)
        self.assertEqual(train.isna().sum().sum(), 0)
        self.assertEqual(test.isna().sum().sum(), 0)
        self.assertEqual(rul.isna().sum().sum(), 0)
        
        # 2. Demonstrate the whitespace parser trap: sep=' ' creates 28 columns with NaNs
        raw_train_file = RAW_DIR / "train_FD001.txt"
        df_naive = pd.read_csv(raw_train_file, sep=" ", header=None)
        self.assertGreater(df_naive.shape[1], 26, "Naive space parser must create phantom columns due to trailing spaces!")
        self.assertTrue(df_naive.isna().sum().sum() > 0, "Naive space parser must contain NaN values!")

    def test_02_validation_gate_and_failure_contracts(self):
        """Verify validation gate catches flatline sensors and audits technical, semantic, and decision dimensions."""
        report = run_validation(self.data_bundle)
        
        self.assertIn("checks", report)
        checks = report["checks"]
        
        # 1. Technical grain uniqueness (PASS)
        self.assertEqual(checks["composite_grain_uniqueness"]["status"], "PASS")
        self.assertEqual(checks["composite_grain_uniqueness"]["train_duplicate_snapshots"], 0)
        
        # 2. Contiguity (PASS)
        self.assertEqual(checks["engine_unit_contiguity"]["status"], "PASS")
        self.assertTrue(checks["engine_unit_contiguity"]["train_contiguous"])
        
        # 3. Cycle continuity (PASS)
        self.assertEqual(checks["cycle_sequence_continuity"]["status"], "PASS")
        self.assertEqual(checks["cycle_sequence_continuity"]["train_broken_trajectories"], 0)
        
        # 4. Sensor variance audit (WARN for 6 constant sensors)
        self.assertEqual(checks["sensor_variance_audit"]["status"], "WARN")
        self.assertEqual(checks["sensor_variance_audit"]["flatline_sensor_count"], 6)
        expected_flatline = ["sensor_1", "sensor_5", "sensor_10", "sensor_16", "sensor_18", "sensor_19"]
        self.assertEqual(checks["sensor_variance_audit"]["flatline_sensor_channels"], expected_flatline)
        
        # 5. Trajectory bounds (PASS)
        self.assertEqual(checks["trajectory_lifespan_bounds"]["status"], "PASS")
        
        # 6. Operational decision context (UNKNOWN)
        self.assertEqual(checks["operational_decision_context"]["status"], "UNKNOWN")
        
        # Overall status should be WARN (advisory due to constant sensors)
        self.assertEqual(report["overall_status"], "WARN")

    def test_03_grain_invariants_and_fanout_prevention(self):
        """Verify transformation maintains strict 1 row = 1 engine cycle without Cartesian fanout."""
        canonical_df = run_transform(self.data_bundle)
        
        self.assertIsInstance(canonical_df, pd.DataFrame)
        total_rows = len(canonical_df)
        expected_rows = len(self.data_bundle["train"])
        
        # Dynamic grain assertions
        self.assertEqual(total_rows, expected_rows, "Transformed rows must match raw training rows!")
        unique_snapshots = canonical_df[["unit_number", "time_in_cycles"]].drop_duplicates().shape[0]
        self.assertEqual(total_rows, unique_snapshots, "Composite grain (unit_number, time_in_cycles) must be 100% unique!")
        
        # Lifecycle validity
        self.assertTrue((canonical_df["total_lifespan"] >= canonical_df["time_in_cycles"]).all())
        self.assertTrue((canonical_df["true_rul"] >= 0).all())
        
        # Categorical stage assignment
        stages = set(canonical_df["analytical_lifecycle_stage"].unique())
        self.assertTrue(stages.issubset({"NOMINAL", "ADVISORY", "CRITICAL"}))

    def test_04_metrics_governance_and_bounds(self):
        """Verify all 5 candidate operational metrics are bounded, accurate, and governed."""
        canonical_df = run_transform(self.data_bundle)
        metrics_df = run_metrics(canonical_df, self.data_bundle)
        
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertEqual(len(metrics_df), 5)
        
        expected_cols = ["metric_name", "formula", "grain", "value_pct", "status", "interpretation", "limitation"]
        self.assertEqual(list(metrics_df.columns), expected_cols)
        
        for _, row in metrics_df.iterrows():
            val = row["value_pct"]
            status = row["status"]
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)
            self.assertIn(status, ["FACT", "OBSERVATIONAL", "UNRATIFIED", "UNKNOWN"])
            
        # Specific metric checks
        sensor_ratio_row = metrics_df[metrics_df["metric_name"] == "non_constant_sensor_ratio"].iloc[0]
        self.assertEqual(sensor_ratio_row["status"], "FACT")
        self.assertEqual(sensor_ratio_row["value_pct"], 71.43)
        
        cv_row = metrics_df[metrics_df["metric_name"] == "lifespan_coefficient_of_variation"].iloc[0]
        self.assertEqual(cv_row["status"], "OBSERVATIONAL")
        self.assertEqual(cv_row["value_pct"], 22.46)
        
        comp_row = metrics_df[metrics_df["metric_name"] == "trajectory_completeness_rate"].iloc[0]
        self.assertEqual(comp_row["status"], "FACT")
        self.assertEqual(comp_row["value_pct"], 100.0)

    def test_05_clean_room_idempotence(self):
        """
        Verify that consecutive pipeline executions on unchanged source data
        yield bit-for-bit identical outputs with matching SHA-256 hashes.
        (Proves deterministic repeatability, not business correctness).
        """
        # Run 1
        rep1 = run_validation(self.data_bundle)
        tf1 = run_transform(self.data_bundle)
        met1 = run_metrics(tf1, self.data_bundle)
        
        hash_final_1 = compute_file_sha256(OUTPUT_DIR / "final_output.csv")
        hash_metrics_1 = compute_file_sha256(OUTPUT_DIR / "metrics.csv")
        hash_val_1 = compute_file_sha256(OUTPUT_DIR / "validation_report.json")
        
        # Run 2
        rep2 = run_validation(self.data_bundle)
        tf2 = run_transform(self.data_bundle)
        met2 = run_metrics(tf2, self.data_bundle)
        
        hash_final_2 = compute_file_sha256(OUTPUT_DIR / "final_output.csv")
        hash_metrics_2 = compute_file_sha256(OUTPUT_DIR / "metrics.csv")
        hash_val_2 = compute_file_sha256(OUTPUT_DIR / "validation_report.json")
        
        # Assert bit-for-bit checksum identity
        self.assertEqual(hash_final_1, hash_final_2, "final_output.csv must be bit-for-bit identical across runs!")
        self.assertEqual(hash_metrics_1, hash_metrics_2, "metrics.csv must be bit-for-bit identical across runs!")
        self.assertEqual(hash_val_1, hash_val_2, "validation_report.json must be bit-for-bit identical across runs!")

if __name__ == "__main__":
    unittest.main()
