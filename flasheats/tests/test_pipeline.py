"""
FlashEats Dependable Pipeline - Automated Test Suite
Includes unit tests, integration tests, and clean-room idempotence verification.
"""
import unittest
import hashlib
from pathlib import Path
import pandas as pd
import json

import sys

# Ensure flasheats root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from pipeline.config import BASE_DIR, OUTPUT_DIR, RAW_DIR, DB_PATH, DATA_DIR
    from pipeline.ingest import extract_sqlite_tables, load_file_sources
    from pipeline.validate import run_validation
    from pipeline.transform import run_transform
    from pipeline.metrics import run_metrics
    from pipeline.run_pipeline import compute_file_sha256
except ImportError:
    from flasheats.pipeline.config import BASE_DIR, OUTPUT_DIR, RAW_DIR, DB_PATH, DATA_DIR
    from flasheats.pipeline.ingest import extract_sqlite_tables, load_file_sources
    from flasheats.pipeline.validate import run_validation
    from flasheats.pipeline.transform import run_transform
    from flasheats.pipeline.metrics import run_metrics
    from flasheats.pipeline.run_pipeline import compute_file_sha256

class TestFlashEatsPipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Load sample data bundle
        cls.db_data = extract_sqlite_tables(DB_PATH)
        cls.file_data = load_file_sources(DATA_DIR)
        cls.data_bundle = {
            **cls.db_data,
            **cls.file_data,
            "dispatch_api": {"records": [], "total_pages": 0, "reported_total": 0}
        }

    def test_01_ingestion_integrity(self):
        """Verify ingestion loads required tables and fields without schema corruption."""
        self.assertIn("orders", self.data_bundle)
        self.assertIn("customers", self.data_bundle)
        self.assertIn("drivers", self.data_bundle)
        self.assertIn("restaurants", self.data_bundle)
        self.assertIn("tickets", self.data_bundle)
        self.assertIn("outcomes", self.data_bundle)
        
        orders = self.data_bundle["orders"]
        self.assertGreater(len(orders), 0)
        self.assertTrue({"order_id", "promised_eta", "final_status"}.issubset(orders.columns))

    def test_02_validation_gate_detects_anomalies(self):
        """Verify validation gate catches duplicates, missing timestamps, and chronology errors."""
        report = run_validation(self.data_bundle)
        
        # 1. Grain / Duplicates check
        grain_chk = report["checks"]["business_grain"]
        self.assertEqual(grain_chk["status"], "WARN")
        self.assertGreater(grain_chk["duplicate_rows_detected"], 0)
        self.assertGreater(len(report["quarantine"]["duplicate_orders"]), 0)
        
        # 2. Missing timestamps check
        ts_chk = report["checks"]["delivered_completion_timestamps"]
        self.assertEqual(ts_chk["status"], "WARN")
        self.assertGreater(ts_chk["missing_completion_timestamp_count"], 0)
        
        # 3. Chronology check
        chrono_chk = report["checks"]["timestamp_chronology"]
        self.assertEqual(chrono_chk["status"], "WARN")
        self.assertGreater(chrono_chk["promised_eta_before_created_count"], 0)
        self.assertGreater(chrono_chk["pickup_after_delivery_count"], 0)
        
        # 4. KPI Governance
        kpi_chk = report["checks"]["kpi_governance"]
        self.assertEqual(kpi_chk["status"], "UNKNOWN")
        self.assertEqual(kpi_chk["publish_56_percent_verdict"], "FAIL (DO NOT PUBLISH TODAY)")

    def test_03_transformation_order_grain(self):
        """Verify order-level transformation enforces strict 1 row = 1 order without fanout."""
        order_model = run_transform(self.data_bundle)
        
        self.assertIsInstance(order_model, pd.DataFrame)
        total_rows = len(order_model)
        unique_orders = order_model["order_id"].nunique()
        
        # Strict dynamic grain assertion
        expected_unique = self.data_bundle["orders"]["order_id"].nunique()
        self.assertEqual(total_rows, unique_orders, "Row count must equal unique order_id count!")
        self.assertEqual(total_rows, expected_unique, "Row count must match base orders unique count!")
        self.assertFalse(order_model["order_id"].duplicated().any(), "Zero duplicate order_ids permitted!")
        
        # Required columns present
        required_cols = [
            "order_id", "customer_id", "support_opened", "cancel_attempted",
            "intervention_count", "intervention_types", "final_status", "late_flag", "delay_min"
        ]
        self.assertEqual(list(order_model.columns), required_cols)

    def test_04_metrics_governance_and_computation(self):
        """Verify metric calculations are bounded, accurate, and governed with appropriate statuses."""
        order_model = run_transform(self.data_bundle)
        metrics_df = run_metrics(order_model, self.data_bundle["orders"], self.data_bundle["outcomes"])
        
        self.assertIsInstance(metrics_df, pd.DataFrame)
        self.assertGreater(len(metrics_df), 0)
        
        for _, row in metrics_df.iterrows():
            val = row["value_pct"]
            status = row["status"]
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 100.0)
            self.assertIn(status, ["UNRATIFIED", "OBSERVATIONAL"])
            
        # Check specific late rate candidate rows
        unratified = metrics_df[metrics_df["status"] == "UNRATIFIED"]
        self.assertGreaterEqual(len(unratified), 3)

    def test_05_clean_room_idempotence(self):
        """
        Verify that consecutive pipeline executions on unchanged source data
        yield bit-for-bit identical outputs with matching SHA-256 hashes.
        """
        # Run 1
        rep1 = run_validation(self.data_bundle)
        tf1 = run_transform(self.data_bundle)
        met1 = run_metrics(tf1, self.data_bundle["orders"], self.data_bundle["outcomes"])
        
        hash_final_1 = compute_file_sha256(OUTPUT_DIR / "final_output.csv")
        hash_metrics_1 = compute_file_sha256(OUTPUT_DIR / "metrics.csv")
        hash_val_1 = compute_file_sha256(OUTPUT_DIR / "validation_report.json")
        
        # Run 2
        rep2 = run_validation(self.data_bundle)
        tf2 = run_transform(self.data_bundle)
        met2 = run_metrics(tf2, self.data_bundle["orders"], self.data_bundle["outcomes"])
        
        hash_final_2 = compute_file_sha256(OUTPUT_DIR / "final_output.csv")
        hash_metrics_2 = compute_file_sha256(OUTPUT_DIR / "metrics.csv")
        hash_val_2 = compute_file_sha256(OUTPUT_DIR / "validation_report.json")
        
        # Assert bit-for-bit checksum identity
        self.assertEqual(hash_final_1, hash_final_2, "final_output.csv must be bit-for-bit identical across runs!")
        self.assertEqual(hash_metrics_1, hash_metrics_2, "metrics.csv must be bit-for-bit identical across runs!")
        self.assertEqual(hash_val_1, hash_val_2, "validation_report.json must be bit-for-bit identical across runs!")

if __name__ == "__main__":
    unittest.main()
