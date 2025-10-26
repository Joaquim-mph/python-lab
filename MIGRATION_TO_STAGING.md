# Migration Guide: Adding a Staging Layer and Pydantic Parameters to the Second Project

> Audience: a contributor who already understands the **second project** (parsers, chip histories, CLI/TUI, plots) and wants to integrate a **staging layer** (Parquet + manifest) and **Pydantic-based parameters** cleanly—without breaking existing workflows.

---

## 0) Executive Summary

- Introduce a **staging layer** that writes two artifacts per run:
  1) **Data Parquet** under `02_stage/raw_measurements/proc=<PROC>/date=<YYYY-MM-DD>/run_id=<sha1>/part-000.parquet`.
  2) **Manifest Parquet** (`02_stage/_manifest/manifest.parquet`) with one row per run (authoritative metadata).

- Move **chip histories** to be computed **from the manifest**, not by scanning day-level `metadata.csv` files. Keep metadata CSVs only as **exports** (human-friendly views).

- Add **Pydantic** to define/validate:
  - `StagingConfig` (paths, parallelism, tz, etc.).
  - `ManifestRow` (schema for authoritative metadata rows).
  - (Optionally) **procedure-specific** models (IV, IVg, ITS) for per-run fields.

This keeps the second project fast, reproducible, and consistent with the first project’s approach.

---

## 1) Terminology & Goals

- **Raw** (`01_raw/`): CSVs exactly as produced by instruments/tools.
- **Stage** (`02_stage/`): standardized Parquet + a single **manifest** table; _source of truth for metadata_.
- **Intermediate** (`03_intermediate/`): optional, pre-segmented data (not required for migration).
- **Analysis** (`04_analysis/`): outputs for statistics, fits, tables.
- **Plots** (`plots/`): figures and publications resources.

**Goal:** Enable **fast, cross-day queries** and **chip histories** by reading a single manifest table, while the TUI/CLI/plotters keep the same “feel.”

---

## 2) Architecture Changes (Before → After)

**Before (second project):**
```
CSV headers  →  parse → metadata/day/*.csv → histories → plots/TUI
                                 ↑
                            authoritative
```

**After (staging-first):**
```
CSV → stage_run() → Data Parquet + Manifest Row → histories → plots/TUI
                                  ↑                         ↑
                           authoritative               metadata CSVs (export only)
```

- **Authoritative metadata** lives in the **manifest** (not day-level CSVs).
- **Chip histories** and **TUI discovery** read from the manifest. You may still **export** day CSVs from the manifest for human review/share.

---

## 3) Files & Directory Layout

```
project_root/
├─ data/
│  ├─ 01_raw/                          # raw CSVs (unchanged)
│  ├─ 02_stage/
│  │  ├─ raw_measurements/
│  │  │  └─ proc=ITS/date=2025-10-18/run_id=abcd1234/part-000.parquet
│  │  └─ _manifest/
│  │     ├─ manifest.parquet
│  │     └─ events/                    # optional per-file JSON logs
│  ├─ 03_intermediate/                 # optional, if/when you add it
│  └─ 04_analysis/                     # existing outputs (unchanged)
├─ src/
│  ├─ stage.py                         # NEW: staging writer functions
│  ├─ models/
│  │  ├─ config.py                     # NEW: Pydantic configs
│  │  └─ manifest.py                   # NEW: Pydantic manifest row
│  ├─ parser.py                        # existing: header & CSV normalization (reuse)
│  ├─ utils.py                         # existing: IO, hashing, tz helpers, etc.
│  ├─ histories.py                     # UPDATED: build from manifest
│  ├─ plots/                           # unchanged
│  ├─ tui/                             # unchanged (reads exported histories)
│  └─ cli/
│     └─ process_and_analyze.py        # UPDATED: add `stage-all` & wire full pipeline
└─ requirements.txt
```

---

## 4) Pydantic Models (drop-in)

Create `src/models/manifest.py`:

```python
from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

Proc = Literal["IV", "IVg", "ITS"]

class ManifestRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Identity / partition
    run_id: str = Field(..., min_length=8, max_length=64)
    source_file: Path
    proc: Proc
    date_local: date
    start_time_utc: datetime
    file_idx: Optional[int] = Field(default=None, ge=0)

    # Chip / grouping
    chip_group: Optional[str] = None
    chip_number: Optional[int] = Field(default=None, ge=0)
    chip_name: Optional[str] = None

    # Experiment descriptors
    has_light: Optional[bool] = None
    laser_voltage_v: Optional[float] = None
    laser_wavelength_nm: Optional[float] = None
    laser_period_s: Optional[float] = None
    vg_start_v: Optional[float] = None
    vg_end_v: Optional[float] = None
    vds_v: Optional[float] = None
    duration_s: Optional[float] = Field(default=None, ge=0)

    # UX helpers / governance
    summary: Optional[str] = None
    schema_version: int = 1
    extraction_version: Optional[str] = None
    ingested_at_utc: datetime

    @field_validator("run_id")
    @classmethod
    def _lowercase_runid(cls, v: str) -> str:
        return v.strip().lower()
```

Create `src/models/config.py`:

```python
from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

class StagingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_root: Path = Field(..., description="01_raw root")
    stage_root: Path = Field(..., description="02_stage/raw_measurements root")
    rejects_dir: Optional[Path] = None
    events_dir: Optional[Path] = None
    manifest_path: Optional[Path] = None

    workers: int = Field(6, ge=1, le=32)
    polars_threads: int = Field(1, ge=1, le=16)
    local_tz: str = Field("America/Santiago")

    @field_validator("rejects_dir", "events_dir", "manifest_path")
    @classmethod
    def _fill_defaults(cls, v, info):
        if v is not None:
            return v
        root = info.data.get("stage_root")
        if root is None:
            return v
        if info.field_name == "rejects_dir":
            return (root.parent / "_rejects")
        if info.field_name == "events_dir":
            return (root / "_manifest" / "events")
        if info.field_name == "manifest_path":
            return (root / "_manifest" / "manifest.parquet")
        return v
```

> Tip: keep models **small and focused**. Add new optional fields as you need them; bump `schema_version` for breaking changes.

---

## 5) Staging Writer (core functions)

Create `src/stage.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List
import polars as pl

from .models.config import StagingConfig
from .models.manifest import ManifestRow
from .parser import read_and_normalize  # you already have this (or equivalent)
from .utils import compute_run_id, ensure_start_time_utc  # adapt from your utils

def stage_run(csv_path: Path, cfg: StagingConfig) -> ManifestRow:
    # 1) read & normalize CSV (existing parser – returns (df, meta))
    df, meta = read_and_normalize(csv_path)  # df: pl.DataFrame, meta: dict

    # 2) compute partition info + run_id
    start_utc = ensure_start_time_utc(meta, cfg.local_tz)
    date_local = start_utc.astimezone().date()  # ensure tz applied inside ensure_start_time_utc
    run_id = compute_run_id(csv_path, start_utc)  # sha1(path|timestamp)

    # 3) write parquet atomically
    out = (
        cfg.stage_root
        / f"proc={meta['proc']}"
        / f"date={date_local.isoformat()}"
        / f"run_id={run_id}"
    )
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "part-000.parquet.tmp"
    df.write_parquet(tmp)
    tmp.rename(out / "part-000.parquet")

    # 4) build manifest row
    row = ManifestRow(
        run_id=run_id,
        source_file=csv_path.relative_to(cfg.raw_root),
        proc=meta["proc"],
        date_local=date_local,
        start_time_utc=start_utc,
        file_idx=meta.get("file_idx"),
        chip_group=meta.get("chip_group"),
        chip_number=meta.get("chip_number"),
        chip_name=meta.get("chip_name"),
        has_light=meta.get("has_light"),
        laser_voltage_v=meta.get("laser_voltage_v"),
        laser_wavelength_nm=meta.get("laser_wavelength_nm"),
        laser_period_s=meta.get("laser_period_s"),
        vg_start_v=meta.get("vg_start_v"),
        vg_end_v=meta.get("vg_end_v"),
        vds_v=meta.get("vds_v"),
        duration_s=meta.get("duration_s"),
        summary=meta.get("summary"),
        schema_version=1,
        extraction_version=meta.get("extraction_version"),
        ingested_at_utc=datetime.now(timezone.utc),
    )
    return row

def append_manifest(rows: List[ManifestRow], manifest_path: Path) -> None:
    from pydantic import TypeAdapter
    ta = TypeAdapter(list[ManifestRow])
    payload = ta.validate_python(rows)  # batch validation/coercion
    df = pl.DataFrame([r.model_dump() for r in payload])

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        pl.concat([pl.read_parquet(manifest_path), df], how="vertical").write_parquet(manifest_path)
    else:
        df.write_parquet(manifest_path)

def stage_all(csvs: Iterable[Path], cfg: StagingConfig) -> None:
    rows = []
    for p in csvs:
        try:
            rows.append(stage_run(p, cfg))
        except Exception as e:
            # optional: write rejects/event JSON here for triage
            print(f"[reject] {p}: {e}")
    append_manifest(rows, cfg.manifest_path or (cfg.stage_root / "_manifest" / "manifest.parquet"))
```

