from pathlib import Path
import re, math, datetime as dt
import polars as pl

# ---------- tiny header parsers ----------
_start_pat = re.compile(r"^\s*#\s*Start time:\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.I)
_proc_pat  = re.compile(r"^\s*#\s*Procedure:\s*<([^>]+)>\s*$", re.I)

def _read_header_info(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            start_time = None
            procedure  = None
            for line in f:
                if line.lstrip().startswith("#Data"):
                    break
                if start_time is None:
                    m = _start_pat.match(line)
                    if m:
                        start_time = float(m.group(1))
                if procedure is None:
                    m2 = _proc_pat.match(line)
                    if m2:
                        procedure = m2.group(1)
            return {"start_time": start_time, "procedure": procedure}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def _proc_short(proc_str: str | None) -> str:
    if not proc_str:
        return "?"
    p = proc_str.split(".")
    return p[-1] if p else proc_str

def build_day_timeline(meta_csv: str, base_dir: Path) -> pl.DataFrame:
    # load the day metadata as-is (no chip filter)
    meta = pl.read_csv(meta_csv, ignore_errors=True)

    # Ensure columns we’ll reference exist
    for c in ["source_file","Chip number","VG","VDS","Laser voltage",
              "Laser wavelength","Laser ON+OFF period","Information",
              "VSD start","VSD end","VSD step","VG start","VG end","VG step"]:
        if c not in meta.columns:
            meta = meta.with_columns(pl.lit(None).alias(c))

    file_idx_re = re.compile(r"_([0-9]+)\.csv$", re.I)

    rows = []
    for row in meta.iter_rows(named=True):
        src = row.get("source_file")
        if not src or (isinstance(src, float) and math.isnan(src)):
            continue
        path = base_dir / str(src)
        head = _read_header_info(path)
        start_time = head.get("start_time")
        proc_full  = head.get("procedure")

        if start_time is None:
            try:
                start_time = path.stat().st_mtime  # fallback
            except Exception:
                start_time = None

        start_dt = dt.datetime.fromtimestamp(start_time) if start_time else None
        time_hms = start_dt.strftime("%H:%M:%S") if start_dt else "?"

        proc_short = _proc_short(proc_full)
        if proc_short == "?" and isinstance(src, str):
            if "IVg" in src: proc_short = "IVg"
            elif "It" in src: proc_short = "It"
            elif "IV" in src: proc_short = "IV"
            elif "LaserCalibration" in src: proc_short = "LaserCalibration"

        m = file_idx_re.search(str(src))
        file_idx = int(m.group(1)) if m else None

        rows.append({
            "start_time": start_time,
            "start_dt": start_dt,
            "time_hms": time_hms,
            "proc": proc_short,
            "proc_full": proc_full,
            "chip": row.get("Chip number"),
            "VG": row.get("VG"),
            "VDS": row.get("VDS"),
            "VL": row.get("Laser voltage"),
            "wl": row.get("Laser wavelength"),
            "period": row.get("Laser ON+OFF period"),
            "info": row.get("Information"),
            "VSD_start": row.get("VSD start"),
            "VSD_end": row.get("VSD end"),
            "VSD_step": row.get("VSD step"),
            "VG_start": row.get("VG start"),
            "VG_end": row.get("VG end"),
            "VG_step": row.get("VG step"),
            "source_file": src,
            "file_idx": file_idx,
        })

    if not rows:
        return pl.DataFrame()

    df = pl.DataFrame(rows).sort("start_time", nulls_last=True)

    # ---- build 'summary' in Python (no pl.map_rows) ----
    def _mk_summary(r: dict) -> str:
        p = r.get("proc")
        chip = (int(r["chip"]) if r.get("chip") is not None and str(r.get("chip")).strip() != "" else "?")
        if p == "It":
            return (f"It  chip {chip}  "
                    f"VG={r.get('VG','?')} V  VDS={r.get('VDS','?')} V  "
                    f"VL={r.get('VL','?')} V  λ={r.get('wl','?')} nm  "
                    f"period={r.get('period','?')} s  "
                    f"#{r.get('file_idx','?')}")
        if p == "IVg":
            return (f"IVg chip {chip}  VDS={r.get('VDS','?')} V  "
                    f"VG:{r.get('VG_start','?')}→{r.get('VG_end','?')} (step {r.get('VG_step','?')})  "
                    f"#{r.get('file_idx','?')}")
        if p == "IV":
            return (f"IV  chip {chip}  VG={r.get('VG','?')} V  "
                    f"VSD:{r.get('VSD_start','?')}→{r.get('VSD_end','?')} (step {r.get('VSD_step','?')})  "
                    f"#{r.get('file_idx','?')}")
        if p == "LaserCalibration":
            return f"LaserCalibration λ={r.get('wl','?')} nm  #{r.get('file_idx','?')}"
        return f"{p} #{r.get('file_idx','?')}"

    summaries = []
    for r in df.iter_rows(named=True):
        summaries.append(_mk_summary(r))
    df = df.with_columns(pl.Series("summary", summaries))

    # Sequence number in day
    df = df.with_columns(pl.arange(1, df.height + 1).alias("seq"))

    return df.select(
        "seq","time_hms","proc","chip","summary","source_file","file_idx","start_time"
    )

def print_day_timeline(meta_csv: str, base_dir: Path, *, save_csv: bool = True) -> pl.DataFrame:
    tl = build_day_timeline(meta_csv, base_dir)
    if tl.height == 0:
        print("[warn] no experiments found")
        return tl

    print("\n=== Day timeline (chronological) ===")
    for r in tl.iter_rows(named=True):
        print(f"{r['seq']:>3d}  {r['time_hms']:>8}  {r['summary']}")
    print("====================================\n")

    if save_csv:
        out = Path(meta_csv).with_name(Path(meta_csv).stem + "_timeline.csv")
        tl.write_csv(out)
        print(f"saved {out}")

    return tl
