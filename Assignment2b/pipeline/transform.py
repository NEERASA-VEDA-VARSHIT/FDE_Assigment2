"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Transformation Stage
Constructs the canonical engine condition-monitoring table.
Computes per-engine baseline references, cumulative sensor drifts,
exploratory lifecycle progression stages, and dynamic grain invariants.
Exports outputs/final_output.csv (Zero ML, pure telemetry transformation).
"""
import pandas as pd
import numpy as np
from pathlib import Path
from .config import OUTPUT_DIR

def run_transform(data_bundle, logger=None):
    """
    Transforms raw engine sensor observations into an enriched analytical condition-monitoring table.
    Enforces strict grain preservation: exactly 1 row per engine cycle.
    """
    if logger:
        logger.info("=== STEP 3: TRANSFORMATION STAGE ===")
        logger.info("Constructing canonical condition-monitoring model...")
        
    df_train = data_bundle["train"].copy()
    
    # -------------------------------------------------------------
    # 1. Compute Historical Lifecycle & Degradation Ground Truth
    # -------------------------------------------------------------
    # For training data (run-to-failure), maximum cycle per engine defines simulated endpoint
    engine_max_cycles = df_train.groupby("unit_number")["time_in_cycles"].transform("max")
    df_train["total_lifespan"] = engine_max_cycles
    df_train["true_rul"] = df_train["total_lifespan"] - df_train["time_in_cycles"]
    df_train["lifecycle_progression"] = (df_train["time_in_cycles"] / df_train["total_lifespan"]).round(4)
    
    # -------------------------------------------------------------
    # 2. Compute Engine-Specific Baseline Reference (First 5 Cycles)
    # -------------------------------------------------------------
    # In C-MAPSS, each engine simulation initializes with random manufacturing variations
    # Establishing a per-engine baseline across initial cycles centers individual drift trajectories
    early_cycles = df_train[df_train["time_in_cycles"] <= 5]
    
    # Active non-constant sensors under FD001 (stds >= 1e-4)
    active_sensors = [
        "sensor_2", "sensor_3", "sensor_4", "sensor_7",
        "sensor_8", "sensor_9", "sensor_11", "sensor_12",
        "sensor_13", "sensor_14", "sensor_15", "sensor_17",
        "sensor_20", "sensor_21"
    ]
    
    baselines = early_cycles.groupby("unit_number")[active_sensors].mean().reset_index()
    baseline_cols = {col: f"{col}_base" for col in active_sensors}
    baselines = baselines.rename(columns=baseline_cols)
    
    # Join baselines back to train table
    df_transformed = df_train.merge(baselines, on="unit_number", how="left")
    
    # -------------------------------------------------------------
    # 3. Compute Cumulative Physical Sensor Drift
    # -------------------------------------------------------------
    # Delta represents observed deviation from initial early-cycle baseline
    for col in active_sensors:
        base_col = f"{col}_base"
        drift_col = f"{col}_drift"
        df_transformed[drift_col] = (df_transformed[col] - df_transformed[base_col]).round(4)
        
    # -------------------------------------------------------------
    # 4. Standardized Gas-Path Wear Indicators
    # -------------------------------------------------------------
    # Standardize observed drift in exhaust gas temp (sensor_4) and core speed (sensor_9)
    # to provide a dimensionless composite drift indicator for exploratory analysis
    t50_drift = df_transformed["sensor_4_drift"]
    nc_drift = df_transformed["sensor_9_drift"]
    
    t50_std = float(df_transformed["sensor_4"].std())
    nc_std = float(df_transformed["sensor_9"].std())
    
    # 4. Exploratory Standardized Drift Index
    # NOTE: An exploratory composite of standardized deviations in two observed sensor channels.
    # It is not a validated physical wear or health index.
    df_transformed["standardized_drift_index"] = (
        (t50_drift / t50_std) + (nc_drift / nc_std)
    ).round(4)
    
    # -------------------------------------------------------------
    # 5. Exploratory Lifecycle Stage Segmentation
    # -------------------------------------------------------------
    # Categorizes engine operational snapshots into analytical cohorts:
    # - NOMINAL: true_rul > 60 cycles
    # - ADVISORY: 30 < true_rul <= 60 cycles
    # - CRITICAL: true_rul <= 30 cycles
    # NOTE: These are analytical exploratory definitions, NOT validated operational maintenance thresholds.
    def assign_lifecycle_stage(rul):
        if rul > 60:
            return "NOMINAL"
        elif rul > 30:
            return "ADVISORY"
        else:
            return "CRITICAL"
            
    df_transformed["analytical_lifecycle_stage"] = df_transformed["true_rul"].apply(assign_lifecycle_stage)
    
    # Canonical output selection
    canonical_columns = [
        "unit_number",
        "time_in_cycles",
        "op_setting_1",
        "op_setting_2",
        "op_setting_3",
        "sensor_2", "sensor_3", "sensor_4", "sensor_7",
        "sensor_8", "sensor_9", "sensor_11", "sensor_12",
        "sensor_13", "sensor_14", "sensor_15", "sensor_17",
        "sensor_20", "sensor_21",
        "sensor_4_drift",   # T50 drift
        "sensor_9_drift",   # Nc drift
        "standardized_drift_index",
        "total_lifespan",
        "true_rul",
        "lifecycle_progression",
        "analytical_lifecycle_stage"
    ]
    canonical_df = df_transformed[canonical_columns].copy()
    
    # -------------------------------------------------------------
    # 6. Dynamic Grain Assertion (Zero Hard-Coding)
    # -------------------------------------------------------------
    expected_rows = len(df_train)
    total_rows = len(canonical_df)
    unique_snapshots = canonical_df[["unit_number", "time_in_cycles"]].drop_duplicates().shape[0]
    
    if logger:
        logger.info(f"Grain verification: Total rows = {total_rows}, Unique engine-cycles = {unique_snapshots}, Expected = {expected_rows}")
        
    assert total_rows == unique_snapshots, (
        f"Grain violation! Total rows ({total_rows}) != unique engine-cycles ({unique_snapshots}). Cartesian fanout detected!"
    )
    assert total_rows == expected_rows, (
        f"Row count discrepancy! Transformed rows ({total_rows}) != input raw rows ({expected_rows})."
    )
    
    # -------------------------------------------------------------
    # 7. Export Canonical Dataset
    # -------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "final_output.csv"
    canonical_df.to_csv(output_path, index=False, encoding="utf-8")
    
    if logger:
        logger.info(f"Canonical condition-monitoring dataset exported to {output_path} ({total_rows} rows).")
        
    return canonical_df
