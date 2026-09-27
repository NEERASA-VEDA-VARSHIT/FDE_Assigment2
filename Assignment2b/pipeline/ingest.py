"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Ingestion Stage
Reads space-delimited text files using robust whitespace parsing, eliminates
trailing-whitespace column pollution, assigns canonical schemas, and returns
the validated data bundle.
"""
import pandas as pd
from pathlib import Path
from .config import RAW_DIR, COLUMN_NAMES, DEFAULT_DATASET

def load_cmapss_dataset(dataset_id=DEFAULT_DATASET, raw_dir=RAW_DIR, logger=None):
    """
    Ingests training, test, and RUL truth files for the specified C-MAPSS variant.
    Uses regex whitespace delimiter to avoid the 28-column trailing space parser trap.
    """
    if logger:
        logger.info(f"=== STEP 1: INGESTION STAGE ({dataset_id}) ===")
        logger.info(f"Loading raw files from {raw_dir}...")
        
    train_path = raw_dir / f"train_{dataset_id}.txt"
    test_path = raw_dir / f"test_{dataset_id}.txt"
    rul_path = raw_dir / f"RUL_{dataset_id}.txt"
    
    for p in [train_path, test_path, rul_path]:
        if not p.exists():
            raise FileNotFoundError(f"Required raw C-MAPSS file missing: {p}")
            
    # Ingest using whitespace regex (sep=r'\s+')
    # This prevents the trailing space on each line from creating two spurious NaN columns (cols 26 & 27)
    df_train = pd.read_csv(train_path, sep=r"\s+", header=None, names=COLUMN_NAMES)
    df_test = pd.read_csv(test_path, sep=r"\s+", header=None, names=COLUMN_NAMES)
    df_rul = pd.read_csv(rul_path, sep=r"\s+", header=None, names=["true_rul"])
    
    # Cast identifiers to integer
    df_train["unit_number"] = df_train["unit_number"].astype(int)
    df_train["time_in_cycles"] = df_train["time_in_cycles"].astype(int)
    
    df_test["unit_number"] = df_test["unit_number"].astype(int)
    df_test["time_in_cycles"] = df_test["time_in_cycles"].astype(int)
    df_rul["true_rul"] = df_rul["true_rul"].astype(int)
    
    # Check NaN absence
    train_nans = int(df_train.isna().sum().sum())
    test_nans = int(df_test.isna().sum().sum())
    rul_nans = int(df_rul.isna().sum().sum())
    
    if train_nans > 0 or test_nans > 0 or rul_nans > 0:
        raise ValueError(
            f"Schema corruption detected during ingestion! Train NaNs: {train_nans}, Test NaNs: {test_nans}, RUL NaNs: {rul_nans}"
        )
        
    train_engines = df_train["unit_number"].nunique()
    test_engines = df_test["unit_number"].nunique()
    rul_count = len(df_rul)
    
    if logger:
        logger.info(f"  Train: {len(df_train)} rows across {train_engines} engines (Cols: {df_train.shape[1]}).")
        logger.info(f"  Test:  {len(df_test)} rows across {test_engines} engines (Cols: {df_test.shape[1]}).")
        logger.info(f"  RUL:   {rul_count} ground-truth test labels loaded.")
        logger.info(f"Ingestion verified: 0 missing values, strict 26-column schema established.")
        
    return {
        "dataset_id": dataset_id,
        "train": df_train,
        "test": df_test,
        "rul": df_rul
    }
