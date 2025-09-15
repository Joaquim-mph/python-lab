from __future__ import annotations
from pathlib import Path
import re, datetime as dt
from typing import Any, Dict, Iterable
import polars as pl
from parser_utils import (_load_schema, 
                                         _short_proc,
                                         _infer_proc_from_name,
                                         _coerce,
                                        _epoch_or_mtime,
)

try:
    from src.ploting.plots import print_day_timeline
except Exception:
    def print_day_timeline(*args, **kwargs):
        return pl.DataFrame()

# ---------- Patterns (more forgiving) ----------
_PROC_LINE = re.compile(r"^\s*#\s*Procedure\s*:\s*<([^>]+)>\s*$", re.I)
_SECTION_LINE = re.compile(r"^\s*#\s*(Parameters|Metadata|Data)\s*:\s*$", re.I)
_KV_LINE = re.compile(r"^\s*#\s*([^:\n]+?)\s*:\s*(.*?)\s*$")
_DATA_MARK = re.compile(r"^\s*#\s*Data\s*:\s*$", re.I)
_START_TIME = re.compile(r"^\s*#\s*Start\s*time\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.I)


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

    records: list[dict] = []
    for p in sorted(all_csvs):
        rec = parse_header(p, schema, verbose=verbose)
        if not rec:
            continue
        if only_procs and rec.get("proc") not in set(only_procs):
            continue

        # file index from name ..._NN.csv
        m = re.search(r"_([0-9]+)\.csv$", p.name, re.I)
        rec["file_idx"] = int(m.group(1)) if m else None

        # normalized source_file (relative to base_dir if possible)
        try:
            rec["source_file"] = str(p.relative_to(base_dir))
        except Exception:
            rec["source_file"] = str(p)

        records.append(rec)

    if not records:
        if verbose:
            print("[parse_folder] no records parsed")
        return pl.DataFrame()

    # --------- normalize records BEFORE DataFrame (avoid mixed dtypes) ---------
    def _iso(val):
        if isinstance(val, dt.datetime):
            return val.isoformat()
        return val

    clean_records: list[dict] = []
    for rec in records:
        r2 = {}
        for k, v in rec.items():
            # stringify any datetime values (any key) to avoid schema flips
            r2[k] = _iso(v)
        clean_records.append(r2)

    # Build DF with a larger inference window to stabilize schema
    try:
        df = pl.from_dicts(clean_records, infer_schema_length=10000)
    except Exception as e:
        if verbose:
            # quick debug for mixed columns
            from collections import defaultdict
            types = defaultdict(set)
            for row in clean_records:
                for k, v in row.items():
                    types[k].add(type(v).__name__)
            mixed = {k: t for k, t in types.items() if len(t) > 1}
            print("[parse_folder][schema debug] mixed columns:", mixed)
        raise

    # Drop duplicate raw "Start time" header if structured columns exist
    if "Start time" in df.columns and (("start_time" in df.columns) or ("start_dt" in df.columns)):
        df = df.drop("Start time")

    # --------- cast to desired dtypes (safe casts) ---------
    if "proc" in df.columns:
        df = df.with_columns(pl.col("proc").cast(pl.Utf8, strict=False))

    if "start_time" in df.columns:
        df = df.with_columns(pl.col("start_time").cast(pl.Float64, strict=False))

    if "start_dt" in df.columns:
        # convert ISO strings (or None) → Datetime
        if df["start_dt"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.col("start_dt")
                  .cast(pl.Utf8, strict=False)
                  .str.to_datetime(strict=False)
            )

    # (optional) try to make common numeric fields numeric without failing
    likely_nums = [c for c in df.columns if c.endswith(("_v","_a","_degc","_ms","_step","_start","_end"))
                   or c in {"vg","vds","vl","laser_wavelength","file_idx","chip_number"}]
    for c in likely_nums:
        if c in df.columns:
            df = df.with_columns(pl.col(c).cast(pl.Float64, strict=False))
    if "chip_number" in df.columns:
        df = df.with_columns(pl.col("chip_number").cast(pl.Int64, strict=False))

    # --------- sort & save ---------
    if "start_time" in df.columns:
        df = df.sort("start_time", nulls_last=True)

    if save_csv:
        out = base_dir / out_name
        df.write_csv(out)
        if verbose:
            print(f"[ok] saved {out}")

    return df





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



EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}

