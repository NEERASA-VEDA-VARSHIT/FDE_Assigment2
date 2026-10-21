"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Metrics Computation Stage
Computes 5 governed analytical metrics across sensor variation profile,
lifespan heterogeneity, analytical lifecycle exposure, and trajectory completeness.
Exports outputs/metrics.csv adhering to FDE governance statuses.
"""

import numpy as np
import pandas as pd

from .config import OUTPUT_DIR


def run_metrics(canonical_df, raw_bundle, logger=None):
    """
    Computes 5 repeatable analytical metrics from transformed condition-monitoring data.
    Enforces governance labeling: FACT, OBSERVATIONAL, UNRATIFIED, UNKNOWN.
    """
    if logger:
        logger.info("=== STEP 4: METRICS COMPUTATION STAGE ===")

    df_train = raw_bundle["train"]
    total_rows = len(canonical_df)

    # -------------------------------------------------------------
    # Metric 1: Non-Constant Sensor Ratio (FACT / DESCRIPTIVE)
    # -------------------------------------------------------------
    sensor_cols = [f"sensor_{i}" for i in range(1, 22)]
    stds = df_train[sensor_cols].std()
    active_sensors = [col for col in sensor_cols if stds[col] >= 1e-4]

    num_active = len(active_sensors)
    total_sensors = len(sensor_cols)
    non_constant_sensor_ratio = round((num_active / total_sensors) * 100, 2)

    # -------------------------------------------------------------
    # Metric 2: Lifespan Coefficient of Variation (OBSERVATIONAL)
    # -------------------------------------------------------------
    # Calculated per training engine: failure_cycle = max(time_in_cycles)
    # Sample standard deviation (ddof=1)
    engine_lifespans = canonical_df.groupby("unit_number")["total_lifespan"].first()
    mean_life = float(engine_lifespans.mean())
    std_life = float(engine_lifespans.std(ddof=1))
    cv_life = round((std_life / mean_life) * 100, 2)

    # -------------------------------------------------------------
    # Metric 3: Critical Lifecycle Exposure (UNRATIFIED / ANALYTICAL)
    # -------------------------------------------------------------
    # Percentage of total fleet operational snapshots with true_rul <= 30 cycles
    critical_snapshots = int((canonical_df["analytical_lifecycle_stage"] == "CRITICAL").sum())
    critical_fraction = round((critical_snapshots / total_rows) * 100, 2)

    # -------------------------------------------------------------
    # Metric 4: Advisory Lifecycle Exposure (UNRATIFIED / ANALYTICAL)
    # -------------------------------------------------------------
    # Percentage of total fleet operational snapshots with 30 < true_rul <= 60 cycles
    advisory_snapshots = int((canonical_df["analytical_lifecycle_stage"] == "ADVISORY").sum())
    advisory_fraction = round((advisory_snapshots / total_rows) * 100, 2)

    # -------------------------------------------------------------
    # Metric 5: Trajectory Completeness Rate (FACT / TECHNICAL)
    # -------------------------------------------------------------
    # Percentage of engines with start at cycle 1 and zero missing cycle steps
    total_engines = int(df_train["unit_number"].nunique())
    complete_engines = 0
    for u, grp in df_train.groupby("unit_number"):
        cycles = grp["time_in_cycles"].values
        if len(cycles) > 0 and cycles[0] == 1 and np.array_equal(cycles, np.arange(1, len(cycles) + 1)):
            complete_engines += 1

    completeness_rate = round((complete_engines / total_engines) * 100, 2)

    # -------------------------------------------------------------
    # Assemble Governed Metrics Table
    # -------------------------------------------------------------
    metrics_records = [
        {
            "metric_name": "non_constant_sensor_ratio",
            "formula": "count(sensor_std >= 1e-4) / total_sensors * 100",
            "grain": "Dataset Schema (21 sensors)",
            "value_pct": non_constant_sensor_ratio,
            "status": "FACT",
            "interpretation": f"{num_active} of {total_sensors} sensors show within-dataset variation under FD001; 6 are constant",
            "limitation": "Non-constant variance indicates measurement variation, not physical diagnostic causation.",
        },
        {
            "metric_name": "lifespan_coefficient_of_variation",
            "formula": "std(failure_cycle, ddof=1) / mean(failure_cycle) * 100",
            "grain": "Engine Fleet (N = 100 engines)",
            "value_pct": cv_life,
            "status": "OBSERVATIONAL",
            "interpretation": f"Simulated engine trajectories terminate across a wide span ({int(engine_lifespans.min())} to {int(engine_lifespans.max())} cycles)",
            "limitation": "Descriptive measure of simulated spread; does not prove maintenance economics or real-world policy.",
        },
        {
            "metric_name": "critical_lifecycle_exposure",
            "formula": "count(true_rul <= 30) / total_cycles * 100",
            "grain": "Engine-Cycle Snapshot (N = 20,631 records)",
            "value_pct": critical_fraction,
            "status": "UNRATIFIED",
            "interpretation": f"Fraction of training records occurring within 30 cycles of simulated failure endpoint ({critical_snapshots}/{total_rows})",
            "limitation": "Analytical lifecycle segmentation only; threshold of 30 cycles is not validated for operational maintenance.",
        },
        {
            "metric_name": "advisory_lifecycle_exposure",
            "formula": "count(30 < true_rul <= 60) / total_cycles * 100",
            "grain": "Engine-Cycle Snapshot (N = 20,631 records)",
            "value_pct": advisory_fraction,
            "status": "UNRATIFIED",
            "interpretation": f"Fraction of training records occurring within the 31-60 cycle window prior to endpoint ({advisory_snapshots}/{total_rows})",
            "limitation": "Analytical lifecycle segmentation only; threshold is an exploratory analytical boundary.",
        },
        {
            "metric_name": "trajectory_completeness_rate",
            "formula": "count(engines with 0 gaps and cycle_1 start) / total_engines * 100",
            "grain": "Engine Trajectory (N = 100 engines)",
            "value_pct": completeness_rate,
            "status": "FACT",
            "interpretation": f"All {complete_engines} of {total_engines} training engines have unbroken, contiguous cycle sequences",
            "limitation": "Confirms simulated sequence integrity, but does not provide elapsed calendar or flight hours.",
        },
    ]

    metrics_df = pd.DataFrame(metrics_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = OUTPUT_DIR / "metrics.csv"
    metrics_df.to_csv(metrics_path, index=False, encoding="utf-8")

    if logger:
        logger.info(f"Metrics table exported to {metrics_path}")
        for _, r in metrics_df.iterrows():
            logger.info(
                f"  {r['metric_name']:35s} | {r['status']:13s} | {r['value_pct']:6.2f}% | {r['interpretation']}"
            )

    return metrics_df
