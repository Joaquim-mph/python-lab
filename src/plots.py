from __future__ import annotations
from pathlib import Path
import numpy as np
from src.utils import _proc_from_path, _file_index, _read_measurement
import polars as pl
import matplotlib.pyplot as plt

# -------------------------------
# Config
# -------------------------------

BASE_DIR     = Path(".")
FIG_DIR = Path("figs")
FIG_DIR.mkdir(exist_ok=True)

# -------------------------------
# Make timeline + sessions
# -------------------------------
def load_and_prepare_metadata(meta_csv: str, chip: float) -> pl.DataFrame:
    df = pl.read_csv(meta_csv, infer_schema_length=1000)
    # Normalize column names we will use often
    df = df.rename({"Chip number": "Chip number",
                    "Laser voltage": "Laser voltage",
                    "Laser toggle": "Laser toggle",
                    "source_file": "source_file"})

    # Filter chip
    df = df.filter(pl.col("Chip number") == chip)

    # Infer procedure and index
    df = df.with_columns([
        pl.col("source_file").map_elements(_proc_from_path).alias("proc"),
        pl.col("source_file").map_elements(_file_index).alias("file_idx"),
        pl.when(pl.col("Laser toggle").cast(pl.Utf8).str.to_lowercase() == "true")
          .then(pl.lit(True))
          .otherwise(pl.lit(False))
          .alias("with_light"),
        pl.col("Laser voltage").cast(pl.Float64).alias("VL_meta"),
        pl.col("VG").cast(pl.Float64).alias("VG_meta").fill_null(strategy="zero")
    ]).sort("file_idx")

    # Build sessions = [IVg → ITS… → IVg] blocks
    # We'll assign the *closing* IVg to the same session as the preceding ITS.
    session_id = 0
    seen_any_ivg = False
    seen_its_since_ivg = False
    ids = []
    roles = []

    for proc in df["proc"].to_list():
        if proc == "IVg":
            if not seen_any_ivg:
                # first IVg starts session
                session_id += 1
                seen_any_ivg = True
                seen_its_since_ivg = False
                roles.append("pre_ivg")
                ids.append(session_id)
            else:
                if seen_its_since_ivg:
                    # this IVg closes the existing session
                    roles.append("post_ivg")
                    ids.append(session_id)
                    # next block will start on the next IVg or ITS as needed
                    seen_its_since_ivg = False
                    seen_any_ivg = False  # force new session on next IVg/ITS
                else:
                    # back-to-back IVg → treat as a new session pre_ivg
                    session_id += 1
                    roles.append("pre_ivg")
                    ids.append(session_id)
                    seen_its_since_ivg = False
        elif proc == "ITS":
            if not seen_any_ivg:
                # ITS without a prior IVg — start a new session
                session_id += 1
                seen_any_ivg = True
            roles.append("its")
            ids.append(session_id)
            seen_its_since_ivg = True
        else:
            roles.append("other")
            ids.append(session_id)

    df = df.with_columns([
        pl.Series("session", ids),
        pl.Series("role", roles),
    ])
    return df

# -------------------------------
# Plotting
# -------------------------------

def plot_ivg_sequence(df: pl.DataFrame, base_dir: Path, tag: str):
    """Plot all IVg in chronological order (Id vs Vg)."""
    ivg = df.filter(pl.col("proc") == "IVg").sort("file_idx")
    if ivg.height == 0:
        return
    plt.figure()
    for row in ivg.iter_rows(named=True):
        path = base_dir / row["source_file"]
        if not path.exists():
            print(f"[warn] missing file: {path}")
            continue
        d = _read_measurement(path)
        # Expect columns: VG, I (standardized)
        if not {"VG", "I"} <= set(d.columns):
            print(f"[warn] {path} lacks VG/I; got {d.columns}")
            continue
        lbl = f"#{int(row['file_idx'])}  {'light' if row['with_light'] else 'dark'}"
        plt.plot(d["VG"], d["I"]*1e6, label=lbl)
    plt.xlabel("VG (V)")
    plt.ylabel("Current (µA)")
    plt.title(f"Encap{int(df['Chip number'][0])} — IVg")
    plt.legend(fontsize=8)
    plt.tight_layout()
    out = FIG_DIR / f"Encap{int(df['Chip number'][0])}_IVg_sequence_{tag}.png"
    plt.savefig(out, dpi=200)
    print(f"saved {out}")
        
        