def find_csv_dirs(raw_root: Path) -> list[Path]:
    """Return all directories under raw_root that contain at least one .csv."""
    raw_root = raw_root.expanduser().resolve()
    dirs = set()
    for p in raw_root.rglob("*.csv"):
        try:
            rel = p.relative_to(raw_root)
        except Exception:
            continue
        # skip virtual envs / hidden libs if somehow under raw_root
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        dirs.add(p.parent)
    return sorted(dirs)



def process_one_dir_mirroring(
    raw_dir: Path,
    *,
    raw_root: Path = Path("data/raw"),
    meta_root: Path = Path("data/metadata"),
    schema_path: Path | None = Path("configs/procedures.yml"),
    overwrite: bool = True,
    make_timeline: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Parse one raw_dir and write outputs mirroring the relative path:
      data/metadata/<rel_path>/metadata.csv
      data/metadata/<rel_path>/timeline.csv
    """
    raw_dir = raw_dir.expanduser().resolve()
    raw_root = raw_root.expanduser().resolve()
    meta_root = meta_root.expanduser().resolve()
    if verbose:
        print(f"[process] {raw_dir}")

    # relative path to mirror
    rel_path = raw_dir.relative_to(raw_root)
    out_dir = (meta_root / rel_path).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # parse headers (no auto-save)
    df_meta = parse_folder_metadata(
        base_dir=raw_dir,
        schema_yaml=schema_path,
        save_csv=False,
        out_name="metadata.csv",
        only_procs=None,
        verbose=verbose,
    )
    if df_meta.height == 0:
        if verbose:
            print(f"[process] no csvs parsed in {raw_dir}")
        return {"raw_dir": str(raw_dir), "written": False, "rows": 0, "rel_path": str(rel_path)}

    # write metadata.csv
    meta_out = out_dir / "metadata.csv"
    if meta_out.exists() and not overwrite:
        if verbose: print(f"[keep] {meta_out}")
    else:
        df_meta.write_csv(meta_out)
        if verbose: print(f"[ok] wrote {meta_out} rows={df_meta.height}")

    # write timeline.csv using your printer
    tl_out = out_dir / "timeline.csv"
    if make_timeline:
        try:
            print_day_timeline(str(meta_out), raw_dir, save_csv=True)
            generated = meta_out.with_name(meta_out.stem + "_timeline.csv")
            if generated.exists():
                if tl_out.exists() and overwrite:
                    tl_out.unlink()
                generated.replace(tl_out)
                if verbose: print(f"[ok] wrote {tl_out}")
        except Exception as e:
            if verbose: print(f"[warn] timeline generation failed for {raw_dir}: {e}")

    return {
        "raw_dir": str(raw_dir),
        "rel_path": str(rel_path),
        "metadata_csv": str(meta_out),
        "timeline_csv": str(tl_out) if tl_out.exists() else "",
        "rows": df_meta.height,
        "written": True,
    }




def process_all_raw_recursive(
    raw_root: str | Path = "data/raw",
    *,
    meta_root: str | Path = "data/metadata",
    schema: str | Path = "configs/procedures.yml",
    overwrite: bool = True,
    make_timeline: bool = True,
    verbose: bool = True,
) -> pl.DataFrame:
    """
    Walk the entire raw_root recursively and mirror outputs in meta_root.
    """
    raw_root = Path(raw_root).expanduser().resolve()
    meta_root = Path(meta_root).expanduser().resolve()
    schema_path = Path(schema).expanduser().resolve() if schema else None

    csv_dirs = find_csv_dirs(raw_root)
    if verbose:
        print(f"[discover] raw_root={raw_root} dirs_with_csv={len(csv_dirs)}")

    records = []
    for d in csv_dirs:
        info = process_one_dir_mirroring(
            d, raw_root=raw_root, meta_root=meta_root,
            schema_path=schema_path, overwrite=overwrite,
            make_timeline=make_timeline, verbose=verbose
        )
        if info.get("written"):
            records.append(info)

    return pl.DataFrame(records) if records else pl.DataFrame()