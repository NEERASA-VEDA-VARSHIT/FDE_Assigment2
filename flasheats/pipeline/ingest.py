"""
FlashEats Dependable Pipeline - Ingestion Stage
Handles SQLite extraction, flat-file loading, and dynamic paginated API ingestion with retry and raw preservation.
"""
import sqlite3
import json
import time
import requests
import pandas as pd
from pathlib import Path
from .config import (
    DB_PATH, DATA_DIR, RAW_DIR, DISPATCH_ORDERS_ENDPOINT,
    DEFAULT_PAGE_SIZE, MAX_API_RETRIES, DEFAULT_RETRY_DELAY_SEC
)

class IngestionError(Exception):
    """Custom exception raised when an unrecoverable ingestion failure occurs."""
    pass

def extract_sqlite_tables(db_path=DB_PATH, logger=None):
    """Extracts relational tables from the SQLite database."""
    if not Path(db_path).exists():
        raise IngestionError(f"Database not found at: {db_path}")
    
    if logger:
        logger.info(f"Extracting SQLite tables from {db_path}...")
        
    con = sqlite3.connect(db_path)
    try:
        orders = pd.read_sql("SELECT * FROM orders", con)
        customers = pd.read_sql("SELECT * FROM customers", con)
        drivers = pd.read_sql("SELECT * FROM drivers", con)
        restaurants = pd.read_sql("SELECT * FROM restaurants", con)
        
        if logger:
            logger.info(f"  orders: {orders.shape}, customers: {customers.shape}, drivers: {drivers.shape}, restaurants: {restaurants.shape}")
            
        return {
            "orders": orders,
            "customers": customers,
            "drivers": drivers,
            "restaurants": restaurants
        }
    finally:
        con.close()

def load_file_sources(data_dir=DATA_DIR, logger=None):
    """Loads CSVs and JSON files from the data directory."""
    if logger:
        logger.info(f"Loading CSV and JSON sources from {data_dir}...")
        
    tickets = pd.read_csv(data_dir / "support_tickets.csv")
    restaurant_status = pd.read_csv(data_dir / "restaurant_status.csv")
    customer_actions = pd.read_csv(data_dir / "customer_app_actions.csv")
    interventions = pd.read_csv(data_dir / "order_interventions.csv")
    outcomes = pd.read_csv(data_dir / "order_outcomes.csv")
    
    with open(data_dir / "driver_events.json", "r", encoding="utf-8") as f:
        driver_events = json.load(f)
        
    with open(data_dir / "client_metric_definitions.json", "r", encoding="utf-8") as f:
        metric_definitions = json.load(f)
        
    if logger:
        logger.info(f"  tickets: {tickets.shape}, restaurant_status: {restaurant_status.shape}, actions: {customer_actions.shape}, interventions: {interventions.shape}, outcomes: {outcomes.shape}, driver_events: {len(driver_events)}")
        
    return {
        "tickets": tickets,
        "restaurant_status": restaurant_status,
        "customer_actions": customer_actions,
        "interventions": interventions,
        "outcomes": outcomes,
        "driver_events": driver_events,
        "metric_definitions": metric_definitions
    }

def fetch_dispatch_api_records(
    endpoint=DISPATCH_ORDERS_ENDPOINT,
    raw_dir=RAW_DIR,
    page_size=DEFAULT_PAGE_SIZE,
    max_retries=MAX_API_RETRIES,
    logger=None
):
    """
    Dynamically paginates through the Dispatch API until has_more is False,
    retrying transient errors and rate limits, preserving raw JSON responses,
    and verifying record count completeness dynamically.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    records = []
    page = 1
    total_retries = 0
    reported_total = None
    
    if logger:
        logger.info(f"Starting dynamic API ingestion from {endpoint} (page_size={page_size})...")
        
    while True:
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(
                    endpoint,
                    params={"page": page, "page_size": page_size},
                    timeout=10
                )
                
                # Check for HTTP 500 (Temporary Upstream Failure)
                if response.status_code == 500:
                    err_info = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    if logger:
                        logger.warning(f"  [Page {page}] HTTP 500 received ({err_info.get('error', 'Server Error')}). Attempt {attempt}/{max_retries}. Retrying in {DEFAULT_RETRY_DELAY_SEC}s...")
                    total_retries += 1
                    time.sleep(DEFAULT_RETRY_DELAY_SEC)
                    continue
                    
                # Check for HTTP 429 (Rate Limit Exceeded)
                elif response.status_code == 429:
                    err_info = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    retry_wait = err_info.get("retry_after_seconds", 1)
                    if logger:
                        logger.warning(f"  [Page {page}] HTTP 429 received ({err_info.get('error', 'Rate Limited')}). Waiting {retry_wait}s before retry...")
                    total_retries += 1
                    time.sleep(retry_wait)
                    continue
                    
                response.raise_for_status()
                payload = response.json()
                
                # Deterministic Raw Preservation: overwrite/update deterministic filename
                raw_file = raw_dir / f"page_{page}.json"
                with open(raw_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    
                page_data = payload.get("data", [])
                records.extend(page_data)
                has_more = payload.get("has_more", False)
                reported_total = payload.get("total_records", reported_total)
                
                success = True
                break
                
            except Exception as e:
                if logger:
                    logger.warning(f"  [Page {page}] Network/Request exception on attempt {attempt}: {e}")
                time.sleep(1)
                
        if not success:
            msg = f"API ingestion failed permanently on page {page} after {max_retries} attempts."
            if logger:
                logger.error(msg)
            raise IngestionError(msg)
            
        if not has_more:
            if logger:
                logger.info(f"Reached final page ({page}). Pagination complete.")
            break
            
        page += 1
        
    retrieved_count = len(records)
    if logger:
        logger.info(f"Ingestion completeness check: Retrieved {retrieved_count} records across {page} pages; API reported total: {reported_total}.")
        
    if reported_total is not None and retrieved_count != reported_total:
        msg = f"API Ingestion Incomplete: retrieved {retrieved_count} records but API reported {reported_total} total records!"
        if logger:
            logger.error(msg)
        raise IngestionError(msg)
        
    return {
        "records": records,
        "total_pages": page,
        "reported_total": reported_total,
        "retrieved_total": retrieved_count,
        "retries_handled": total_retries
    }

def run_ingestion(logger=None):
    """Orchestrates the entire ingestion stage."""
    if logger:
        logger.info("=== STEP 1: INGESTION STAGE ===")
    db_data = extract_sqlite_tables(logger=logger)
    file_data = load_file_sources(logger=logger)
    api_data = fetch_dispatch_api_records(logger=logger)
    
    return {
        **db_data,
        **file_data,
        "dispatch_api": api_data
    }
