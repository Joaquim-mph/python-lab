# file: tools/plot_iv.py
"""
Plot IV and IT traces from raw experiment CSVs using a previously-built metadata.csv
(derived from headers with `parse_iv_metadata`).

Usage examples:

  # Plot IV for a specific device
  python tools/plot_iv.py iv --metadata metadata.csv \
      --group "Chip group name" --chip 3 --legend --title "Device 3: IV sweeps"

  # Plot IT for a sample filtered by text in Information
  python tools/plot_iv.py it --metadata metadata.csv \
      --info-contains "no light" --ylog --save it_no_light.png

  # If paths in metadata are relative to a different root
  python tools/plot_iv.py iv --root /path/to/Alisson_04_sept

Notes:
- Only uses Matplotlib (no seaborn).
- One chart per command.
- No explicit colors set (matplotlib defaults).
- Heuristics try to find column names for Voltage/Current/Time/Gate Voltage.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Optional

import polars as pl
import matplotlib as mpl
import matplotlib.pyplot as plt
import scienceplots
from styles import set_plot_style
set_plot_style("super_nova")
# ----------------------------
# Column name heuristics
# ----------------------------
TIME_CANDIDATES = [
    r"^time$",
    r"^time\s*\(\s*s\s*\)$",
    r"^t$",
]

VOLT_CANDIDATES = [
    r"^v$", 
    r"^voltage$", 
    r"^vsd$", 
    r"^vds$", 
    r"^v_sd$", 
    r"^v_ds$",
]

CURR_CANDIDATES = [
    r"^i$",
    r"^current$",
    r"^id$",
    r"^isd$",
    r"^ig$",
    r"^i_d$",
    r"^i_sd$",
]

GATE_VOLT_CANDIDATES = [
    r"^vg$", r"^v_g$", r"^vgate$", r"^v_gate$",
]

# Metadata fields we may show in legend labels if present
LEGEND_META_FIELDS = [
    "Information",
    "Laser toggle",
    "Laser voltage",
    "Laser wavelength",
    "VG",
    "VDS",
]

# ----------------------------
# Helpers
# ----------------------------

def normalize(name: str) -> str:
    """Lowercase, collapse spaces/parentheses/units to underscores for matching."""
    s = name.strip().lower()
    # Replace common separators and remove surrounding spaces
    s = re.sub(r"[\s\-/]+", "_", s)
    s = s.replace("(s)", "")
    s = s.replace("(a)", "")
    s = s.replace("(v)", "")
    s = s.replace("[", "").replace("]", "")
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def find_first_column(df: pl.DataFrame, patterns: list[str]) -> Optional[str]:
    """Return the *original* column name whose normalized form matches one of patterns."""
    norm_map = {col: normalize(col) for col in df.columns}
    for pat in patterns:
        rx = re.compile(pat)
        for original, normed in norm_map.items():
            if rx.match(normed):
                return original
    return None


def detect_columns(df: pl.DataFrame, mode: str) -> tuple[Optional[str], Optional[str]]:
    """Detect x,y columns for a given mode: 'iv', 'it', or 'ivg'."""
    if mode == "iv":
        x = find_first_column(df, VOLT_CANDIDATES)
        y = find_first_column(df, CURR_CANDIDATES)
        return x, y
    elif mode == "it":
        x = find_first_column(df, TIME_CANDIDATES)
        y = find_first_column(df, CURR_CANDIDATES)
        return x, y
    elif mode == "ivg":
        x = find_first_column(df, GATE_VOLT_CANDIDATES)   # no fallback to VOLT_CANDIDATES
        y = find_first_column(df, CURR_CANDIDATES)
        return x, y
    else:
        raise ValueError("mode must be 'iv', 'it', or 'ivg'")


def count_header_rows(csv_path: Path) -> int:
    """Count leading header lines starting with '#'."""
    n = 0
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("#"):
                n += 1
            else:
                break
    return n


def read_data_block(csv_path: Path) -> pl.DataFrame:
    """Read the data portion of an IV CSV by skipping header lines that start with '#'."""
    skip = count_header_rows(csv_path)
    try:
        df = pl.read_csv(
            csv_path,
            skip_rows=skip,
            infer_schema_length=4096,
            ignore_errors=True,
            try_parse_dates=True,
            null_values=["nan", "NaN", ""],
            encoding="utf8-lossy",
        )
    except Exception as e:
        raise RuntimeError(f"read_csv failed: {e}")

    if df.height == 0 or df.width == 0:
        raise RuntimeError("empty data block")
    return df


# ----------------------------
# Metadata filtering
# ----------------------------

def load_metadata(path: Path) -> pl.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"metadata file not found: {path}")
    df = pl.read_csv(path, infer_schema_length=2048, encoding="utf8-lossy")
    if "source_file" not in df.columns:
        raise ValueError("metadata.csv must include a 'source_file' column")
    return df


def filter_metadata(
    meta: pl.DataFrame,
    *,
    sample: Optional[str] = None,
    group_field: Optional[str] = None,  # e.g. "Chip group name"
    chip: Optional[str | int] = None,   # e.g. 3
    info_contains: Optional[str] = None,
    info_regex: Optional[str] = None,
) -> pl.DataFrame:
    df = meta
    if sample and "Sample" in df.columns:
        df = df.filter(pl.col("Sample").cast(pl.Utf8, strict=False).str.contains(sample, literal=True, strict=False))

    if group_field and group_field in df.columns:
        df = df.filter(pl.col(group_field).cast(pl.Utf8, strict=False).is_not_null())

    if chip is not None and "Chip number" in df.columns:
        chip_str = str(chip)
        try:
            chip_float = float(chip_str)
        except Exception:
            chip_float = None

        cond = (pl.col("Chip number").cast(pl.Utf8, strict=False) == chip_str)
        if chip_float is not None:
            cond = cond | (pl.col("Chip number").cast(pl.Float64, strict=False) == chip_float)
        cond = cond | (
            pl.col("Chip number").cast(pl.Utf8, strict=False)
            .str.replace(r"^(\d+)\.0+$", r"\1", literal=False) == chip_str
        )
        df = df.filter(cond)

    if info_contains and "Information" in df.columns:
        df = df.filter(pl.col("Information").cast(pl.Utf8, strict=False).str.contains(info_contains, literal=False, strict=False))

    if info_regex and "Information" in df.columns:
        df = df.filter(pl.col("Information").cast(pl.Utf8, strict=False).str.contains(info_regex, literal=False))

    return df


def build_label(row: dict) -> str:
    parts: list[str] = []
    for key in LEGEND_META_FIELDS:
        if key in row and row[key] is not None and row[key] != "":
            parts.append(f"{key}={row[key]}")
    return "; ".join(parts) if parts else Path(str(row.get("source_file", ""))).name


def resolve_source_path(src: str, root: Optional[Path]) -> Path:
    p = Path(src)
    if root is not None and not p.is_absolute():
        p = root / p
    return p


# ----------------------------
# Plotters
# ----------------------------

def plot_iv(paths: list[Path], meta_rows: list[dict], *, title: Optional[str], xlog: bool, ylog: bool, legend: bool):
    plt.figure()
    for csv_path, meta_row in zip(paths, meta_rows):
        try:
            df = read_data_block(csv_path)
            x_col, y_col = detect_columns(df, mode="iv")
            if not x_col or not y_col:
                print(f"[skip] {csv_path.name}: could not detect IV columns")
                continue
            x = df.get_column(x_col).to_numpy()
            y = df.get_column(y_col).to_numpy()
            lbl = build_label(meta_row)
            plt.plot(x, y, label=lbl)
        except Exception as e:
            print(f"[warn] failed {csv_path}: {e}")
            continue

    plt.xlabel("Voltage (detected)")
    plt.ylabel("Current (detected)")
    if xlog:
        plt.xscale("log")
    if ylog:
        plt.yscale("log")
    if title:
        plt.title(title)
    if legend:
        plt.legend()
    plt.tight_layout()


def plot_it(paths: list[Path], meta_rows: list[dict], *, title: Optional[str], xlog: bool, ylog: bool, legend: bool):
    plt.figure()
    for csv_path, meta_row in zip(paths, meta_rows):
        try:
            df = read_data_block(csv_path)
            x_col, y_col = detect_columns(df, mode="it")
            if not x_col or not y_col:
                print(f"[skip] {csv_path.name}: could not detect IT columns")
                continue
            x = df.get_column(x_col).to_numpy()
            y = df.get_column(y_col).to_numpy()
            lbl = build_label(meta_row)
            plt.plot(x, y, label=lbl)
        except Exception as e:
            print(f"[warn] failed {csv_path}: {e}")
            continue

    plt.xlabel("Time (detected)")
    plt.ylabel("Current (detected)")
    if xlog:
        plt.xscale("log")
    if ylog:
        plt.yscale("log")
    if title:
        plt.title(title)
    if legend:
        plt.legend()
    plt.tight_layout()


def plot_ivg(paths: list[Path], meta_rows: list[dict], *, title: Optional[str], xlog: bool, ylog: bool, legend: bool):
    """Plot I vs VG (gate sweep) at fixed VDS."""
    plt.figure()
    for csv_path, meta_row in zip(paths, meta_rows):
        try:
            df = read_data_block(csv_path)
            x_col, y_col = detect_columns(df, mode="ivg")
            if not x_col or not y_col:
                print(f"[skip] {csv_path.name}: could not detect IVg columns")
                continue
            x = df.get_column(x_col).to_numpy()
            y = df.get_column(y_col).to_numpy()
            lbl = build_label(meta_row)
            plt.plot(x, y, label=lbl)
        except Exception as e:
            print(f"[warn] failed {csv_path}: {e}")
            continue

    plt.xlabel("Gate Voltage VG (detected)")
    plt.ylabel("Current (detected)")
    if xlog:
        plt.xscale("log")
    if ylog:
        plt.yscale("log")
    if title:
        plt.title(title)
    if legend:
        plt.legend()
    plt.tight_layout()


# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot IV/IT traces from metadata + raw CSVs")
    p.add_argument("mode", choices=["iv", "it", "ivg"], help="plot type: iv, it, or ivg")
    p.add_argument("--metadata", default="metadata.csv", type=Path, help="Path to metadata CSV")
    p.add_argument("--root", type=Path, default=None, help="Optional root to prepend to relative source_file paths")
    # Filters
    p.add_argument("--sample", type=str, default=None, help="Filter by Sample contains")
    p.add_argument("--group", dest="group_field", type=str, default=None, help="Group field to use with --chip (e.g. 'Chip group name')")
    p.add_argument("--chip", type=str, default=None, help="Chip number to match when --group is given")
    p.add_argument("--info-contains", type=str, default=None, help="Substring to search in Information")
    p.add_argument("--info-regex", type=str, default=None, help="Regex to search in Information")
    p.add_argument("--limit", type=int, default=None, help="Max number of traces")
    # Plot opts
    p.add_argument("--title", type=str, default=None)
    p.add_argument("--xlog", action="store_true")
    p.add_argument("--ylog", action="store_true")
    p.add_argument("--legend", action="store_true")
    p.add_argument("--save", type=Path, default=None, help="Save figure to path (png/pdf)")
    p.add_argument("--dpi", type=int, default=150)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    meta = load_metadata(args.metadata)

    df_sel = filter_metadata(
        meta,
        sample=args.sample,
        group_field=args.group_field,
        chip=args.chip,
        info_contains=args.info_contains,
        info_regex=args.info_regex,
    )

    if df_sel.height == 0:
        available_cols = ", ".join(meta.columns)
        raise SystemExit(
            "No rows matched filters. Try relaxing filters or check field names.\n"
            f"Available metadata columns: {available_cols}"
        )

    if args.limit is not None:
        df_sel = df_sel.head(args.limit)

    rows = df_sel.to_dicts()
    paths: list[Path] = []
    meta_rows: list[dict] = []
    for row in rows:
        src = row.get("source_file")
        if not src:
            continue
        p = resolve_source_path(str(src), args.root)
        if not p.exists():
            print(f"[skip] missing: {p}")
            continue
        paths.append(p)
        meta_rows.append(row)

    if not paths:
        raise SystemExit("No existing source files to plot after filtering.")

    if args.mode == "iv":
        plot_iv(paths, meta_rows, title=args.title, xlog=args.xlog, ylog=args.ylog, legend=args.legend)
    elif args.mode == "it":
        plot_it(paths, meta_rows, title=args.title, xlog=args.xlog, ylog=args.ylog, legend=args.legend)
    else:
        plot_ivg(paths, meta_rows, title=args.title, xlog=args.xlog, ylog=args.ylog, legend=args.legend)

    if args.save:
        plt.savefig(args.save, dpi=args.dpi, bbox_inches="tight")
        print(f"Saved figure -> {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