def plot_its_overlay(df: pl.DataFrame, base_dir: Path, tag: str):
    import numpy as np

    its = df.filter(pl.col("proc") == "ITS").sort("file_idx")
    if its.height == 0:
        print("[warn] no ITS rows in metadata")
        return

    plt.figure()
    curves_plotted = 0

    # Collect info for automatic shading/x-limits
    t_totals = []              # per-trace total duration (max t)
    starts_vl, ends_vl = [], []  # ON start/end inferred from VL data
    on_durations_meta = []     # ON duration from metadata (if present)

    for row in its.iter_rows(named=True):
        path = base_dir / row["source_file"]
        if not path.exists():
            print(f"[warn] missing file: {path}")
            continue

        d = _read_measurement(path)
        if not {"t", "I"} <= set(d.columns):
            print(f"[warn] {path} lacks t/I; got {d.columns}")
            continue

        # plot the trace
        lbl = (
            f"#{int(row['file_idx'])}  session {row['session']}  "
            f"Vg={row.get('VG_meta', 0):g} V  VL={row.get('VL_meta', float('nan'))} V"
        )
        plt.plot(d["t"], d["I"], label=lbl)
        curves_plotted += 1

        # total duration for this trace
        try:
            t_totals.append(float(d["t"].max()))
        except Exception:
            pass

        # Try to infer ON window from VL if available
        if "VL" in d.columns:
            try:
                vl = d["VL"].to_numpy()
                tt = d["t"].to_numpy()
                on_idx = np.where(vl > 0)[0]
                if on_idx.size:
                    starts_vl.append(float(tt[on_idx[0]]))
                    ends_vl.append(float(tt[on_idx[-1]]))
            except Exception:
                pass

        # Grab ON duration from metadata if present on this row
        if "Laser ON+OFF period" in its.columns:
            try:
                on_durations_meta.append(float(row["Laser ON+OFF period"]))
            except Exception:
                pass

    if curves_plotted == 0:
        print("[warn] no ITS traces plotted; skipping light-window shading")
        return

    # ---- Decide x-limits from data (median of total durations)
    if t_totals:
        T_total = float(np.median(t_totals))
        if np.isfinite(T_total) and T_total > 0:
            plt.xlim(20, T_total)

    # ---- Compute ON window [t0, t1]
    t0 = t1 = None

    # 1) Best: from VL signal (median across traces)
    if starts_vl and ends_vl:
        t0 = float(np.median(starts_vl))
        t1 = float(np.median(ends_vl))

    # 2) Next: from metadata (treat 'Laser ON+OFF period' as ON duration; OFF–ON–OFF centered)
    if (t0 is None or t1 is None) and on_durations_meta and t_totals:
        on_dur = float(np.median(on_durations_meta))
        T_total = float(np.median(t_totals))
        if np.isfinite(on_dur) and np.isfinite(T_total) and T_total > 0:
            pre_off = max(0.0, (T_total - on_dur) / 2.0)
            t0 = pre_off
            t1 = pre_off + on_dur

    # 3) Fallback: middle third of the run
    if (t0 is None or t1 is None) and t_totals:
        T_total = float(np.median(t_totals))
        if np.isfinite(T_total) and T_total > 0:
            t0 = T_total / 3.0
            t1 = 2.0 * T_total / 3.0

    if (t0 is not None) and (t1 is not None) and (t1 > t0):
        plt.axvspan(t0, t1, alpha=0.15)

    plt.xlabel("t (s)")
    plt.ylabel("Id (A)")
    plt.title(f"Chip {int(df['Chip number'][0])} — ITS overlay")
    plt.legend(fontsize=8)
    plt.tight_layout()
    out = FIG_DIR / f"chip{int(df['Chip number'][0])}_ITS_overlay_{tag}.png"
    plt.savefig(out, dpi=200)
    print(f"saved {out}")


