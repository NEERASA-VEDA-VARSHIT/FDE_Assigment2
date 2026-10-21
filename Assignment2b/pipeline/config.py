"""
NASA C-MAPSS Jet Engine Dependable Pipeline - Central Configuration
Defines paths, schema definitions, sensor mappings, and structured logging.
"""

import logging
import sys
from pathlib import Path

# Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "CMAPSSData"
if not RAW_DIR.exists() and (BASE_DIR / "data" / "raw" / "cmapss").exists():
    RAW_DIR = BASE_DIR / "data" / "raw" / "cmapss"
OUTPUT_DIR = BASE_DIR / "outputs"

# Active Dataset Selection
DEFAULT_DATASET = "FD001"

# Standard C-MAPSS 26-Column Schema Definitions
COLUMN_NAMES = [
    "unit_number",
    "time_in_cycles",
    "op_setting_1",
    "op_setting_2",
    "op_setting_3",
    "sensor_1",
    "sensor_2",
    "sensor_3",
    "sensor_4",
    "sensor_5",
    "sensor_6",
    "sensor_7",
    "sensor_8",
    "sensor_9",
    "sensor_10",
    "sensor_11",
    "sensor_12",
    "sensor_13",
    "sensor_14",
    "sensor_15",
    "sensor_16",
    "sensor_17",
    "sensor_18",
    "sensor_19",
    "sensor_20",
    "sensor_21",
]

# Physical Engineering Metadata for Sensors (Saxena et al., 2008, Table 2)
SENSOR_METADATA = {
    "sensor_1": {"symbol": "T2", "description": "Total temperature at fan inlet", "units": "deg_R"},
    "sensor_2": {"symbol": "T24", "description": "Total temperature at LPC outlet", "units": "deg_R"},
    "sensor_3": {"symbol": "T30", "description": "Total temperature at HPC outlet", "units": "deg_R"},
    "sensor_4": {"symbol": "T50", "description": "Total temperature at LPT outlet", "units": "deg_R"},
    "sensor_5": {"symbol": "P2", "description": "Pressure at fan inlet", "units": "psia"},
    "sensor_6": {"symbol": "P15", "description": "Total pressure in bypass-duct", "units": "psia"},
    "sensor_7": {"symbol": "P30", "description": "Total pressure at HPC outlet", "units": "psia"},
    "sensor_8": {"symbol": "Nf", "description": "Physical fan speed", "units": "rpm"},
    "sensor_9": {"symbol": "Nc", "description": "Physical core speed", "units": "rpm"},
    "sensor_10": {"symbol": "epr", "description": "Engine pressure ratio (P50/P2)", "units": "--"},
    "sensor_11": {"symbol": "Ps30", "description": "Static pressure at HPC outlet", "units": "psia"},
    "sensor_12": {"symbol": "phi", "description": "Ratio of fuel flow to Ps30", "units": "pps/psi"},
    "sensor_13": {"symbol": "NRf", "description": "Corrected fan speed", "units": "rpm"},
    "sensor_14": {"symbol": "NRc", "description": "Corrected core speed", "units": "rpm"},
    "sensor_15": {"symbol": "BPR", "description": "Bypass Ratio", "units": "--"},
    "sensor_16": {"symbol": "farB", "description": "Burner fuel-air ratio", "units": "--"},
    "sensor_17": {"symbol": "htBleed", "description": "Bleed Enthalpy", "units": "--"},
    "sensor_18": {"symbol": "Nf_dmd", "description": "Demanded fan speed", "units": "rpm"},
    "sensor_19": {"symbol": "PCNfR_dmd", "description": "Demanded corrected fan speed", "units": "rpm"},
    "sensor_20": {"symbol": "W31", "description": "HPT coolant bleed", "units": "lbm/s"},
    "sensor_21": {"symbol": "W32", "description": "LPT coolant bleed", "units": "lbm/s"},
}

# Operational Setting Metadata (Saxena et al., 2008, Section V.D)
SETTING_METADATA = {
    "op_setting_1": {"description": "Flight Altitude", "units": "kft (0-42)"},
    "op_setting_2": {"description": "Mach Number", "units": "Mach (0-0.84)"},
    "op_setting_3": {"description": "Throttle Resolver Angle (TRA)", "units": "deg / % (20-100)"},
}


# Setup Logging
def setup_logging(log_filename="pipeline.log"):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = OUTPUT_DIR / log_filename

    logger = logging.getLogger("cmapss_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
