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
def preview_collisions(csv_path: str | Path):
    df = pl.read_csv(csv_path, n_rows=0)  # read header only
    mapping = {}
    for c in df.columns:
        sc = _snake(c)
        mapping.setdefault(sc, []).append(c)
    collisions = {k:v for k,v in mapping.items() if len(v) > 1}
    print("columns:", df.columns)
    print("collisions:", collisions)


def _normalize_columns(df: pl.DataFrame) -> pl.DataFrame:
    # 1) Drop redundant header copy of start time
    cols = set(df.columns)
    if "Start time" in cols and (("start_time" in cols) or ("start_dt" in cols)):
        df = df.drop("Start time")

    # 2) Rename to snake_case with collision handling
    rename = {}
    seen = set()
    for c in df.columns:
        # canonical snake
        tgt = _snake(c)
        # special-case: if someone ships "Start time" and we didn't drop it
        if c.strip().lower() == "start time":
            tgt = "start_dt" if "start_dt" not in seen else "start_time"

        # avoid duplicates by suffixing _2, _3, ...
        base = tgt
        k = 2
        while tgt in seen:
            tgt = f"{base}_{k}"
            k += 1
        seen.add(tgt)
        rename[c] = tgt

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
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}


def iter_metadata_csv(meta_root: Path):
    meta_root = meta_root.expanduser().resolve()
    for meta_csv in meta_root.rglob("metadata.csv"):
        # skip hidden/venv
        if any(p in EXCLUDE_DIRS for p in meta_csv.relative_to(meta_root).parts):
            continue
        yield meta_csv

def build_warehouse(
    meta_root: str | Path = "data/metadata",
    out_root: str | Path = "warehouse",
    overwrite: bool = True,
    verbose: bool = True,
) -> dict:
    meta_root = Path(meta_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    exp_root = out_root / "experiments"
    exp_root.mkdir(parents=True, exist_ok=True)

    rows_total = 0
    written = 0

    for meta_csv in iter_metadata_csv(meta_root):
        rel_path = meta_csv.parent.relative_to(meta_root)  # mirror below experiments/
        try:
            df = pl.read_csv(meta_csv)
        except Exception as e:
            if verbose: print(f"[warn] read fail {meta_csv}: {e}")
            continue

        # normalize + dtypes
        df = _normalize_columns(df)
        df = _ensure_dtypes(df)
        # add structure context
        df = df.with_columns(
            pl.lit(str(rel_path)).alias("rel_path"),
            pl.lit(meta_csv.parent.name).alias("leaf_name"),
        )

        out_dir = (exp_root / rel_path).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-0.parquet"
        if out_file.exists() and not overwrite:
            if verbose: print(f"[keep] {out_file}")
        else:
            df.write_parquet(out_file)
            if verbose: print(f"[ok] wrote {out_file} rows={df.height}")

        rows_total += df.height
        written += 1

    # optional index of partitions
    idx_path = out_root / "index.parquet"
    if written > 0:
        # simple index listing rel paths
        idx = pl.DataFrame({"rel_path": [str(p.parent.relative_to(meta_root)) for p in iter_metadata_csv(meta_root)]}).unique()
        idx.write_parquet(idx_path)
        if verbose: print(f"[ok] wrote {idx_path} parts={written}")
    else:
        idx_path = None
        if verbose: print("[warn] nothing written")

    return {"parts": written, "rows": rows_total, "experiments_path": str(exp_root), "index_path": str(idx_path) if idx_path else None}

def build_timeline_dataset(
    meta_root="data/metadata", out_root="warehouse", overwrite=True, verbose=True
):
    meta_root = Path(meta_root).resolve()
    out_root = Path(out_root).resolve()
    tl_root = out_root / "timelines"
    tl_root.mkdir(parents=True, exist_ok=True)

    parts = 0
    for tl_csv in meta_root.rglob("timeline.csv"):
        rel_path = tl_csv.parent.relative_to(meta_root)
        try:
            df = pl.read_csv(tl_csv)
        except Exception as e:
            if verbose: print(f"[warn] read fail {tl_csv}: {e}")
            continue
        # normalize cols and add context
        df = df.rename({c: c.lower().replace(" ", "_") for c in df.columns})
        df = df.with_columns(
            pl.lit(str(rel_path)).alias("rel_path"),
            pl.lit(tl_csv.parent.name).alias("leaf_name"),
        )
        out_dir = (tl_root / rel_path).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "part-0.parquet"
        if out_file.exists() and not overwrite:
            if verbose: print(f"[keep] {out_file}")
        else:
            df.write_parquet(out_file)
            parts += 1
            if verbose: print(f"[ok] wrote {out_file} rows={df.height}")

    if verbose:
        print(f"[done] timeline parts={parts}")