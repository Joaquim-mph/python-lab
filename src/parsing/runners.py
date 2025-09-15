
from __future__ import annotations
from pathlib import Path
import polars as pl
from src.parsing.folder_parser import parse_folder_metadata

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
            schema_path=schema_path, overwrite=overwrite, verbose=verbose
        )
        if info.get("written"):
            records.append(info)

    return pl.DataFrame(records) if records else pl.DataFrame()