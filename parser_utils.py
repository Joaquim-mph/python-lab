from __future__ import annotations
from pathlib import Path
import re, datetime as dt
from typing import Any
import polars as pl
import yaml


_TYPE_MAP = {
    "int": int,
    "float": float,
    "str": str,
    "bool": lambda x: str(x).strip().lower() in {"1","true","t","yes","y","on"},
    "datetime": "datetime",
    "float_no_unit": float,
}

def _load_schema(yaml_path: Path | None) -> dict[str, Any]:
    if not yaml_path or not yaml_path.exists():
        return {}
    with yaml_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _short_proc(proc_full: str | None) -> str:
    if not proc_full:
        return "?"
    return proc_full.split(".")[-1]

def _infer_proc_from_name(path: Path) -> str | None:
    name = path.name.lower()
    if "ivgt" in name: return "IVgT"
    if "ivg" in name:  return "IVg"
    if re.search(r"(^|[^a-z])it[^a-z]", name): return "It"  # 'It' but not 'IV'
    if re.search(r"(^|[^a-z])iv([^a-z]|$)", name): return "IV"
    if "lasercalibration" in name: return "LaserCalibration"
    if "itt" in name: return "ITt"
    return None

def _coerce(value: str | None, expected: str | None) -> Any:
    if value is None or value == "":
        return None

    num_pat = re.compile(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")

    if expected is None:
        v = value.strip()
        if re.fullmatch(r"[+-]?\d+", v):
            try: return int(v)
            except: return v
        if re.fullmatch(r"[+-]?\d*(\.\d+)?([eE][+-]?\d+)?", v):
            try: return float(v)
            except: return v
        lv = v.lower()
        if lv in {"true","false"}:
            return lv == "true"
        return v

    typ = _TYPE_MAP.get(expected, str)

    if typ in (int, float):
        m = num_pat.search(str(value))
        if not m:
            return None
        try:
            return typ(m.group(0))
        except Exception:
            return None

    if typ == "datetime":
        try:
            v = str(value).strip()
            if re.fullmatch(r"\d+(\.\d+)?", v):
                return dt.datetime.fromtimestamp(float(v))
            return dt.datetime.fromisoformat(v)
        except Exception:
            return None

    try:
        return typ(value)
    except Exception:
        return value

def _epoch_or_mtime(start_time_str: str | None, path: Path) -> tuple[float | None, dt.datetime | None]:
    ts = None
    if start_time_str and re.fullmatch(r"\d+(\.\d+)?", start_time_str.strip()):
        try:
            ts = float(start_time_str)
        except Exception:
            ts = None
    if ts is None:
        try:
            ts = path.stat().st_mtime
        except Exception:
            return None, None
    try:
        return ts, dt.datetime.fromtimestamp(ts)
    except Exception:
        return ts, None


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip()).strip("-")
    return s or "unknown"

def _day_from_df(df: pl.DataFrame) -> str | None:
    """
    Try to infer a canonical day (YYYY-MM-DD) from 'start_dt' if present.
    Returns None if not available.
    """
    if "start_dt" not in df.columns or df["start_dt"].null_count() == df.height:
        return None
    # take min datetime in that day as the representative date
    try:
        dmin = df.select(pl.col("start_dt").min()).item()
        if isinstance(dmin, dt.datetime):
            return dmin.date().isoformat()
        # Polars Datetime -> Python datetime
        if dmin is not None:
            dmin_py = pl.Series([dmin]).dt.to_python_datetime()[0]
            return dmin_py.date().isoformat()
    except Exception:
        pass
    return None