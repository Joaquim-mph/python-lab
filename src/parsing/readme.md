# parse_folder.py — Function-by-Function Walkthrough

What each function does, its inputs/outputs, edge cases, and notable implementation details.

---

## Module Context (Quick)

- **Imports:** `Path`, `re`, `datetime as dt`, typing helpers, `polars as pl`, `yaml`.
- **Optional import:** `print_day_timeline` (falls back to a no-op returning an empty `pl.DataFrame()` if import fails).
- **Header parsing regexes:** tolerant patterns for  
  `# Procedure: <...>`, `# Parameters:`, `# Metadata:`, `# Data:`, `# Start time: ...`.
- **_TYPE_MAP:** maps schema type strings (`int`, `float`, `str`, `bool`, `datetime`, `float_no_unit`) to casters.

---

## Helpers

### `_load_schema(yaml_path: Path | None) -> dict[str, Any]`
- **Purpose:** Load a YAML schema (`procedures.yml`) declaring expected keys and data types.  
- **Inputs:** Path to YAML file (or None).  
- **Output:** Dict (empty if missing).  
- **Notes:** Returns `{}` if file absent; uses `yaml.safe_load`.

---

### `_short_proc(proc_full: str | None) -> str`
- **Purpose:** Reduce fully-qualified procedure (e.g., `laser_setup.procedures.IVg.IVg`) to short tag (`"IVg"`).  
- **Output:** Short string or `"?"` if absent.  

---

### `_infer_proc_from_name(path: Path) -> str | None`
- **Purpose:** Heuristic fallback to infer procedure type from filename.  
- **Logic:** Looks for cues (case-insensitive):  
  - `"ivgt"` → `IVgT`  
  - `"ivg"` → `IVg`  
  - `"itt"` → `ITt`  
  - `"lasercalibration"` → `LaserCalibration`  
- **Output:** Short name or `None`.  

---

### `_coerce(value: str | None, expected: str | None) -> Any`
- **Purpose:** Convert header strings to typed values via schema.  
- **Key behaviors:**
  - If no expected type → heuristics: detect int, float (sci notation), booleans, else return string.
  - If expected type in `_TYPE_MAP`:  
    - **Numeric:** extract numeric token (`"0.1 V"` → `0.1`).  
    - **Datetime:** epoch seconds or ISO → `datetime.datetime`.  
  - Casting errors → `None` or original value.  
- **Why useful:** Robust against units (`V`, `A`), mixed formats.

---

### `_epoch_or_mtime(start_time_str: str | None, path: Path) -> tuple[float | None, dt.datetime | None]`
- **Purpose:** Resolve usable timestamp if header missing/broken.  
- **Process:**  
  - If numeric string → epoch.  
  - Else → file’s modification time.  
- **Output:** `(epoch_float | None, datetime | None)`.  
- **Edge cases:** `(None, None)` if both fail.  

---

### `_slugify(name: str) -> str`
- **Purpose:** Create URL/filename-friendly slug.  
- **Rule:** Replace non-alphanumerics with dashes; strip; fallback `"unknown"`.  

---

### `_day_from_df(df: pl.DataFrame) -> str | None`
- **Purpose:** Infer canonical day (`YYYY-MM-DD`) from `start_dt`.  
- **Logic:** Take min `start_dt` → `.date()`.  
- **Output:** ISO string or None.  
- **Note:** Not used in main flows, but handy for day IDs.  

---

## Core Parsers

### `parse_header(path: Path, schema: dict[str, Any], *, verbose: bool=False) -> dict[str, Any]`
- **Purpose:** Read CSV header (until `# Data:`) and extract:  
  `procedure_full`, `proc`, `start_time`, `start_dt`, `source_file`, Parameters, Metadata.
- **Flow:**  
  1. Stream lines until `# Data:`; capture key fields.  
  2. Determine `proc`: header → `_short_proc`; else `_infer_proc_from_name` or `"?"`.  
  3. Apply schema coercion if available.  
  4. Compute `(start_time, start_dt)` via header or mtime.  
- **Output:** Flat dict with metadata.  
- **Errors:** Returns `{}` on failure (logs if verbose).  

---