**Key points**:
- Keep staging **idempotent**: re-running should not duplicate rows; use stable `run_id`.
- Write Parquet atomically (tmp → rename).
- Build **all history drivers from the manifest** (next section).

---

## 6) Chip Histories From the Manifest

Update `src/histories.py` to read **manifest.parquet** instead of day-level `metadata.csv`:

```python
from __future__ import annotations
from pathlib import Path
import polars as pl

def build_chip_history(manifest_path: Path, chip_number: int, proc: str | None = None) -> pl.DataFrame:
    lf = pl.scan_parquet(manifest_path)
    q = lf.filter(pl.col("chip_number") == chip_number)
    if proc:
        q = q.filter(pl.col("proc") == proc)
    df = (
        q.sort(["start_time_utc", "file_idx"])
         .with_columns(
             pl.int_range(1, pl.len()+1).over("chip_number").alias("seq")
         )
         .select([
             "seq", "date_local", "proc", "has_light", "summary",
             "chip_group", "chip_number", "run_id", "source_file"
         ])
    ).collect()
    return df

def export_chip_history_csv(manifest_path: Path, chip_number: int, out_csv: Path, proc: str | None = None) -> None:
    df = build_chip_history(manifest_path, chip_number, proc)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(out_csv)
```

- **Downstream plotters/TUI** keep consuming `*_history.csv` (stable contract).
- If you need **per-day** CSVs for humans, export them from the manifest with small filters.

---

## 7) CLI Changes (Typer)

Extend your existing `process_and_analyze.py` to add a **stage-all** command and wire full pipeline:

```python
import typer
from pathlib import Path
from src.models.config import StagingConfig
from src.stage import stage_all
from src.histories import export_chip_history_csv

app = typer.Typer(add_completion=False)

@app.command("stage-all")
def stage_all_cmd(
    raw_root: Path = typer.Option(..., help="data/01_raw"),
    stage_root: Path = typer.Option(..., help="data/02_stage/raw_measurements"),
    local_tz: str = typer.Option("America/Santiago"),
    workers: int = typer.Option(6),
    polars_threads: int = typer.Option(1),
):
    cfg = StagingConfig(
        raw_root=raw_root,
        stage_root=stage_root,
        local_tz=local_tz,
        workers=workers,
        polars_threads=polars_threads,
    )
    csvs = raw_root.rglob("*.csv")
    stage_all(csvs, cfg)

@app.command("chip-histories")
def chip_histories_cmd(
    manifest_path: Path = typer.Option(..., help="data/02_stage/_manifest/manifest.parquet"),
    chip: int = typer.Option(..., help="Chip number"),
    out_csv: Path = typer.Option(..., help="Where to write Alisson{chip}_history.csv"),
    proc: str | None = typer.Option(None, help="Optional: filter by procedure"),
):
    export_chip_history_csv(manifest_path, chip, out_csv, proc)

@app.command("full-pipeline")
def full_pipeline_cmd(
    raw_root: Path = typer.Option(...),
    stage_root: Path = typer.Option(...),
    manifest_path: Path = typer.Option(...),
    chip: int = typer.Option(...),
    history_out: Path = typer.Option(...),
):
    stage_all_cmd(raw_root, stage_root)  # stage all runs
    chip_histories_cmd(manifest_path, chip, history_out)  # build history from manifest

if __name__ == "__main__":
    app()
```

> You can add pretty logging/progress via Rich; keep options aligned with your first project for a uniform UX.

---

## 8) Migration Plan (Backfill + Cutover)

1) **Add new modules** (`models/`, `stage.py`) alongside your current code.
2) **Run backfill staging** over existing `01_raw/`:
   ```bash
   python -m src.cli.process_and_analyze stage-all \
      --raw-root data/01_raw \
      --stage-root data/02_stage/raw_measurements \
      --local-tz America/Santiago \
      --workers 8 --polars-threads 2
   ```
