"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Validation Stage
Executes validation contracts across technical, semantic, and operational decision dimensions.
Audits grain integrity, cycle continuity, schema compliance, sensor variance,
trajectory plausibility, and test RUL alignment.
Exports outputs/validation_report.json following explicit failure contracts: PASS, WARN, FAIL, UNKNOWN.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from .config import OUTPUT_DIR

def run_validation(data_bundle, logger=None):
    """
    Executes automated validation checks on ingested C-MAPSS data.
    Implements FDE Failure Contract: PASS, WARN, FAIL, UNKNOWN.
    """
    if logger:
        logger.info("=== STEP 2: VALIDATION STAGE ===")
        
    df_train = data_bundle["train"]
    df_test = data_bundle["test"]
    df_rul = data_bundle["rul"]
    dataset_id = data_bundle["dataset_id"]
    
    checks = {}
    
    # -------------------------------------------------------------
    # Check 1: Primary Key / Grain Uniqueness (Technical & Semantic)
    # -------------------------------------------------------------
    # Grain invariant: (unit_number, time_in_cycles) must be unique
    train_dups = int(df_train.duplicated(subset=["unit_number", "time_in_cycles"]).sum())
    test_dups = int(df_test.duplicated(subset=["unit_number", "time_in_cycles"]).sum())
    
    grain_status = "PASS" if (train_dups == 0 and test_dups == 0) else "FAIL"
    checks["composite_grain_uniqueness"] = {
        "status": grain_status,
        "dimension": "Technical / Semantic",
        "contract": "Each engine-cycle snapshot (unit_number, time_in_cycles) must be strictly unique.",
        "train_duplicate_snapshots": train_dups,
        "test_duplicate_snapshots": test_dups
    }
    if logger:
        logger.info(f"  [Grain Uniqueness] Status: {grain_status} | Train Dups: {train_dups} | Test Dups: {test_dups}")
        
    # -------------------------------------------------------------
    # Check 2: Contiguous Engine Identifiers (Technical)
    # -------------------------------------------------------------
    tr_units = sorted(df_train["unit_number"].unique())
    te_units = sorted(df_test["unit_number"].unique())
    
    tr_expected = list(range(1, len(tr_units) + 1))
    te_expected = list(range(1, len(te_units) + 1))
    
    tr_contiguous = (tr_units == tr_expected)
    te_contiguous = (te_units == te_expected)
    
    unit_status = "PASS" if (tr_contiguous and te_contiguous) else "WARN"
    checks["engine_unit_contiguity"] = {
        "status": unit_status,
        "dimension": "Technical",
        "contract": "Engine identifiers must be strictly contiguous integers from 1 to N.",
        "train_engines_detected": len(tr_units),
        "train_contiguous": tr_contiguous,
        "test_engines_detected": len(te_units),
        "test_contiguous": te_contiguous
    }
    if logger:
        logger.info(f"  [Unit Contiguity] Status: {unit_status} | Train: {len(tr_units)} (1..{len(tr_units)}) | Test: {len(te_units)} (1..{len(te_units)})")

    # -------------------------------------------------------------
    # Check 3: Monotonic Cycle Continuity & Zero Missing Cycles (Semantic)
    # -------------------------------------------------------------
    def audit_cycle_continuity(df):
        broken_engines = []
        for u, grp in df.groupby("unit_number"):
            cycles = grp["time_in_cycles"].values
            if len(cycles) == 0:
                broken_engines.append({"unit": int(u), "reason": "empty_trajectory"})
            elif cycles[0] != 1:
                broken_engines.append({"unit": int(u), "reason": f"starts_at_{cycles[0]}"})
            elif not np.array_equal(cycles, np.arange(1, len(cycles) + 1)):
                broken_engines.append({"unit": int(u), "reason": "cycle_step_gaps"})
        return broken_engines

    train_broken = audit_cycle_continuity(df_train)
    test_broken = audit_cycle_continuity(df_test)
    
    cycle_status = "PASS" if (len(train_broken) == 0 and len(test_broken) == 0) else "FAIL"
    checks["cycle_sequence_continuity"] = {
        "status": cycle_status,
        "dimension": "Semantic",
        "contract": "Trajectories must start at cycle 1 and increment monotonically by +1 with zero missing cycles.",
        "train_broken_trajectories": len(train_broken),
        "test_broken_trajectories": len(test_broken)
    }
    if logger:
        logger.info(f"  [Cycle Continuity] Status: {cycle_status} | Train Gaps: {len(train_broken)} | Test Gaps: {len(test_broken)}")

    # -------------------------------------------------------------
    # Check 4: Sensor Variance & Flatline Channel Audit (Technical / Information)
    # -------------------------------------------------------------
    # Identify channels with standard deviation < 1e-4
    sensor_cols = [f"sensor_{i}" for i in range(1, 22)]
    stds = df_train[sensor_cols].std()
    
    flatline_sensors = [col for col in sensor_cols if stds[col] < 1e-4]
    flatline_count = len(flatline_sensors)
    
    # Under FD001 (Sea Level), zero-variance channels are an observed data reality
    variance_status = "WARN" if flatline_count > 0 else "PASS"
    checks["sensor_variance_audit"] = {
        "status": variance_status,
        "dimension": "Technical / Measurement",
        "contract": "Audit sensor columns for within-dataset variation under the evaluated flight regime.",
        "total_sensors_evaluated": len(sensor_cols),
        "flatline_sensor_count": flatline_count,
        "flatline_sensor_channels": flatline_sensors,
        "active_sensor_channels": [c for c in sensor_cols if c not in flatline_sensors],
        "interpretation": "Identified channels exhibit zero within-dataset variation under FD001 and cannot distinguish degradation progression in this analysis."
    }
    if logger:
        logger.info(f"  [Sensor Variance Audit] Status: {variance_status} | Constant Channels: {flatline_count}/21 {flatline_sensors}")

    # -------------------------------------------------------------
    # Check 5: Trajectory Lifespan Distribution & Bounds (Semantic)
    # -------------------------------------------------------------
    train_lifespans = df_train.groupby("unit_number")["time_in_cycles"].max()
    min_life = int(train_lifespans.min())
    max_life = int(train_lifespans.max())
    median_life = float(train_lifespans.median())
    mean_life = float(train_lifespans.mean())
    std_life = float(train_lifespans.std(ddof=1))
    
    lifespan_status = "PASS" if (min_life >= 50 and max_life <= 1000) else "WARN"
    checks["trajectory_lifespan_bounds"] = {
        "status": lifespan_status,
        "dimension": "Semantic",
        "contract": "Run-to-failure lifespans fall within expected simulation bounds [50, 1000] cycles.",
        "min_cycles_to_failure": min_life,
        "max_cycles_to_failure": max_life,
        "median_cycles_to_failure": median_life,
        "mean_cycles_to_failure": round(mean_life, 2),
        "std_cycles_to_failure": round(std_life, 2),
        "statistical_convention": "Sample standard deviation (ddof=1)"
    }
    if logger:
        logger.info(f"  [Lifespan Bounds] Status: {lifespan_status} | Min: {min_life} | Max: {max_life} | Mean: {mean_life:.1f} | Median: {median_life:.1f}")

    # -------------------------------------------------------------
    # Check 6: Test RUL Alignment & Documentation Discrepancy (Technical)
    # -------------------------------------------------------------
    rul_rows = len(df_rul)
    test_engines = len(te_units)
    rul_aligned = (rul_rows == test_engines)
    
    doc_discrepancy = (dataset_id == "FD004" and test_engines == 248)
    
    rul_status = "PASS" if rul_aligned else "FAIL"
    checks["test_rul_alignment"] = {
        "status": rul_status,
        "dimension": "Technical",
        "contract": "Ground truth RUL vector length must exactly match the number of unique test engines.",
        "test_engines": test_engines,
        "rul_labels_provided": rul_rows,
        "documentation_swapped_discrepancy": doc_discrepancy,
        "reconciliation_note": "In FD004, a documentation/file-count discrepancy was identified during programmatic validation (readme claims 248 train / 249 test; actual files contain 249 train / 248 test)."
    }
    if logger:
        logger.info(f"  [Test RUL Alignment] Status: {rul_status} | Test Units: {test_engines} | RUL Count: {rul_rows}")

    # -------------------------------------------------------------
    # Check 7: Organizational / Decision Context Contracts (Decision / Governance)
    # -------------------------------------------------------------
    checks["operational_decision_context"] = {
        "status": "UNKNOWN",
        "dimension": "Organizational / Decision Context",
        "contract": "Verify whether validated operational maintenance thresholds, economic costs, or real-world failure probabilities exist in the dataset.",
        "validated_maintenance_threshold": "UNKNOWN (Not present in C-MAPSS dataset)",
        "maintenance_cost_matrix": "UNKNOWN (Economic data not included in simulation)",
        "real_world_failure_probability": "UNKNOWN (Simulation models synthetic run-to-failure endpoints)",
        "governance_implication": "All analytical thresholds (e.g., RUL <= 30) must be treated as unratified exploratory boundaries, not operational maintenance policies."
    }
    if logger:
        logger.info("  [Decision Context] Status: UNKNOWN | Maintenance thresholds & economic costs are unobserved in C-MAPSS.")

    # -------------------------------------------------------------
    # Synthesize Final Report
    # -------------------------------------------------------------
    # Overall pipeline execution status: FAIL if any technical/semantic failure;
    # WARN if non-fatal technical observations (e.g. constant sensors) exist.
    overall_status = "PASS"
    for c_name, c_data in checks.items():
        if c_data["status"] == "FAIL":
            overall_status = "FAIL"
            break
        elif c_data["status"] == "WARN" and overall_status != "FAIL":
            overall_status = "WARN"

    report = {
        "dataset_id": dataset_id,
        "overall_status": overall_status,
        "total_train_records": len(df_train),
        "total_test_records": len(df_test),
        "checks": checks
    }
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    if logger:
        logger.info(f"Validation report saved to {report_path} (Overall Status: {overall_status}).")
        
    return report
