# src/warehouse/builder.py
from __future__ import annotations
from pathlib import Path
import datetime as dt
import re
import polars as pl

# ---------- helpers ----------
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}

def _snake(s: str) -> str:
    s = s.strip().replace("/", "_").replace("\\", "_")
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()

def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    # 1) Drop redundant header copy of start time if parser already emitted start_time/start_dt
    cols = set(df.columns)
    if "Start time" in cols and (("start_time" in cols) or ("start_dt" in cols)):
        df = df.drop("Start time")

    # 2) snake_case with collision handling
    rename: dict[str, str] = {}
    seen: set[str] = set()
    for c in df.columns:
        tgt = _snake(c)
        # if someone left a mixed "Start time", prefer start_dt (otherwise start_time)
        if c.strip().lower() == "start time":
            tgt = "start_dt" if "start_dt" not in seen else "start_time"
        base = tgt
        k = 2
        while tgt in seen:
            tgt = f"{base}_{k}"
            k += 1
        seen.add(tgt)
        rename[c] = tgt
    return df.rename(rename)

def _ensure_dtypes(df: pl.DataFrame) -> pl.DataFrame:
    cols = df.columns
    if "start_time" in cols:
        df = df.with_columns(pl.col("start_time").cast(pl.Float64, strict=False))
    if "start_dt" in cols and df["start_dt"].dtype != pl.Datetime:
        df = df.with_columns(
            pl.col("start_dt").cast(pl.Utf8, strict=False).str.to_datetime(strict=False)
        )
    # common numeric suspects
    likely_nums = [
        c for c in cols
        if c.endswith(("_v", "_a", "_degc", "_ms", "_step", "_start", "_end"))
        or c in {"vg", "vds", "vl", "laser_wavelength", "chip_number", "file_idx"}
    ]
    for c in likely_nums:
        if c in df.columns:
            df = df.with_columns(pl.col(c).cast(pl.Float64, strict=False))
    if "chip_number" in df.columns:
        df = df.with_columns(pl.col("chip_number").cast(pl.Int64, strict=False))
    return df

def _iter_metadata_csv(meta_root: Path):
    meta_root = meta_root.expanduser().resolve()
    for meta_csv in meta_root.rglob("metadata.csv"):
        rel_parts = meta_csv.relative_to(meta_root).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        yield meta_csv

# ---------- public API ----------
def build_warehouse(
    meta_root: str | Path = "data/metadata",
    out_root: str | Path = "warehouse",
    overwrite: bool = True,
    verbose: bool = True,
    pin_schema: bool = False,
) -> dict:
    """
    Read all data/metadata/**/metadata.csv and write partitioned Parquet:
      warehouse/experiments/<rel_path>/part-0.parquet
    Also writes a rich warehouse/index.parquet.
    """
    meta_root = Path(meta_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    exp_root = out_root / "experiments"
    exp_root.mkdir(parents=True, exist_ok=True)

    rows_total = 0
    parts_info: list[dict] = []

    # Optional "public schema" to keep analytics stable (toggle with pin_schema)
    KEEP = {
        "proc": pl.Utf8,
        "start_time": pl.Float64,
        "start_dt": pl.Datetime,
        "chip_number": pl.Int64,
        "vg": pl.Float64,
        "vds": pl.Float64,
        "vg_start": pl.Float64,
        "vg_end": pl.Float64,
        "vg_step": pl.Float64,
        "file_idx": pl.Int64,
        "source_file": pl.Utf8,
        # context fields we add:
        "rel_path": pl.Utf8,
        "leaf_name": pl.Utf8,
        "day_id": pl.Utf8,
    }

    for meta_csv in _iter_metadata_csv(meta_root):
        rel_path = meta_csv.parent.relative_to(meta_root)
        leaf_name = meta_csv.parent.name
        day_id = leaf_name  # mirrors folder exactly

        try:
            df = pl.read_csv(meta_csv)
        except Exception as e:
            if verbose:
                print(f"[warn] read fail {meta_csv}: {e}")
            continue

        df = _normalize_columns(df)
        df = _ensure_dtypes(df)

        # add context columns
        df = df.with_columns(
            pl.lit(str(rel_path)).alias("rel_path"),
            pl.lit(leaf_name).alias("leaf_name"),
            pl.lit(day_id).alias("day_id"),
        )

        # schema pinning (prevents scan_parquet schema drift surprises)
        if pin_schema:
            present = [c for c in KEEP if c in df.columns]
            if present:
                df = df.select([pl.col(c).cast(KEEP[c], strict=False) for c in present])

        # write partition file
        out_dir = (exp_root / rel_path).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-0.parquet"
        if out_file.exists() and not overwrite:
            if verbose:
                print(f"[keep] {out_file}")
        else:
            df.write_parquet(out_file, compression="zstd", statistics=True)
            if verbose:
                print(f"[ok] wrote {out_file} rows={df.height}")

        rows_total += df.height
        parts_info.append({
            "rel_path": str(rel_path),
            "leaf_name": leaf_name,
            "day_id": day_id,
            "rows": df.height,
            "last_modified": dt.datetime.utcfromtimestamp(out_file.stat().st_mtime),
        })

    # write index
    idx_path = out_root / "index.parquet"
    if parts_info:
        idx = pl.DataFrame(parts_info).unique().sort(["day_id", "rel_path"])
        idx.write_parquet(idx_path, compression="zstd", statistics=True)
        if verbose:
            print(f"[ok] wrote {idx_path} parts={idx.height}")
    else:
        idx_path = None
        if verbose:
            print("[warn] nothing written")

    return {
        "parts": len(parts_info),
        "rows": rows_total,
        "experiments_path": str(exp_root),
        "index_path": str(idx_path) if idx_path else None,
    }

def build_timeline_dataset(
    meta_root: str | Path = "data/metadata",
    out_root: str | Path = "warehouse",
    overwrite: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Read all data/metadata/**/timeline.csv and write partitioned Parquet:
      warehouse/timelines/<rel_path>/part-0.parquet
    """
    meta_root = Path(meta_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    tl_root = out_root / "timelines"
    tl_root.mkdir(parents=True, exist_ok=True)

    parts = 0
    for tl_csv in meta_root.rglob("timeline.csv"):
        rel_path = tl_csv.parent.relative_to(meta_root)
        leaf_name = tl_csv.parent.name
        try:
            df = pl.read_csv(tl_csv)
        except Exception as e:
            if verbose:
                print(f"[warn] read fail {tl_csv}: {e}")
            continue

        # normalize cols + add context
        df = df.rename({c: c.lower().replace(" ", "_") for c in df.columns})
        df = df.with_columns(
            pl.lit(str(rel_path)).alias("rel_path"),
            pl.lit(leaf_name).alias("leaf_name"),
            pl.lit(leaf_name).alias("day_id"),
        )

        out_dir = (tl_root / rel_path).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-0.parquet"
        if out_file.exists() and not overwrite:
            if verbose:
                print(f"[keep] {out_file}")
        else:
            df.write_parquet(out_file, compression="zstd", statistics=True)
            parts += 1
            if verbose:
                print(f"[ok] wrote {out_file} rows={df.height}")

    if verbose:
        print(f"[done] timeline parts={parts}")
    return {"parts": parts, "timelines_path": str(tl_root)}
