# Chip History Timeline Guide

Complete guide for tracking experiment history across all chips using the timeline module.

---

## Overview

The timeline module now includes powerful functions to track the complete experimental history of your chips across all measurement sessions. This is particularly useful for:

- **Tracking device evolution**: See how a chip's characteristics change over time
- **Planning experiments**: Know what measurements have already been done
- **Quality control**: Identify unusual patterns or gaps in measurements
- **Documentation**: Generate complete records for publications/reports

---

## Quick Start

### Generate History for One Chip

```python
from pathlib import Path
from src.timeline import print_chip_history

# View complete history for Alisson72
print_chip_history(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("raw_data"),
    chip_number=72,
    chip_group_name="Alisson"
)
```

### Generate Histories for All Chips

```python
from pathlib import Path
from src.timeline import generate_all_chip_histories

# Automatically find all chips and generate their histories
histories = generate_all_chip_histories(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("raw_data"),
    chip_group_name="Alisson",
    save_csv=True,  # Saves AlissonXX_history.csv for each chip
    min_experiments=5  # Only chips with 5+ experiments
)
```

---

## Available Functions

### 1. `build_chip_history()`

Low-level function that builds the history DataFrame without printing.

**Parameters:**
- `metadata_dir`: Path to directory containing metadata CSV files
- `raw_data_dir`: Path to raw data directory
- `chip_number`: The chip number to track (e.g., 72 for "Alisson72")
- `chip_group_name`: Chip group prefix (default: "Alisson")

**Returns:** Polars DataFrame with columns:
- `seq`: Sequential experiment number
- `date`: Date in YYYY-MM-DD format
- `time_hms`: Time in HH:MM:SS format
- `proc`: Procedure type (IVg, ITS, IV, etc.)
- `summary`: Full experiment description
- `source_file`: Path to raw CSV file
- `file_idx`: File index number
- `start_time`: Unix timestamp
- `day_folder`: Metadata folder name

**Example:**
```python
from src.timeline import build_chip_history

history = build_chip_history(
    Path("metadata"),
    Path("raw_data"),
    chip_number=72,
    chip_group_name="Alisson"
)

# Access the data programmatically
print(f"Total experiments: {history.height}")
print(f"Procedures: {history['proc'].unique().to_list()}")
```

---

### 2. `print_chip_history()`

Print and save complete experiment history for a specific chip.

**Parameters:**
- `metadata_dir`: Path to directory containing metadata CSV files
- `raw_data_dir`: Path to raw data directory
- `chip_number`: The chip number to track
- `chip_group_name`: Chip group prefix (default: "Alisson")
- `save_csv`: If True, saves to `{chip_group_name}{chip_number}_history.csv`
- `proc_filter`: Optional filter by procedure type (e.g., "IVg", "ITS")

**Example Output:**
```
================================================================================
Complete Experiment History: Alisson72
Total experiments: 156
Date range: 2024-09-04 to 2024-09-20
================================================================================

─── 2024-09-04 (Alisson_04_sept) ──────────────────────────────────────────────
   1  14:23:15  IVg Alisson72  VDS=0.1 V  VG:-4.0→4.0 (step 0.1)  #1
   2  14:35:42  ITS Alisson72  VG=-3.0 V  VDS=0.1 V  VL=3.5 V  λ=455.0 nm  period=120.0 s  #2
   3  14:48:19  IVg Alisson72  VDS=0.1 V  VG:-4.0→4.0 (step 0.1)  #3

─── 2024-09-15 (Alisson_15_sept) ──────────────────────────────────────────────
   4  09:12:33  IVg Alisson72  VDS=0.1 V  VG:-4.0→4.0 (step 0.1)  #12
   ...

================================================================================

✓ Saved complete history to: Alisson72_history.csv
```

**Example with Filtering:**
```python
# Only show IVg measurements
print_chip_history(
    Path("metadata"),
    Path("raw_data"),
    chip_number=72,
    chip_group_name="Alisson",
    proc_filter="IVg"  # Only gate voltage sweeps
)
```

---

### 3. `generate_all_chip_histories()`

Automatically discover all chips and generate their complete histories.

**Parameters:**
- `metadata_dir`: Path to directory containing metadata CSV files
- `raw_data_dir`: Path to raw data directory
- `chip_group_name`: Chip group prefix (default: "Alisson")
- `save_csv`: If True, saves each chip's history to separate CSV
- `min_experiments`: Only include chips with at least this many experiments

**Returns:** Dictionary mapping chip_number → history DataFrame

**Example Output:**
```
Scanning metadata directory: metadata
Found 12 metadata file(s)
Found 5 unique chip(s): [68, 72, 75, 81, 100]

Processing Alisson68...
  → 23 experiments (2024-09-04 to 2024-09-15)
  → Saved to Alisson68_history.csv

Processing Alisson72...
  → 156 experiments (2024-09-04 to 2024-09-20)
  → Saved to Alisson72_history.csv

Processing Alisson75...
  → Skipped (only 3 experiment(s), minimum is 5)

Processing Alisson81...
  → 67 experiments (2024-09-08 to 2024-09-20)
  → Saved to Alisson81_history.csv

Processing Alisson100...
  → 12 experiments (2024-09-08 to 2024-09-10)
  → Saved to Alisson100_history.csv

================================================================================
Generated histories for 4 chip(s)
================================================================================
```

