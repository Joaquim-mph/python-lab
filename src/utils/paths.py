from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RAW = DATA / "00_raw"
META = DATA / "01_metadata"
WAREHOUSE = REPO / "02_warehouse"  # or DATA / "warehouse" if you prefer
CONFIG = REPO / "config" 