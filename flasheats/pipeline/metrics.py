"""
FlashEats Dependable Pipeline - Metrics Stage
Computes governed operational metrics and candidate KPI definitions dynamically.
Distinguishes pipeline calculations from ratified KPIs using explicit governance statuses (UNRATIFIED vs OBSERVATIONAL).
"""

import pandas as pd

from .config import OUTPUT_DIR


def run_metrics(canonical_df, raw_orders, outcomes, logger=None):
    """
    Computes all candidate KPIs and operational metrics dynamically from data.
    Exports structured metrics to outputs/metrics.csv.
    """
    if logger:
        logger.info("=== STEP 4: METRICS COMPUTATION STAGE ===")

    total_orders = len(canonical_df)

    # -------------------------------------------------------------
    # 1. Candidate KPI Definitions (Late Delivery Rate)
    # -------------------------------------------------------------
    # Population A: Delivered orders with non-null completion timestamp
    valid_outcomes = outcomes[outcomes["late_flag"].notna()]
    total_delivered_evaluated = len(valid_outcomes)
    late_gt_0_count = int((valid_outcomes["late_flag"] == 1.0).sum())
    late_gt_10_count = int((valid_outcomes["delay_min"] > 10.0).sum())

    rate_gt_0 = (
        round((late_gt_0_count / total_delivered_evaluated * 100.0), 2)
        if total_delivered_evaluated > 0
        else 0
    )
    rate_gt_10 = (
        round((late_gt_10_count / total_delivered_evaluated * 100.0), 2)
        if total_delivered_evaluated > 0
        else 0
    )

    # Population B: All delivered orders (including 37 missing timestamps)
    delivered_all = canonical_df[canonical_df["final_status"].str.lower() == "delivered"]
    total_delivered_all = len(delivered_all)
    rate_all_delivered = (
        round((late_gt_0_count / total_delivered_all * 100.0), 2) if total_delivered_all > 0 else 0
    )

    # Population C: Total placed orders (all unique orders)
    rate_total_placed = round((late_gt_0_count / total_orders * 100.0), 2) if total_orders > 0 else 0

    # -------------------------------------------------------------
    # 2. Workflow & Operational Friction Metrics
    # -------------------------------------------------------------
    # Customer Friction Rate (support opened or cancel attempted)
    friction_mask = (canonical_df["support_opened"] == 1) | (canonical_df["cancel_attempted"] == 1)
    friction_count = int(friction_mask.sum())
    friction_rate = round((friction_count / total_orders * 100.0), 2) if total_orders > 0 else 0

    # Operational Intervention Rate
    intervened_mask = canonical_df["intervention_count"] > 0
    intervened_count = int(intervened_mask.sum())
    intervention_rate = round((intervened_count / total_orders * 100.0), 2) if total_orders > 0 else 0

    # Intervention Rescue Rate (Observational Recovery Metric)
    # Evaluated among intervened orders with valid outcome
    intervened_evaluated = canonical_df[intervened_mask & canonical_df["late_flag"].notna()]
    total_intervened_evaluated = len(intervened_evaluated)
    rescued_count = int((intervened_evaluated["late_flag"] == 0.0).sum())
    rescue_rate = (
        round((rescued_count / total_intervened_evaluated * 100.0), 2)
        if total_intervened_evaluated > 0
        else 0
    )

    # -------------------------------------------------------------
    # 3. Assemble Structured Metrics Table
    # -------------------------------------------------------------
    metrics_records = [
        {
            "metric_name": "late_delivery_rate",
            "definition": "delay > 0 min among delivered orders with non-null completion timestamp",
            "numerator": late_gt_0_count,
            "denominator": total_delivered_evaluated,
            "value_pct": rate_gt_0,
            "status": "UNRATIFIED",
            "category": "Outcome (Candidate KPI - Historical / VP Ops)",
            "governance_note": "Unratified candidate metric. Dropping 37 delivered orders without documentation creates 1.36pp shift.",
        },
        {
            "metric_name": "late_delivery_rate",
            "definition": "delay > 10 min among delivered orders with non-null completion timestamp",
            "numerator": late_gt_10_count,
            "denominator": total_delivered_evaluated,
            "value_pct": rate_gt_10,
            "status": "UNRATIFIED",
            "category": "Outcome (Candidate KPI - Support Lead)",
            "governance_note": "Unratified candidate metric. Incorporates 10-minute customer friction tolerance buffer.",
        },
        {
            "metric_name": "late_delivery_rate",
            "definition": "delay > 0 min among all unique delivered orders (including missing timestamps)",
            "numerator": late_gt_0_count,
            "denominator": total_delivered_all,
            "value_pct": rate_all_delivered,
            "status": "UNRATIFIED",
            "category": "Outcome (Candidate KPI - Conservative Delivered)",
            "governance_note": "Unratified candidate metric. Assumes missing completion timestamps are non-late or unproven.",
        },
        {
            "metric_name": "late_delivery_rate",
            "definition": "delay > 0 min among total unique orders placed (including cancellations)",
            "numerator": late_gt_0_count,
            "denominator": total_orders,
            "value_pct": rate_total_placed,
            "status": "UNRATIFIED",
            "category": "Outcome (Candidate KPI - Total Fulfillment)",
            "governance_note": "Unratified candidate metric. Captures platform-wide fulfillment rate.",
        },
        {
            "metric_name": "customer_friction_rate",
            "definition": "orders where customer opened support or attempted cancellation",
            "numerator": friction_count,
            "denominator": total_orders,
            "value_pct": friction_rate,
            "status": "OBSERVATIONAL",
            "category": "Customer Interaction",
            "governance_note": "Leading indicator of churn and dissatisfaction before or during delivery.",
        },
        {
            "metric_name": "operational_intervention_rate",
            "definition": "orders receiving at least one operational remedy (dispatch / support / merchant)",
            "numerator": intervened_count,
            "denominator": total_orders,
            "value_pct": intervention_rate,
            "status": "OBSERVATIONAL",
            "category": "Operational Workflow",
            "governance_note": "Measures manual intervention overhead and workflow instability.",
        },
        {
            "metric_name": "intervention_rescue_rate",
            "definition": "intervened orders successfully delivered on-time (delay <= 0 min)",
            "numerator": rescued_count,
            "denominator": total_intervened_evaluated,
            "value_pct": rescue_rate,
            "status": "OBSERVATIONAL",
            "category": "Operational Recovery (Observational)",
            "governance_note": "Strictly observational recovery metric. Must NOT be interpreted as causal proof that interventions caused recovery due to adverse selection (interventions applied selectively to severely delayed orders).",
        },
    ]

    metrics_df = pd.DataFrame(metrics_records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics_csv_path = OUTPUT_DIR / "metrics.csv"
    metrics_df.to_csv(metrics_csv_path, index=False, encoding="utf-8")

    if logger:
        logger.info(f"Metrics table exported to {metrics_csv_path}")
        for _, r in metrics_df.iterrows():
            logger.info(
                f"  {r['metric_name']:30s} | {r['status']:13s} | {r['value_pct']:6.2f}% ({r['numerator']}/{r['denominator']}) | {r['definition']}"
            )

    return metrics_df
