# file: src/build_metadata_tree.py
#!/usr/bin/env python3
"""
Mirror-parse raw CSV headers into per-folder metadata.csv files.

Usage:
  python src/build_metadata_tree.py --raw raw_data --out metadata
"""

from __future__ import annotations

from pathlib import Path
import argparse
import re
import sys
from typing import Dict, List

import polars as pl

# ── Parsing helpers (why: robust numeric extraction from header values) ──
NUMERIC_FULL = re.compile(
    r"""^
       [-+]?               # sign
       \d*\.?\d+           # number
       (?:[eE][-+]?\d+)?   # sci
       (?:\s*[A-Za-z%μμΩ°]+)?  # unit
       $""",
    re.VERBOSE,
)
NUMERIC_PART = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

def parse_iv_metadata(csv_path: Path) -> Dict[str, object]:
    """
    Read only the '#Parameters' header block of a .csv and return a flat dict.
    WHY: we want fast, uniform metadata without loading big arrays.
    """
    params: Dict[str, object] = {}
    with csv_path.open(encoding="utf-8", errors="ignore") as f:
        in_params = False
        for line in f:
            if line.startswith("#Parameters:"):
                in_params = True
                continue
            if not in_params:
                # stop early when we reach non-header content
                if not line.startswith("#"):
                    break
                continue
            if not line.startswith("#\t"):
                break

            # "#\tKey: value"
            try:
                key, raw_val = line[2:].split(":", 1)
            except ValueError:
                # malformed header line: skip
                continue
            key = key.strip()
            raw_val = raw_val.strip()

            if NUMERIC_FULL.match(raw_val):
                num_str = NUMERIC_PART.search(raw_val).group()
                try:
                    params[key] = float(num_str)
                except ValueError:
                    params[key] = raw_val  # fallback
            elif raw_val.lower() in ("true", "false"):
                params[key] = (raw_val.lower() == "true")
            else:
                params[key] = raw_val

    # Derive optional fields
    lv = params.get("Laser voltage")
    if isinstance(lv, (int, float)):
        params["Laser toggle"] = (lv != 0.0)

    params["source_file"] = str(csv_path)
    return params

# ── Core build ──
def find_csvs_in_directory(dir_path: Path) -> List[Path]:
    """
    Return CSV files directly under dir_path (no recursion), excluding '._*'.
    """
    return [
        p for p in dir_path.glob("*.csv")
        if not p.name.startswith("._") and p.is_file()
    ]

def write_metadata_csv(records: List[Dict[str, object]], out_csv: Path) -> None:
    """
    Write records to out_csv using Polars. Ensures parent dirs exist.
    """
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(records)
    # WHY: polars writes faster and keeps types; csv for portability
    df.write_csv(out_csv)

def build_metadata_tree(raw_root: Path, out_root: Path) -> int:
    """
    Walk raw_root; for each directory that has CSVs directly in it,
    parse and write out_root/<relative>/metadata.csv.
    Returns count of metadata files written.
    """
    written = 0
    # Include raw_root itself
    for dir_path in [raw_root, *[p for p in raw_root.rglob("*") if p.is_dir()]]:
        csvs = find_csvs_in_directory(dir_path)
        if not csvs:
            continue

        records: List[Dict[str, object]] = []
        for p in csvs:
            try:
                rec = parse_iv_metadata(p)
                records.append(rec)
            except Exception as e:
                print(f"warning: could not parse {p}: {e}", file=sys.stderr)

        if not records:
            continue

        rel = dir_path.relative_to(raw_root)  # '' for root
        out_dir = out_root / rel
        out_csv = out_dir / "metadata.csv"
        write_metadata_csv(records, out_csv)
        written += 1
        print(f"[ok] wrote {out_csv} ({len(records)} rows)")

    return written

# ── CLI ──
def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Mirror raw_data/ tree into metadata/ with per-folder metadata.csv files.")
    ap.add_argument("--raw", type=Path, default=Path("raw_data"), help="Root of raw CSV tree (default: raw_data)")
    ap.add_argument("--out", type=Path, default=Path("metadata"), help="Root of output mirror tree (default: metadata)")
    return ap.parse_args(argv)

def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    raw_root: Path = args.raw
    out_root: Path = args.out

    if not raw_root.exists() or not raw_root.is_dir():
        print(f"error: raw root not found: {raw_root}", file=sys.stderr)
        return 2

    count = build_metadata_tree(raw_root, out_root)
    if count == 0:
        print("warning: no metadata files written (no CSVs found?)", file=sys.stderr)
        return 1

    print(f"|DONE| wrote {count} metadata.csv file(s) under {out_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
