from __future__ import annotations
from pathlib import Path
import re, datetime as dt
import polars as pl

# --- helpers ---
def _snake(s: str) -> str:
    s = s.strip().replace("/", "_").replace("\\", "_")
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()

def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    rename = {c: _snake(c) for c in df.columns}
    return df.rename(rename)

def _ensure_dtypes(df: pl.DataFrame) -> pl.DataFrame:
    # harden the common ones
    cols = df.columns
    if "start_time" in cols:
        df = df.with_columns(pl.col("start_time").cast(pl.Float64, strict=False))
    if "start_dt" in cols:
        # strings/objects -> Datetime
        if df["start_dt"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.col("start_dt")
                  .cast(pl.Utf8, strict=False)
                  .str.to_datetime(strict=False)
            )
    # numeric columns with accidental strings (after unit stripping in your parser they should be numeric already)
    # keep it light: attempt safe casts on a few likely numeric names if present
    likely_nums = [c for c in cols if c.endswith(("_v","_a","_degc","_ms","_step","_start","_end")) or c in {"vg","vds","vl","laser_wavelength","chip_number","file_idx"}]
    for c in likely_nums:
        if c in df.columns:
            df = df.with_columns(pl.col(c).cast(pl.Float64, strict=False))
    # chip number as Int where possible
    if "chip_number" in df.columns:
        df = df.with_columns(pl.col("chip_number").cast(pl.Int64, strict=False))
    return df

def _add_day_id(df: pl.DataFrame, day_id: str) -> pl.DataFrame:
    return df.with_columns(pl.lit(day_id).alias("day_id"))

# --- main builder ---
def build_warehouse(
    meta_root: str | Path = "data/metadata",
    out_root: str | Path = "warehouse",
    overwrite: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Scan data/metadata/*/metadata.csv, normalize/union, and write Parquet:
      warehouse/experiments/day_id=YYYY-MM-DD/part-*.parquet
      warehouse/index.parquet (one row per day)
    Returns basic info.
    """
    meta_root = Path(meta_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    exp_root = out_root / "experiments"
    exp_root.mkdir(parents=True, exist_ok=True)

    # find per-day metadata.csv files
    day_dirs = sorted([p for p in meta_root.iterdir() if p.is_dir()])
    rows_total = 0
    written_days = []

    union_frames: list[pl.DataFrame] = []
    for d in day_dirs:
        meta_csv = d / "metadata.csv"
        if not meta_csv.exists():
            if verbose: print(f"[skip] no metadata.csv in {d}")
            continue
        day_id = d.name  # mirror exactly (e.g., 2025-09-12)
        try:
            df = pl.read_csv(meta_csv)
        except Exception as e:
            if verbose: print(f"[warn] failed to read {meta_csv}: {e}")
            continue

        df = _normalize_columns(df)
        df = _ensure_dtypes(df)
        df = _add_day_id(df, day_id)

        rows_total += df.height
        written_days.append(day_id)

        # write partitioned parquet for this day
        out_dir = exp_root / f"day_id={day_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-0.parquet"
        if out_file.exists() and not overwrite:
            if verbose: print(f"[keep] {out_file}")
        else:
            df.write_parquet(out_file)
            if verbose: print(f"[ok] wrote {out_file}  rows={df.height}")

        union_frames.append(df.select("day_id").unique())

    # write index
    if union_frames:
        idx = pl.concat(union_frames).unique().sort("day_id")
        idx_path = out_root / "index.parquet"
        idx.write_parquet(idx_path)
        if verbose: print(f"[ok] wrote {idx_path}  days={idx.height}")
    else:
        idx_path = None
        if verbose: print("[warn] nothing written")

    return {
        "days": written_days,
        "rows": rows_total,
        "experiments_path": str(exp_root),
        "index_path": str(idx_path) if idx_path else None,
    }



# lazy scan across all partitions
lf = pl.scan_parquet("warehouse/experiments/day_id=*/part-*.parquet")

# peek schema/columns
print(lf.columns)

# examples:

# A) counts per procedure
q1 = (
    lf.group_by("proc")
      .agg(pl.len().alias("n"))
      .sort("n", descending=True)
)
q1.collect()

# B) experiments per day and proc
q2 = (
    lf.group_by(["day_id", "proc"])
      .agg(pl.len().alias("n"))
      .sort(["day_id", "proc"])
)
q2.collect()

# C) filter and select a few fields (e.g., IVg with VDS and VG sweep)
q3 = (
    lf.filter(pl.col("proc") == "IVg")
      .select("day_id", "source_file", "start_dt", "chip_number", "vds", "vg_start", "vg_end", "vg_step")
      .sort("start_dt")
)
q3.collect()

# D) time-window query (e.g., September 12 only)
q4 = (
    lf.filter(pl.col("day_id") == "2025-09-12")
      .filter(pl.col("proc").is_in(["IVg", "It"]))
      .select("start_dt","proc","chip_number","vds","vg","vl","laser_wavelength","source_file")
      .sort("start_dt")
)
q4.collect()

# E) convert lazy → eager for quick plots or further ops
df_ivg = q3.collect()