# src/warehouse/builder_parallel.py
from __future__ import annotations
from pathlib import Path
import os, datetime as dt, hashlib, re, threading
import concurrent.futures as cf
import polars as pl

from src.warehouse.db_schema import build_schema_overrides_from_yaml

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}

# ---------- small utils ----------
def _hash_path(p: Path) -> str:
    return hashlib.sha1(str(p).encode("utf-8")).hexdigest()[:16]

_PROC_LINE  = re.compile(r"^\s*#\s*Procedure\s*:\s*<([^>]+)>\s*$", re.I)
_START_TIME = re.compile(r"^\s*#\s*Start\s*time\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.I)

def _infer_proc_from_name(name: str) -> str | None:
    n = name.lower()
    if "ivgt" in n: return "IVgT"
    if re.search(r"(^|[^a-z])ivg([^a-z]|$)", n): return "IVg"
    if re.search(r"(^|[^a-z])it([^a-z]|$)", n):  return "It"
    if re.search(r"(^|[^a-z])iv([^a-z]|$)", n):  return "IV"
    if "lasercalibration" in n: return "LaserCalibration"
    if "itt" in n: return "ITt"
    return None

def parse_header_only(csv_path: Path) -> dict:
    start_time = None
    proc_full = None
    header_lines = 0
    saw_data = False
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            header_lines += 1
            if line.lstrip().startswith("#Data"):
                saw_data = True
                break
            m = _PROC_LINE.match(line)
            if m: proc_full = m.group(1).strip()
            m2 = _START_TIME.match(line)
            if m2: start_time = float(m2.group(1))
    if saw_data:
        header_lines += 1  # include the data header row

    proc_short = proc_full.split(".")[-1] if proc_full else None
    if not proc_short:
        proc_short = _infer_proc_from_name(csv_path.name) or "unknown"

    if start_time is not None:
        try: start_dt = dt.datetime.fromtimestamp(float(start_time))
        except Exception: start_dt = None
    else:
        try:
            start_time = csv_path.stat().st_mtime
            start_dt = dt.datetime.fromtimestamp(start_time)
        except Exception:
            start_time, start_dt = None, None

    return {
        "meta": {
            "procedure_full": proc_full,
            "proc": proc_short,
            "start_time": start_time,
            "start_dt": start_dt
        },
        "header_lines": header_lines,
    }

def _day_id_from(meta: dict, csv_path: Path) -> str:
    sd = meta.get("start_dt")
    if isinstance(sd, dt.datetime):
        return sd.date().isoformat()
    st = meta.get("start_time")
    try:
        if st is not None:
            return dt.datetime.fromtimestamp(float(st)).date().isoformat()
    except Exception:
        pass
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", str(csv_path))
    if m: return m.group(1)
    try:
        return dt.datetime.fromtimestamp(csv_path.stat().st_mtime).date().isoformat()
    except Exception:
        return "unknown"

# ---------- schema cache from YAML (thread-safe) ----------
_SCHEMAS_LOCK = threading.Lock()
_SCHEMAS_CACHE: dict[str, dict[str, pl.DataType]] | None = None

def _get_proc_schema(proc: str, procedures_yaml: Path | None) -> dict[str, pl.DataType] | None:
    """Load YAML once; return {col_name: dtype} for this procedure, or None."""
    global _SCHEMAS_CACHE
    if not procedures_yaml:
        return None
    if _SCHEMAS_CACHE is None:
        with _SCHEMAS_LOCK:
            if _SCHEMAS_CACHE is None:
                _SCHEMAS_CACHE = build_schema_overrides_from_yaml(procedures_yaml)
    return _SCHEMAS_CACHE.get(proc)

# ---------- streaming sink with robust fallbacks ----------
def _sink_stream(
    csv_path: Path,
    header_lines: int,
    out_path: Path,
    meta_cols: dict,
    proc: str,
    procedures_yaml: Path | None,
):
    schema_overrides = _get_proc_schema(proc, procedures_yaml)

    def try_sink(**kwargs):
        ldf = (
            pl.scan_csv(
                csv_path,
                has_header=True,
                schema_overrides=schema_overrides,           # <-- pinned schema per proc
                **kwargs
            )
            .with_columns(*[pl.lit(v).alias(k) for k, v in meta_cols.items()])
        )
        ldf.sink_parquet(str(out_path), compression="zstd", statistics=True)

    # Fast path: comment-prefix
    infer_len = 0 if schema_overrides else 10_000
    try:
        try_sink(
            comment_prefix="#",
            infer_schema_length=infer_len,
            try_parse_dates=not bool(schema_overrides),    # no need when schema pinned
            low_memory=True,
            truncate_ragged_lines=True,
        )
        return
    except Exception:
        pass

    # Fallback: skip_rows
    try:
        try_sink(
            skip_rows=header_lines,
            infer_schema_length=infer_len,
            try_parse_dates=not bool(schema_overrides),
            low_memory=True,
            truncate_ragged_lines=True,
        )
        return
    except Exception:
        pass

    # Fallback: disable quotes
    try:
        try_sink(
            skip_rows=header_lines,
            infer_schema_length=infer_len,
            try_parse_dates=not bool(schema_overrides),
            low_memory=True,
            truncate_ragged_lines=True,
            quote_char=None,
        )
        return
    except Exception:
        pass

    # Last resort: lossy + ignore_errors
    try_sink(
        skip_rows=header_lines,
        infer_schema_length=infer_len if infer_len else 5_000,
        try_parse_dates=False,
        low_memory=True,
        truncate_ragged_lines=True,
        quote_char=None,
        ignore_errors=True,
        encoding="utf8-lossy",
    )

# ---------- single-file worker ----------
def _process_one(
    csv_path: Path,
    raw_root: Path,
    out_data: Path,
    overwrite: bool,
    verbose: bool,
    procedures_yaml: Path | None,
) -> dict | None:
    try:
        parsed = parse_header_only(csv_path)
    except Exception as e:
        if verbose: print(f"[skip parse] {csv_path}: {e}")
        return None

    meta = parsed["meta"]
    header_lines = parsed["header_lines"]

    rel = csv_path.relative_to(raw_root)
    computer = rel.parts[0] if len(rel.parts) > 0 else "unknown"
    day_id = _day_id_from(meta, csv_path)
    proc = (meta.get("proc") or "unknown").replace("/", "_")
    file_hash = _hash_path(csv_path)

    # convert dt to ISO (keeps parquet schema simple/consistent)
    meta_cols = {k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in meta.items()}
    meta_cols |= {
        "rel_path": str(rel),
        "computer": computer,
        "day_id": day_id,
        "file_name": csv_path.name,
        "experiment_id": file_hash,
    }

    part_dir = out_data / f"day_id={day_id}" / f"proc={proc}" / f"computer={computer}"
    part_dir.mkdir(parents=True, exist_ok=True)
    part_file = part_dir / f"part-{file_hash}.parquet"

    if part_file.exists() and not overwrite:
        return {"status": "kept", "experiment_id": file_hash, "proc": proc, "day_id": day_id,
                "computer": computer, "source": str(rel)}

    try:
        _sink_stream(csv_path, header_lines, part_file, meta_cols, proc, procedures_yaml)
    except Exception as e:
        if verbose: print(f"[fail] {csv_path} → {part_file}: {e}")
        return None

    return {"status": "ok", "experiment_id": file_hash, "proc": proc, "day_id": day_id,
            "computer": computer, "source": str(rel)}

# ---------- public parallel builder ----------
def build_parquet_from_raw_parallel(
    raw_root: str | Path,
    out_root: str | Path,
    *,
    procedures_yaml: str | Path | None = "config/procedures.yml",
    overwrite: bool = True,
    verbose: bool = True,
    write_experiments_index: bool = True,
    max_workers: int | None = None,
    log_every: int = 200,
) -> dict:
    raw_root = Path(raw_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    out_data = out_root / "raw_measurements"
    out_data.mkdir(parents=True, exist_ok=True)

    # normalize yaml path (allow None to disable pinning)
    pyaml = Path(procedures_yaml).resolve() if procedures_yaml else None
    if pyaml and not pyaml.exists():
        if verbose:
            print(f"[warn] procedures.yml not found at {pyaml}; running without schema pinning")
        pyaml = None

    csv_files = [p for p in raw_root.rglob("*.csv") if not any(part in EXCLUDE_DIRS for part in p.parts)]
    if verbose:
        print(f"[raw->parquet] scan {raw_root} … csv={len(csv_files)}")

    if max_workers is None:
        max_workers = min(8, (os.cpu_count() or 4))  # be gentle to disk

    results = []
    written = 0

    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [
            ex.submit(_process_one, p, raw_root, out_data, overwrite, verbose, pyaml)
            for p in csv_files
        ]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            res = fut.result()
            if res:
                results.append(res)
                if res["status"] == "ok":
                    written += 1
            if verbose and (i % log_every == 0):
                print(f"  … {i}/{len(csv_files)} processed")

    # optional compact index (one row per csv)
    idx_path = None
    if write_experiments_index and results:
        idx = pl.from_dicts(results, infer_schema_length=10_000)
        idx = idx.sort(["day_id", "proc", "experiment_id"])
        idx_path = out_root / "experiments_index.parquet"
        idx.write_parquet(idx_path, compression="zstd", statistics=True)
        if verbose:
            print(f"[ok] wrote {idx_path} rows={idx.height}")

    if verbose:
        print(f"[done] written parts={written}")

    return {
        "written_parts": written,
        "dataset_path": str(out_data),
        "index_path": str(idx_path) if idx_path else None,
    }
