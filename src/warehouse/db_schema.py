# src/warehouse/schema_from_yaml.py
from __future__ import annotations
from pathlib import Path
from typing import Dict
import yaml
import polars as pl

# Map your YAML scalar types -> Polars dtypes
_YAML2PL: Dict[str, pl.DataType] = {
    "float": pl.Float64,
    "float_no_unit": pl.Float64,   # alias in your YAML
    "int": pl.Int64,
    "bool": pl.Boolean,
    "str": pl.Utf8,
    # "datetime" appears in Metadata; your Data sections don’t use it.
    # If you ever had datetime columns in Data, add: "datetime": pl.Datetime
}

def build_schema_overrides_from_yaml(yaml_path: str | Path) -> dict[str, dict[str, pl.DataType]]:
    """
    Read procedures.yml and create:
        { "<PROC>": { "<Data column name>": PolarsDtype, ... }, ... }
    These keys must match *exactly* the CSV header text (incl. spaces/units).
    """
    yaml_path = Path(yaml_path)
    with yaml_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    out: dict[str, dict[str, pl.DataType]] = {}
    procs = (cfg.get("procedures") or {})
    for proc_name, sections in procs.items():
        data_sec = (sections or {}).get("Data") or {}
        if not data_sec:
            # Nothing to pin for this proc
            continue
        dmap: dict[str, pl.DataType] = {}
        for col_name, ytype in data_sec.items():
            ytype = str(ytype).strip()
            pltype = _YAML2PL.get(ytype, pl.Utf8)  # default to Utf8 if unknown
            dmap[str(col_name)] = pltype
        out[proc_name] = dmap
    return out
