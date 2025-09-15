from __future__ import annotations
from pathlib import Path
import re, datetime as dt
from typing import Any, Dict
import polars as pl
import yaml

from parser_utils import (_short_proc,
                                         _infer_proc_from_name,
                                         _coerce,
                                        _epoch_or_mtime,
)

try:
    from src.ploting.plots import print_day_timeline
except Exception:
    def print_day_timeline(*args, **kwargs):
        return pl.DataFrame()

_TYPE_MAP = {
    "int": int,
    "float": float,
    "str": str,
    "bool": lambda x: str(x).strip().lower() in {"1","true","t","yes","y","on"},
    "datetime": "datetime",
    "float_no_unit": float,
}


# ---------- Patterns (more forgiving) ----------
_PROC_LINE = re.compile(r"^\s*#\s*Procedure\s*:\s*<([^>]+)>\s*$", re.I)
_SECTION_LINE = re.compile(r"^\s*#\s*(Parameters|Metadata|Data)\s*:\s*$", re.I)
_KV_LINE = re.compile(r"^\s*#\s*([^:\n]+?)\s*:\s*(.*?)\s*$")
_DATA_MARK = re.compile(r"^\s*#\s*Data\s*:\s*$", re.I)
_START_TIME = re.compile(r"^\s*#\s*Start\s*time\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.I)


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





#######



def parse_header(path: Path, schema: dict[str, Any], *, verbose: bool=False) -> dict[str, Any]:
    proc_full = None
    section = None
    parsed: dict[str, dict[str, Any]] = {"Parameters": {}, "Metadata": {}}
    start_time_str = None

    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if _DATA_MARK.match(line):
                    break
                m = _PROC_LINE.match(line)
                if m:
                    proc_full = m.group(1).strip()
                    continue
                m = _SECTION_LINE.match(line)
                if m:
                    section = m.group(1)
                    continue
                sm = _START_TIME.match(line)
                if sm:
                    start_time_str = sm.group(1).strip()
                m = _KV_LINE.match(line)
                if m and section in ("Parameters", "Metadata"):
                    key = m.group(1).strip()
                    val = m.group(2).strip()
                    parsed[section][key] = val
    except Exception as e:
        if verbose:
            print(f"[parse_header] error reading {path}: {e}")
        return {}

    proc_short = _short_proc(proc_full) if proc_full else None
    if not proc_short or proc_short == "?":
        proc_short = _infer_proc_from_name(path) or "?"

    if schema and "procedures" in schema and proc_short in schema["procedures"]:
        spec = schema["procedures"][proc_short]
        for sec_name in ("Parameters", "Metadata"):
            exp = (spec.get(sec_name) or {})
            for k, v in list(parsed[sec_name].items()):
                expected = exp.get(k)
                if expected is None:
                    k_norm = re.sub(r"\s*\([^)]*\)\s*$", "", k)
                    expected = exp.get(k_norm)
                parsed[sec_name][k] = _coerce(v, expected)

        if "Metadata" in spec and "Start time" in spec["Metadata"]:
            st_coerced = _coerce(start_time_str, "datetime")
            if isinstance(st_coerced, dt.datetime):
                start_dt = st_coerced
                start_time = start_dt.timestamp()
            else:
                start_time, start_dt = _epoch_or_mtime(start_time_str, path)
        else:
            start_time, start_dt = _epoch_or_mtime(start_time_str, path)
    else:
        start_time, start_dt = _epoch_or_mtime(start_time_str, path)

    out: Dict[str, Any] = {
        "procedure_full": proc_full,
        "proc": proc_short,
        "start_time": start_time,
        "start_dt": start_dt,
        "source_file": str(path),  # relative later
    }
    for sec in ("Parameters", "Metadata"):
        for k, v in parsed[sec].items():
            out[k] = v

    if verbose:
        print(f"[parse_header] {path.name}: proc={out['proc']} start_time={out['start_time']} fields={len(out)}")
    return out