### `parse_folder_metadata(base_dir: Path, *, schema_yaml: Path | None=None, save_csv: bool=True, out_name: str="metadata.csv", only_procs: Iterable[str] | None=None, verbose: bool=False) -> pl.DataFrame`
- **Purpose:** Crawl dir, parse all `*.csv` headers → consolidated metadata table.  
- **Flow:**  
  1. Load schema.  
  2. Find CSVs (skip `._*`).  
  3. Parse each via `parse_header`.  
  4. Add `file_idx` from suffix if present.  
  5. Normalize paths, coerce columns, sort by time.  
  6. Optionally save CSV.  
- **Output:** `pl.DataFrame`.  
- **Side-effects:** Prints summary; writes CSV if enabled.  

---

## “One Folder” Runners

### `run_one_day(day_raw_dir: Path, *, schema_path: Path | None=None, out_root: Path=Path("data/metadata"), overwrite: bool=True, make_timeline: bool=True, verbose: bool=True) -> dict`
- **Purpose:** Process one raw folder → `data/metadata/<folder>/`.  
- **Flow:**  
  1. Parse CSVs (no save).  
  2. If empty → return early.  
  3. Use folder name as `day_id`.  
  4. Write `metadata.csv`.  
  5. If `make_timeline=True`, generate `timeline.csv`.  
- **Output:** Dict with paths, row counts, written=True if success.  

---

### `run_all_days(raw_root: str | Path="data/raw", *, schema: str | Path="configs/procedures.yml", out_root: str | Path="data/metadata", overwrite: bool=True, make_timeline: bool=True, verbose: bool=True) -> pl.DataFrame`
- **Purpose:** Iterate first-level subfolders in raw_root, run `run_one_day`.  
- **Flow:**  
  1. Enumerate dirs.  
  2. Skip dirs without CSVs.  
  3. Run `run_one_day` per dir.  
  4. Build index frame → save `_index.csv`.  
- **Output:** Index `pl.DataFrame`.  
- **Scope:** First-level only. For deeper use recursive runners.  

---

## Recursive, Structure-Preserving Runners

- **EXCLUDE_DIRS:** `{".git", ".venv", "__pycache__", ".ipynb_checkpoints"}`  

### `find_csv_dirs(raw_root: Path) -> list[Path]`
- **Purpose:** Discover dirs under raw_root containing at least one CSV.  
- **Flow:** `rglob("*.csv")` → unique parents, skip excluded dirs.  
- **Output:** Sorted list of dirs.  

---

### `process_one_dir_mirroring(raw_dir: Path, *, raw_root: Path=Path("data/raw"), meta_root: Path=Path("data/metadata"), schema_path: Path | None=Path("configs/procedures.yml"), overwrite: bool=True, make_timeline: bool=True, verbose: bool=True) -> dict`
- **Purpose:** Process one dir, mirror structure from raw_root → meta_root.  
- **Flow:**  
  1. Compute rel_path.  
  2. Parse headers.  
  3. Write `metadata.csv`.  
  4. Optionally produce `timeline.csv`.  
- **Output:** Dict with rel_path, output paths, row counts.  
- **Why:** Preserves arbitrary nesting.  

---

### `process_all_raw_recursive(raw_root: str | Path="data/raw", *, meta_root: str | Path="data/metadata", schema: str | Path="configs/procedures.yml", overwrite: bool=True, make_timeline: bool=True, verbose: bool=True) -> pl.DataFrame`
- **Purpose:** Recursively process every dir with CSVs.  
- **Flow:**  
  1. Discover dirs with `find_csv_dirs`.  
  2. Run `process_one_dir_mirroring` per dir.  
  3. Return summary DataFrame.  
- **Output:** Compact log frame.  

---

## Practical Notes / Edge Cases

- **Units in values:** `_coerce` extracts numeric tokens → `"0.1 V"` → `0.1`.  
- **Timestamps:** fallback to file mtime if missing/unparseable.  
- **Schema optional:** Parsing works without schema, but stricter with one.  
- **Timelines:** Produced via `print_day_timeline`, normalized to `timeline.csv`.  
- **Structure options:**  
  - Use `run_all_days` for flat folder trees.  
  - Use recursive runners for nested structures.  

---

## Extra Note

If desired, minimal docstrings can be added above each function in the code itself, or a Markdown doc can be generated directly from source.