def plot_its_by_vg(
    df: pl.DataFrame,
    base_dir: Path,
    tag: str,
    vgs: list[float] | None = None,          # e.g., [-2.0]
    wavelengths: list[float] | None = None,  # e.g., [455.0]
    tol: float = 1e-6,                       # tolerance for Vg match
    wl_tol: float = 1e-6,                    # tolerance for wavelength match
    xlim_seconds: float | None = 180.0,      # None -> autoscale
    vl_threshold: float = 0.0,               # VL > threshold => light ON
):
    """
    Overlay ITS traces grouped by (Vg, wavelength) from metadata.
    Uses VL>vl_threshold to detect light ON; falls back to metadata ON duration if needed.
    """

    its_all = df.filter(pl.col("proc") == "ITS").sort("file_idx")
    if its_all.height == 0:
        print("[warn] no ITS rows in metadata")
        return

    if "VG_meta" not in its_all.columns:
        print("[warn] VG_meta not present in metadata; cannot group by Vg")
        return

    # Determine target Vg values
    if vgs is None:
        vgs = sorted(float(v) for v in its_all.get_column("VG_meta").drop_nulls().unique().to_list())
    else:
        vgs = list(vgs)

    # Determine target wavelengths
    if wavelengths is None:
        if "Laser wavelength" in its_all.columns:
            wavelengths = sorted(
                float(w) for w in its_all.get_column("Laser wavelength").drop_nulls().unique().to_list()
            )
        else:
            wavelengths = [float("nan")]  # no wavelength column → single pass
    else:
        wavelengths = list(wavelengths)

    for VG_target in vgs:
        for WL_target in wavelengths:
            # Build selection mask
            mask = (pl.col("VG_meta") - VG_target).abs() <= tol
            if "Laser wavelength" in its_all.columns and not np.isnan(WL_target):
                mask = mask & ((pl.col("Laser wavelength") - WL_target).abs() <= wl_tol)

            sel = its_all.filter(mask)
            if sel.height == 0:
                msg_wl = f", λ≈{WL_target:g} nm" if not np.isnan(WL_target) else ""
                print(f"[info] no ITS rows for Vg≈{VG_target:g} V{msg_wl}")
                continue

            plt.figure()
            curves_plotted = 0

            # For window/x-lims
            t_totals = []
            starts_vl, ends_vl = [], []
            on_durs_meta = []

            for row in sel.iter_rows(named=True):
                path = base_dir / row["source_file"]
                if not path.exists():
                    print(f"[warn] missing file: {path}")
                    continue

                d = _read_measurement(path)
                if not {"t", "I"} <= set(d.columns):
                    print(f"[warn] {path} lacks t/I; got {d.columns}")
                    continue

                lbl = f"#{int(row['file_idx'])}  VL={row.get('VL_meta', float('nan'))} V"
                #######
                d_clip = d.filter(pl.col("t") >= 20.0)
                plt.plot(d_clip["t"], d_clip["I"]*1e6, label=lbl)
                #plt.plot(d["t"], d["I"], label=lbl)
                curves_plotted += 1

                # total duration
                try:
                    t_totals.append(float(d["t"].max()))
                except Exception:
                    pass

                # VL-based ON detection
                if "VL" in d.columns:
                    try:
                        vl = d["VL"].to_numpy()
                        tt = d["t"].to_numpy()
                        on_idx = np.where(vl > vl_threshold)[0]
                        if on_idx.size:
                            starts_vl.append(float(tt[on_idx[0]]))
                            ends_vl.append(float(tt[on_idx[-1]]))
                    except Exception:
                        pass

                # Metadata ON duration (treat “Laser ON+OFF period” as ON duration for OFF–ON–OFF)
                if "Laser ON+OFF period" in sel.columns:
                    try:
                        on_durs_meta.append(float(row["Laser ON+OFF period"]))
                    except Exception:
                        pass

            if curves_plotted == 0:
                print(f"[warn] no ITS traces plotted for Vg≈{VG_target:g} V, λ≈{WL_target:g} nm; skipping")
                plt.close()
                continue

            # X-limits
            if xlim_seconds is not None:
                plt.xlim(20.0, float(xlim_seconds))
                T_total = float(xlim_seconds)
            else:
                T_total = float(np.median(t_totals)) if t_totals else None
                if T_total and np.isfinite(T_total) and T_total > 0:
                    plt.xlim(0.0, T_total)

            # ON window
            t0 = t1 = None
            if starts_vl and ends_vl:
                t0 = float(np.median(starts_vl))
                t1 = float(np.median(ends_vl))
            if (t0 is None or t1 is None) and on_durs_meta:
                on_dur = float(np.median(on_durs_meta))
                T_use = float(xlim_seconds) if xlim_seconds is not None else (float(np.median(t_totals)) if t_totals else None)
                if T_use and np.isfinite(T_use) and T_use > 0:
                    pre_off = max(0.0, (T_use - on_dur) / 2.0)
                    t0, t1 = pre_off, pre_off + on_dur
            if (t0 is None or t1 is None):
                T_use = (float(xlim_seconds) if xlim_seconds is not None
                         else (float(np.median(t_totals)) if t_totals else None))
                if T_use and np.isfinite(T_use) and T_use > 0:
                    t0, t1 = T_use/3.0, 2.0*T_use/3.0
            if (t0 is not None) and (t1 is not None) and (t1 > t0):
                plt.axvspan(t0, t1, alpha=0.15)

            # Title (use median wavelength in the selection when available)
            if "Laser wavelength" in sel.columns:
                wl_series = sel.get_column("Laser wavelength").cast(pl.Float64, strict=False).drop_nulls()
                if wl_series.len() > 0:
                    wl_used = float(wl_series.median())
                else:
                    wl_used = float("nan")
            else:
                wl_used = float("nan")

            wl_txt = f", λ={wl_used:.0f} nm" if np.isfinite(wl_used) else ""
            plt.title(f"Encap{int(df['Chip number'][0])} — Vg={VG_target:g} V{wl_txt}")
            plt.xlabel("Time (s)")
            plt.ylabel(f"Current (µA)")
            plt.legend(fontsize=8)
            plt.tight_layout()

            safe_vg = str(VG_target).replace("-", "m").replace(".", "p")
            safe_wl = (f"{int(round(wl_used))}nm" if np.isfinite(wl_used)
                       else ("allwl"))
            out = FIG_DIR / f"chip{int(df['Chip number'][0])}_ITS_overlay_Vg{safe_vg}_{safe_wl}_{tag}.png"
            plt.savefig(out, dpi=200)
            print(f"saved {out}")