**Access the Results:**
```python
histories = generate_all_chip_histories(
    Path("metadata"),
    Path("raw_data"),
    chip_group_name="Alisson"
)

# Print summary for each chip
for chip_num, history in sorted(histories.items()):
    dates = history["date"].unique().to_list()
    print(f"Alisson{chip_num}: {history.height} experiments over {len(dates)} days")
```

---

## Use Cases

### 1. Track Chip Degradation

```python
from src.timeline import build_chip_history

history = build_chip_history(Path("metadata"), Path("raw_data"), 72, "Alisson")

# Count IVg measurements by date to track how often you characterized the device
ivg_by_date = history.filter(
    (pl.col("proc") == "IVg")
).group_by("date").agg([
    ("date", "count")
]).sort("date")

print("IVg characterizations per day:")
for row in ivg_by_date.iter_rows(named=True):
    print(f"  {row['date']}: {row['count']} measurements")
```

### 2. Find Specific Measurements

```python
# Find all UV stress tests (wavelength < 400nm)
history = build_chip_history(Path("metadata"), Path("raw_data"), 72, "Alisson")

# Parse wavelength from summary string (you could also join with original metadata)
uv_tests = history.filter(pl.col("summary").str.contains("λ=365.0 nm"))

print(f"Found {uv_tests.height} UV stress tests")
for row in uv_tests.iter_rows(named=True):
    print(f"  {row['date']} {row['time_hms']}: {row['summary']}")
```

### 3. Generate Summary Statistics

```python
from src.timeline import generate_all_chip_histories

histories = generate_all_chip_histories(
    Path("metadata"),
    Path("raw_data"),
    chip_group_name="Alisson",
    save_csv=False  # Don't save individual files
)

# Summary report
print("\n" + "="*80)
print("EXPERIMENT SUMMARY ACROSS ALL CHIPS")
print("="*80)

total_experiments = sum(h.height for h in histories.values())
print(f"\nTotal chips tracked: {len(histories)}")
print(f"Total experiments: {total_experiments}")

print("\nPer-chip breakdown:")
for chip_num in sorted(histories.keys()):
    h = histories[chip_num]
    proc_types = h["proc"].unique().to_list()
    print(f"  Alisson{chip_num:3d}: {h.height:4d} experiments ({', '.join(sorted(proc_types))})")
```

---

## File Organization

When you run the chip history functions, they create CSV files in your working directory:

```
python-lab/
├── Alisson68_history.csv    # Complete history for chip 68
├── Alisson72_history.csv    # Complete history for chip 72
├── Alisson81_history.csv    # Complete history for chip 81
├── ...
```

Each CSV contains all experiments for that chip, sorted chronologically, with full metadata.

---

## Integration with Existing Workflow

The chip history functions integrate seamlessly with your existing pipeline:

```python
from pathlib import Path
from src.timeline import print_chip_history, print_day_timeline

# 1. Daily timeline (single day)
print_day_timeline(
    "metadata/Alisson_15_sept/metadata.csv",
    Path("raw_data"),
    chip_group_name="Alisson"
)

# 2. Complete chip history (all days)
print_chip_history(
    Path("metadata"),
    Path("raw_data"),
    chip_number=72,
    chip_group_name="Alisson"
)

# 3. Batch process all chips
from src.timeline import generate_all_chip_histories

generate_all_chip_histories(
    Path("metadata"),
    Path("raw_data"),
    chip_group_name="Alisson",
    min_experiments=10  # Only well-characterized chips
)
```

---

## Tips and Best Practices

1. **Chip Group Naming**: Set `chip_group_name` to match your naming convention:
   - If you use "Alisson72", use `chip_group_name="Alisson"`
   - If you use "Device72", use `chip_group_name="Device"`
   - If you use just "72", use `chip_group_name=""`

2. **Filtering Results**: Use `proc_filter` to focus on specific measurement types:
   ```python
   # Only gate voltage sweeps
   print_chip_history(..., proc_filter="IVg")

   # Only time series
   print_chip_history(..., proc_filter="ITS")
   ```

3. **Minimum Experiments**: When using `generate_all_chip_histories()`, set `min_experiments` to avoid cluttering output with barely-tested chips:
   ```python
   # Only chips with substantial data
   generate_all_chip_histories(..., min_experiments=20)
   ```

4. **Save Strategies**:
   - Set `save_csv=True` to keep permanent records
   - Set `save_csv=False` for quick exploration without creating files

5. **Programmatic Analysis**: Use `build_chip_history()` when you need to:
   - Perform custom analysis on the history data
   - Generate custom plots
   - Export data in different formats
   - Build automated quality control checks

---

## Example Script

See `example_chip_history.py` for a complete working example that demonstrates:
- Single chip history generation
- Automatic all-chip processing
- Programmatic data access and analysis

Run it with:
```bash
python example_chip_history.py
```

---

## Troubleshooting

**Problem**: "No metadata files found"
- **Solution**: Check that `metadata_dir` path is correct and contains metadata CSV files

**Problem**: "No experiments found for ChipXX"
- **Solution**: Verify the chip number exists in your metadata files. Check the "Chip number" column.

**Problem**: Incorrect chip names in output
- **Solution**: Adjust the `chip_group_name` parameter to match your naming convention

**Problem**: Missing dates in timeline
- **Solution**: Ensure metadata files have valid timestamps in the `start_time` or `Start time` column

---

## See Also

- `src/timeline.py` - Source code for all timeline functions
- `CLAUDE.md` - Complete codebase documentation
- `README.md` - General project documentation