3) **Build chip histories** _from manifest_ and compare to current outputs:
   ```bash
   python -m src.cli.process_and_analyze chip-histories \
      --manifest-path data/02_stage/_manifest/manifest.parquet \
      --chip 67 \
      --out-csv data/histories/Alisson67_history.csv
   ```
4) **Diff** old vs new histories (spot-check: seq order, counts, basic fields).
5) **Cutover**: switch any internal code that reads day-level metadata CSVs to read histories exported from the manifest (contract stays the same, source changes).
6) **Deprecate** day-level metadata CSVs as inputs; keep an **export command** to generate them for humans:
   ```bash
   # (pseudo) manifest → per-day metadata.csv exporter
   python -m src.cli.process_and_analyze export-metadata --date 2025-10-18
   ```

---

## 9) Validation & Testing Checklist

- **Schema validation**: `ManifestRow(extra="forbid")`. Add a unit test that a row with an extra key fails validation.
- **Idempotency**: run `stage-all` twice; manifest row count should not explode (use stable `run_id` & dedupe if needed).
- **Time handling**: unit test for `ensure_start_time_utc` with/without tz info.
- **Performance smoke**: stage 5–10k CSVs—ensure no shared-state crashes; consider per-process Polars threads.
- **Downstream parity**: compare plots/histories built pre- vs post-migration on a few chips/dates.

---

## 10) Performance Notes

- Use **batch Pydantic validation** (`TypeAdapter(list[ManifestRow])`) before writing to Parquet.
- Keep Parquet **column order stable** for better diffs/compression (not strictly required).
- Avoid overly wide DataFrames; keep manifest **narrow** and denormalized.
- Consider a periodic **manifest compaction** if you append frequently.

---

## 11) Failure Modes & Triage

- **Missing/odd headers**: stage to **rejects** with reason; don’t crash the batch.
- **Timestamp ambiguity**: respect `local_tz` and fall back deterministically (e.g., file mtime) only as last resort.
- **Schema drift**: bump `schema_version`, keep readers backward-compatible where possible (e.g., fill new nullable cols).

---

## 12) FAQ (Short)

**Q: Do we still need metadata CSVs?**  
A: Not as inputs. Maintain them as **exports** for human review/sharing; generate **from manifest** to avoid drift.

**Q: Will TUI/plotters break?**  
A: No—keep their contract reading `*_history.csv`. You just change **how** histories are generated (from the manifest).

**Q: Can we precompute helpful fields?**  
A: Yes—`has_light`, `summary`, and `seq` are cheap and speed up TUI/CLI dramatically.

---

## 13) Ready-to-Run Commands

```bash
# 1) Stage everything
python -m src.cli.process_and_analyze stage-all \
  --raw-root data/01_raw \
  --stage-root data/02_stage/raw_measurements \
  --workers 8 --polars-threads 2

# 2) Build and export a chip history (chip 67 example)
python -m src.cli.process_and_analyze chip-histories \
  --manifest-path data/02_stage/_manifest/manifest.parquet \
  --chip 67 \
  --out-csv data/histories/Alisson67_history.csv

# 3) (Optional) Full pipeline
python -m src.cli.process_and_analyze full-pipeline \
  --raw-root data/01_raw \
  --stage-root data/02_stage/raw_measurements \
  --manifest-path data/02_stage/_manifest/manifest.parquet \
  --chip 67 \
  --history-out data/histories/Alisson67_history.csv
```

---

## 14) Appendix: Utilities You Likely Reuse

- `compute_run_id(path, start_utc)` → SHA1 over `"path|timestamp"` (lowercased); first 16–20 chars is plenty.
- `ensure_start_time_utc(meta, local_tz)` → parse start time (header preferred; else path; else mtime), localize → UTC.
- `read_and_normalize(path)` → returns `(polars.DataFrame, meta: dict)` with canonicalized columns/units and essential metadata (proc, chip info, LED, wavelengths, etc.).

These already exist in your codebase; keep behavior stable and feed them into staging.

---

### Closing
This migration gives you _one source of truth_ (manifest), faster queries, simpler tooling, and parity with the first project’s proven approach. The change is **surgical**: add staging, point histories to the manifest, and keep CSV exports as human-friendly views.