def plot_ivg_last_of_day1_vs_first_of_day2(
    meta_day1: pl.DataFrame,
    meta_day2: pl.DataFrame,
    base_dir_day1: Path,
    base_dir_day2: Path,
    tag: str,
):
    # keep only IVg rows, already per-chip if you used load_and_prepare_metadata(...)
    ivg1 = meta_day1.filter(pl.col("proc") == "IVg").sort("file_idx")
    ivg2 = meta_day2.filter(pl.col("proc") == "IVg").sort("file_idx")

    if ivg1.height == 0 or ivg2.height == 0:
        print("[warn] one of the days has no IVg runs")
        return

    r1 = ivg1.tail(1).row(0, named=True)   # last of day 1
    r2 = ivg2.head(1).row(0, named=True)   # first of day 2

    p1 = base_dir_day1 / r1["source_file"]
    p2 = base_dir_day2 / r2["source_file"]

    d1 = _read_measurement(p1)
    d2 = _read_measurement(p2)

    if not {"VG","I"} <= set(d1.columns):
        print(f"[warn] {p1} lacks VG/I; got {d1.columns}")
        return
    if not {"VG","I"} <= set(d2.columns):
        print(f"[warn] {p2} lacks VG/I; got {d2.columns}")
        return

    plt.figure()
    lbl1 = f"Day1 last (#{int(r1['file_idx'])})"
    lbl2 = f"Day2 first (#{int(r2['file_idx'])})"
    # optionally show wavelength if present in metadata
    if "Laser wavelength" in ivg1.columns and ivg1["Laser wavelength"].drop_nulls().len() > 0:
        lbl1 += f", λ={float(ivg1['Laser wavelength'].drop_nulls().median()):.0f} nm"
    if "Laser wavelength" in ivg2.columns and ivg2["Laser wavelength"].drop_nulls().len() > 0:
        lbl2 += f", λ={float(ivg2['Laser wavelength'].drop_nulls().median()):.0f} nm"

    plt.plot(d1["VG"], d1["I"], label=lbl1)
    plt.plot(d2["VG"], d2["I"], label=lbl2)

    chip_txt = f"Chip {int(meta_day1['Chip number'][0])}" if 'Chip number' in meta_day1.columns else "Chip"
    plt.xlabel("VG (V)")
    plt.ylabel("Current (A)")
    plt.title(f"{chip_txt} — IVg: last (day1) vs first (day2)")
    plt.legend(fontsize=8)
    plt.tight_layout()

    out = FIG_DIR / f"{chip_txt.replace(' ','')}_IVg_last_day1_first_day2_{tag}.png"
    plt.savefig(out, dpi=200)
    print(f"saved {out}")

