import polars as pl
from pathlib import Path
import re, datetime as dt
from typing import Iterable
from src.parsing.header_parser import _load_schema, parse_header


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
