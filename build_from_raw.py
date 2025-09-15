

# src/warehouse/build_raw.py
from __future__ import annotations
from pathlib import Path
import hashlib, re, datetime as dt
from typing import Any, Dict, Iterable, Optional
import polars as pl







def _read_numeric_table(csv_path, header_lines: int) -> pl.DataFrame:
    # Fast path (covers 95% cases): comments + ragged trimming
    try:
        return pl.read_csv(
            csv_path,
            comment_prefix="#",
            has_header=True,
            infer_schema_length=10_000,   # usually enough; lower than 100k is faster
            try_parse_dates=True,
            low_memory=True,              # better for many medium/small files
            truncate_ragged_lines=True,
        )
    except Exception:
        # Fallback 1: explicit skip_rows
        try:
            return pl.read_csv(
                csv_path,
                skip_rows=header_lines,
                has_header=True,
                infer_schema_length=10_000,
                try_parse_dates=True,
                low_memory=True,
                truncate_ragged_lines=True,
            )
        except Exception:
            # Fallback 2: disable quoting (handles mismatched quotes)
            try:
                return pl.read_csv(
                    csv_path,
                    skip_rows=header_lines,
                    has_header=True,
                    infer_schema_length=10_000,
                    try_parse_dates=True,
                    low_memory=True,
                    truncate_ragged_lines=True,
                    quote_char=None,
                )
            except Exception:
                # Fallback 3: lossy decoding + ignore malformed rows
                return pl.read_csv(
                    csv_path,
                    skip_rows=header_lines,
                    has_header=True,
                    infer_schema_length=5_000,   # smaller since we’re ignoring errors anyway
                    try_parse_dates=False,       # skip date inference here to avoid surprises
                    low_memory=True,
                    truncate_ragged_lines=True,
                    ignore_errors=True,
                    encoding="utf8-lossy",
                    quote_char=None,
                )



# ---- main: build Parquet directly from raw CSVs ----
def build_parquet_from_raw(
    raw_root: str | Path = "data/00_raw",
    out_root: str | Path = "data/02_warehouse",
    *,
    overwrite: bool = True,
    verbose: bool = True,
    write_experiments_index: bool = True,
) -> dict:
    """
    For every *.csv under raw_root:
      - parse the header to metadata
      - read the numeric table (skipping header) lazily
      - attach metadata as extra columns
      - write Parquet partition:
          <out_root>/raw_measurements/day_id=YYYY-MM-DD/proc=<PROC>/computer=<REL_TOP>/part-<hash>.parquet

    Also writes experiments_index.parquet (1 row per file) if enabled.
    """
    raw_root = Path(raw_root).expanduser().resolve()
    out_root = Path(out_root).expanduser().resolve()
    out_data = out_root / "raw_measurements"
    out_data.mkdir(parents=True, exist_ok=True)

    csv_files: list[Path] = [p for p in raw_root.rglob("*.csv") if not any(q in EXCLUDE_DIRS for q in p.parts)]
    if verbose:
        print(f"[raw->parquet] scanning {raw_root} ... found csv={len(csv_files)}")

    index_rows: list[dict] = []
    written = 0

    for csv_path in sorted(csv_files):
        try:
            parsed = parse_header_only(csv_path)
        except Exception as e:
            if verbose: print(f"[skip parse] {csv_path}: {e}")
            continue

        meta = parsed["meta"]
        header_lines = parsed["header_lines"]

        # infer extra context
        rel = csv_path.relative_to(raw_root)
        computer = rel.parts[0] if len(rel.parts) > 0 else "unknown"  # e.g., LabComputer1
        day_id = _day_id_from(meta, csv_path)
        proc = meta.get("proc") or "unknown"
        file_hash = _hash_path(csv_path)

        # read numeric data:
        # Prefer comment-prefix approach (Polars ignores lines starting with '#')
        # Fallback to skip_rows if comment_prefix isn't available in your Polars.
        df_data = _read_numeric_table(csv_path, header_lines)
            

        # attach metadata to each row (lightweight columns)
        # Convert datetime to ISO first, cast after union if needed
        meta_cols = {}
        for k, v in meta.items():
            if isinstance(v, dt.datetime):
                meta_cols[k] = v.isoformat()
            else:
                meta_cols[k] = v

        df = df_data.with_columns(
            *[pl.lit(val).alias(k) for k, val in meta_cols.items()],
            pl.lit(str(rel)).alias("rel_path"),
            pl.lit(computer).alias("computer"),
            pl.lit(day_id).alias("day_id"),
            pl.lit(csv_path.name).alias("file_name"),
            pl.lit(file_hash).alias("experiment_id"),
        )

        df = _to_parquet_types(df)

        # partitioned output path
        part_dir = out_data / f"day_id={day_id}" / f"proc={proc}" / f"computer={computer}"
        part_dir.mkdir(parents=True, exist_ok=True)
        part_file = part_dir / f"part-{file_hash}.parquet"

        if part_file.exists() and not overwrite:
            if verbose: print(f"[keep] {part_file}")
        else:
            df.write_parquet(part_file, compression="zstd", statistics=True)
            if verbose: print(f"[ok] {part_file} rows={df.height}")
            written += 1

        # index row (one per csv)
        if write_experiments_index:
            index_rows.append({
                "experiment_id": file_hash,
                "proc": proc,
                "day_id": day_id,
                "computer": computer,
                "rows": df_data.height,
                "source": str(rel),
                "start_time": meta.get("start_time"),
                "start_dt": meta.get("start_dt").isoformat() if isinstance(meta.get("start_dt"), dt.datetime) else None,
                "chip_number": meta.get("Chip number"),
                "vg": meta.get("VG"),
                "vds": meta.get("VDS"),
                "laser_voltage": meta.get("Laser voltage"),
                "laser_wavelength": meta.get("Laser wavelength"),
            })

    # write index
    idx_path = None
    if write_experiments_index:
        if index_rows:
            idx = pl.from_dicts(index_rows, infer_schema_length=10000)
            if "start_dt" in idx.columns and idx["start_dt"].dtype != pl.Datetime:
                idx = idx.with_columns(pl.col("start_dt").cast(pl.Utf8, strict=False).str.to_datetime(strict=False))
            idx = idx.sort(["day_id", "proc"])
            idx_path = out_root / "experiments_index.parquet"
            idx.write_parquet(idx_path, compression="zstd", statistics=True)
            if verbose: print(f"[ok] wrote {idx_path} rows={idx.height}")
        else:
            if verbose: print("[warn] no index rows")

    return {
        "written_parts": written,
        "dataset_path": str(out_data),
        "index_path": str(idx_path) if idx_path else None,
    }















