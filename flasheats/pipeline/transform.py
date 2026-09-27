"""
FlashEats Dependable Pipeline - Transformation Stage
Pre-aggregates one-to-many event streams to prevent Cartesian join multiplication,
safely normalizes representations, constructs the canonical order-level model,
asserts grain uniqueness dynamically, and exports final_output.csv.
"""
import pandas as pd
from pathlib import Path
from .config import OUTPUT_DIR

def run_transform(data_bundle, logger=None):
    """
    Transforms raw and validated datasets into the canonical order-level model.
    Applies strict pre-aggregation on 1-to-many event streams before joining.
    """
    if logger:
        logger.info("=== STEP 3: TRANSFORMATION STAGE ===")
        
    orders = data_bundle["orders"]
    customer_actions = data_bundle["customer_actions"]
    tickets = data_bundle["tickets"]
    interventions = data_bundle["interventions"]
    outcomes = data_bundle["outcomes"]
    
    # -------------------------------------------------------------
    # 1. Pre-aggregate One-to-Many Event Sources
    # -------------------------------------------------------------
    if logger:
        logger.info("Pre-aggregating one-to-many event tables to order grain...")
        
    # A. Customer App Actions
    actions_agg = customer_actions.groupby("order_id").agg(
        app_action_count=("action_id", "count"),
        cancel_attempted=("action_type", lambda s: int((s == "CANCEL_ATTEMPTED").any())),
        support_opened_app=("action_type", lambda s: int((s.isin(["SUPPORT_CONTACTED", "HELP_CLICKED"])).any()))
    ).reset_index()
    
    # B. Support Tickets
    valid_tickets = tickets[tickets["order_id"].notna()].copy()
    tickets_agg = valid_tickets.groupby("order_id").agg(
        support_ticket_count=("ticket_id", "count")
    ).reset_index()
    tickets_agg["support_opened_ticket"] = 1
    
    # C. Order Interventions
    interventions_agg = interventions.groupby("order_id").agg(
        intervention_count=("intervention_id", "count"),
        intervention_types=("intervention_type", lambda s: "; ".join(sorted(s.unique())))
    ).reset_index()
    
    # -------------------------------------------------------------
    # 2. Deduplicate Base Orders Deterministically
    # -------------------------------------------------------------
    base_orders = orders.drop_duplicates("order_id", keep="first")[
        ["order_id", "customer_id", "restaurant_id", "driver_id", "final_status"]
    ].copy()
    
    # Safely normalize final_status casing
    base_orders["final_status"] = base_orders["final_status"].astype(str).str.lower().str.strip()
    
    # -------------------------------------------------------------
    # 3. Join Order-Level Dimensions & Outcomes
    # -------------------------------------------------------------
    if logger:
        logger.info("Joining pre-aggregated event dimensions to order outcomes...")
        
    order_model = outcomes.merge(base_orders, on="order_id", how="left")
    order_model = order_model.merge(actions_agg, on="order_id", how="left")
    order_model = order_model.merge(tickets_agg, on="order_id", how="left")
    order_model = order_model.merge(interventions_agg, on="order_id", how="left")
    
    # Reconcile flags
    order_model["cancel_attempted"] = order_model["cancel_attempted"].fillna(0).astype(int)
    order_model["support_opened_app"] = order_model["support_opened_app"].fillna(0).astype(int)
    order_model["support_opened_ticket"] = order_model["support_opened_ticket"].fillna(0).astype(int)
    order_model["support_opened"] = (
        (order_model["support_opened_app"] == 1) | (order_model["support_opened_ticket"] == 1)
    ).astype(int)
    
    order_model["intervention_count"] = order_model["intervention_count"].fillna(0).astype(int)
    order_model["intervention_types"] = order_model["intervention_types"].fillna("NONE")
    
    # Ensure final_status matches normalized status
    if "final_status_norm" in order_model.columns:
        order_model["final_status"] = order_model["final_status_norm"]
        
    # Canonical columns
    canonical_columns = [
        "order_id",
        "customer_id",
        "support_opened",
        "cancel_attempted",
        "intervention_count",
        "intervention_types",
        "final_status",
        "late_flag",
        "delay_min"
    ]
    canonical_df = order_model[canonical_columns].copy()
    
    # -------------------------------------------------------------
    # 4. Dynamic Grain Assertion (Zero Hard-Coding)
    # -------------------------------------------------------------
    expected_order_count = orders["order_id"].nunique()
    total_rows = len(canonical_df)
    unique_orders = canonical_df["order_id"].nunique()
    
    if logger:
        logger.info(f"Grain verification: Total rows = {total_rows}, Unique order_ids = {unique_orders}, Expected orders = {expected_order_count}")
        
    assert canonical_df["order_id"].is_unique, (
        f"Grain violation! order_id is not unique in canonical model ({total_rows - unique_orders} duplicate occurrences)."
    )
    assert total_rows == unique_orders, (
        f"Grain violation! Total rows ({total_rows}) != unique order_ids ({unique_orders}). "
        "A join caused Cartesian row multiplication."
    )
    assert total_rows == expected_order_count, (
        f"Order count discrepancy! Transformed rows ({total_rows}) != expected base orders ({expected_order_count})."
    )
    
    # -------------------------------------------------------------
    # 5. Export Canonical Dataset
    # -------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "final_output.csv"
    canonical_df.to_csv(output_path, index=False, encoding="utf-8")
    
    if logger:
        logger.info(f"Canonical order-level dataset exported to {output_path} ({total_rows} rows).")
        
    return canonical_df
