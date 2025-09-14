from __future__ import annotations
from pathlib import Path
import re, datetime as dt
from typing import Any, Dict, Iterable
import polars as pl
import yaml

try:
    from src.plots import print_day_timeline
except Exception:
    def print_day_timeline(*args, **kwargs):
        return pl.DataFrame()

# ---------- Patterns (more forgiving) ----------
_PROC_LINE = re.compile(r"^\s*#\s*Procedure\s*:\s*<([^>]+)>\s*$", re.I)
_SECTION_LINE = re.compile(r"^\s*#\s*(Parameters|Metadata|Data)\s*:\s*$", re.I)
_KV_LINE = re.compile(r"^\s*#\s*([^:\n]+?)\s*:\s*(.*?)\s*$")
_DATA_MARK = re.compile(r"^\s*#\s*Data\s*:\s*$", re.I)
_START_TIME = re.compile(r"^\s*#\s*Start\s*time\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.I)

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


########


#######




def run_one_day(
    day_raw_dir: Path,
    *,
    schema_path: Path | None = None,
    out_root: Path = Path("data/metadata"),
    overwrite: bool = True,
    make_timeline: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Parse one subfolder under data/raw and write:
      data/metadata/<same-folder-name>/metadata.csv
      data/metadata/<same-folder-name>/timeline.csv
    """
    day_raw_dir = day_raw_dir.expanduser().resolve()
    if verbose:
        print(f"[run_one_day] raw={day_raw_dir}")

    df_meta = parse_folder_metadata(
        base_dir=day_raw_dir,
        schema_yaml=schema_path,
        save_csv=False,           # we control the output path
        out_name="metadata.csv",
        only_procs=None,
        verbose=verbose,
    )
    if df_meta.height == 0:
        if verbose:
            print(f"[run_one_day] no csvs parsed in {day_raw_dir}")
        return {"raw": str(day_raw_dir), "written": False, "rows": 0}

    # ✅ Use the raw folder name verbatim
    day_id = day_raw_dir.name

    out_dir = (out_root / day_id).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    meta_out = out_dir / "metadata.csv"
    if meta_out.exists() and not overwrite:
        if verbose:
            print(f"[run_one_day] exists, skip: {meta_out}")
    else:
        df_meta.write_csv(meta_out)
        if verbose:
            print(f"[ok] wrote {meta_out}")

    tl_out = out_dir / "timeline.csv"
    if make_timeline:
        try:
            # reuse your printer (it writes <stem>_timeline.csv next to meta_out)
            print_day_timeline(str(meta_out), day_raw_dir, save_csv=True)
            generated = meta_out.with_name(meta_out.stem + "_timeline.csv")
            if generated.exists():
                if tl_out.exists() and overwrite:
                    tl_out.unlink()
                generated.replace(tl_out)
                if verbose:
                    print(f"[ok] wrote {tl_out}")
        except Exception as e:
            if verbose:
                print(f"[warn] timeline generation failed for {day_raw_dir}: {e}")

    return {
        "raw": str(day_raw_dir),
        "day_id": day_id,
        "metadata_csv": str(meta_out),
        "timeline_csv": str(tl_out if tl_out.exists() else ""),
        "rows": df_meta.height,
        "written": True,
    }

def run_all_days(
    raw_root: str | Path = "data/raw",
    *,
    schema: str | Path = "configs/procedures.yml",
    out_root: str | Path = "data/metadata",
    overwrite: bool = True,
    make_timeline: bool = True,
    verbose: bool = True,
) -> pl.DataFrame:
    """
    For each first-level subfolder in raw_root, create a mirrored folder in data/metadata/<same-name>/.
    Also writes data/metadata/_index.csv.
    """
    raw_root = Path(raw_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    schema_path = Path(schema).expanduser().resolve() if schema else None

    if verbose:
        print(f"[run_all_days] raw_root={raw_root} out_root={out_root} schema={schema_path}")

    day_dirs = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    if verbose:
        print(f"[run_all_days] found {len(day_dirs)} candidate folders")

    records = []
    for d in day_dirs:
        if not any(d.rglob("*.csv")):
            if verbose:
                print(f"[skip] {d} (no CSVs)")
            continue
        info = run_one_day(
            d,
            schema_path=schema_path,
            out_root=out_root,
            overwrite=overwrite,
            make_timeline=make_timeline,
            verbose=verbose,
        )
        if info.get("written"):
            records.append(info)

    if not records:
        if verbose:
            print("[run_all_days] nothing written")
        return pl.DataFrame()

    idx = pl.DataFrame(records).select("day_id", "raw", "metadata_csv", "timeline_csv", "rows").sort("day_id")
    out_root.mkdir(parents=True, exist_ok=True)
    idx_path = out_root / "_index.csv"
    idx.write_csv(idx_path)
    if verbose:
        print(f"[ok] wrote {idx_path}")

    return idx

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



def parse_folder_metadata(
    base_dir: Path,
    *,
    schema_yaml: Path | None = None,
    save_csv: bool = True,
    out_name: str = "metadata.csv",
    only_procs: Iterable[str] | None = None,
    verbose: bool = False,
) -> pl.DataFrame:
    schema = _load_schema(schema_yaml)
    all_csvs = [p for p in base_dir.rglob("*.csv") if not p.name.startswith("._")]
    if verbose:
        print(f"[parse_folder] base_dir={base_dir} csvs_found={len(all_csvs)}")

    records = []
    for p in sorted(all_csvs):
        rec = parse_header(p, schema, verbose=verbose)
        if not rec:
            continue
        if only_procs and rec.get("proc") not in set(only_procs):
            continue
        m = re.search(r"_([0-9]+)\.csv$", p.name, re.I)
        rec["file_idx"] = int(m.group(1)) if m else None
        try:
            rec["source_file"] = str(p.relative_to(base_dir))
        except Exception:
            rec["source_file"] = str(p)
        records.append(rec)

    if not records:
        if verbose:
            print("[parse_folder] no records parsed")
        return pl.DataFrame()

    df = pl.DataFrame(records)

    if "proc" in df.columns:
        df = df.with_columns(pl.col("proc").cast(pl.String))
    if "start_time" in df.columns:
        df = df.with_columns(pl.col("start_time").cast(pl.Float64, strict=False))
    if "start_dt" in df.columns and df["start_dt"].dtype != pl.Datetime:
        df = df.with_columns(
            pl.col("start_dt")
            .map_elements(lambda x: x.isoformat() if isinstance(x, dt.datetime) else None, return_dtype=pl.String)
            .str.to_datetime(strict=False)
        )

    if "start_time" in df.columns:
        df = df.sort("start_time", nulls_last=True)

    if save_csv:
        out = base_dir / out_name
        df.write_csv(out)
        print(f"[ok] saved {out}")

    return df




def run(
    folder: str | Path = "data/raw/Alisson_12_sept",
    schema: str | Path = "configs/procedures.yml",
    out_name: str = "Alisson_12_sept_metadata.csv",
    make_timeline: bool = True,
    verbose: bool = False,
):
    base = Path(folder).expanduser().resolve()
    schema_path = Path(schema).expanduser().resolve() if schema else None

    if verbose:
        print(f"[run] base={base} exists={base.exists()} schema={schema_path}")

    df_meta = parse_folder_metadata(
        base_dir=base,
        schema_yaml=schema_path,
        save_csv=True,
        out_name=out_name,
        only_procs=None,
        verbose=verbose,
    )

    if df_meta.height == 0:
        print("[warn] no CSVs parsed")
        return df_meta

    if make_timeline:
        meta_csv_path = base / out_name
        print_day_timeline(str(meta_csv_path), base)

    return df_meta






if __name__ == "__main__":
    # one-liner to process everything
    run_all_days()
