from __future__ import annotations
from pathlib import Path
import polars as pl
from src.parsing.folder_parser import parse_folder_metadata
try:
    from src.ploting.plots import print_day_timeline
except Exception:
    def print_day_timeline(*args, **kwargs):
        return pl.DataFrame()




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