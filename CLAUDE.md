# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Utilities for parsing and plotting IV/ITS measurement data from semiconductor device characterization experiments. Processes raw CSV files with embedded metadata to generate organized plots for analysis.

## Commands

### Metadata Generation
```bash
# Generate metadata CSV from raw measurement files
# Mirrored structure (recommended):
python src/parser.py --raw raw_data --out metadata

# Creates metadata/<folder_name>/metadata.csv for each raw_data/<folder_name>/
# Parses #Parameters and #Metadata blocks from CSV headers
```

### Single Day Processing
```bash
# Process one day's experiments with organized output
# Edit METADATA_CSV, BASE_DIR, and CHIPS_TO_PROCESS in src/process_day.py
python src/process_day.py
```

### Batch Processing
```bash
# Process all days automatically
python src/process_all.py --raw raw_data --meta metadata

# Filter specific chips
python src/process_all.py --chips 68 75

# Disable GIFs or overlays
python src/process_all.py --no-gif --no-overlays
```

### Interactive Analysis
```bash
# Launch Jupyter for exploratory analysis
jupyter notebook encap72.ipynb
```
Notebooks (e.g., `encap72.ipynb`, `encap81.ipynb`, `plots.ipynb`) are used for custom plots and one-off analyses.

**Important:** Plots display inline in Jupyter automatically. The plotting module detects Jupyter environment and switches to inline display mode (vs 'Agg' backend used in scripts).

### Chip History Tracking
```bash
# Generate complete experiment history for a specific chip
python example_chip_history.py

# Or use programmatically:
from src.timeline import print_chip_history, generate_all_chip_histories

# Single chip history (saves to Alisson72_history.csv)
print_chip_history(Path("metadata"), Path("raw_data"), chip_number=72, chip_group_name="Alisson")

# All chips automatically (saves AlissonXX_history.csv for each chip)
histories = generate_all_chip_histories(Path("metadata"), Path("raw_data"), min_experiments=5)
```

See `CHIP_HISTORY_GUIDE.md` for detailed documentation.

### Cross-Day Analysis (New!)
```python
# Combine experiments from multiple days for plotting
from pathlib import Path
from src.timeline import print_chip_history
from src.plots import combine_metadata_by_seq, plot_its_overlay, plot_ivg_sequence

# Step 1: View chip history to get seq numbers
print_chip_history(Path("metadata"), Path("."), 67, "Alisson", proc_filter="ITS")
# Output shows: seq=52 (2025-10-15), seq=57 (2025-10-16), seq=58 (2025-10-16)

# Step 2: Combine by seq numbers (NOT file_idx!)
meta = combine_metadata_by_seq(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("."),
    chip=67.0,
    seq_numbers=[52, 57, 58],  # Use seq from history
    chip_group_name="Alisson"
)

# Step 3: Plot with any plotting function
plot_its_overlay(meta, Path("."), "cross_day_analysis", legend_by="led_voltage")
plot_ivg_sequence(meta_ivg, Path("."), "cross_day_ivg")
plot_ivg_transconductance(meta_ivg, Path("."), "cross_day_gm")
```

**Key points:**
- Use `seq` numbers (first column in chip history) for cross-day selection
- `file_idx` repeats across days - only use for single-day filtering
- Works with ALL plot types: ITS, IVg, transconductance, delta plots
- See `CROSS_DAY_ITS_GUIDE.md` and `example_cross_day_its.ipynb` for details

## Code Architecture

### Core Data Pipeline

1. **Metadata Extraction** (`src/parser.py`)
   - Parses CSV header blocks (`#Parameters:`, `#Metadata:`)
   - Extracts experimental parameters: chip number, voltages, laser settings, timestamps
   - Outputs `<folder>_metadata.csv` files
   - Key function: `parse_iv_metadata(csv_path)` returns flat dict of all header fields

2. **Measurement Reading** (`src/utils.py`)
   - `_read_measurement(path)` → polars DataFrame with standardized columns (VG, VSD, I, t, VL)
   - Handles variable CSV formats, detects data start position, normalizes column names
   - `load_and_prepare_metadata(meta_csv, chip)` → filters and enriches metadata with:
     - `proc`: inferred procedure type (IVg, ITS, IV)
     - `session`: groups measurements into IVg → ITS... → IVg blocks
     - `role`: pre_ivg, its, post_ivg for session analysis

3. **Plotting** (`src/plots.py`)
   - **Environment detection**: Automatically uses inline backend in Jupyter, 'Agg' backend in scripts
   - **Cross-day analysis**: `combine_metadata_by_seq()` - NEW! Combines experiments from multiple days
     - Uses `seq` numbers from chip history (unique across all days)
     - Automatically finds correct metadata files for each day
     - Handles schema mismatches between days (uses common columns)
     - Works with ALL plotting functions (ITS, IVg, transconductance)
   - **IVg plots**: `plot_ivg_sequence()` shows Id vs Vg curves chronologically
   - **Transconductance plots**: Multiple functions for gm = dI/dVg analysis
     - `plot_ivg_transconductance()` - Uses `np.gradient()` with automatic sweep segmentation
     - `plot_ivg_transconductance_savgol()` - Savitzky-Golay filtered derivatives for smoother curves
     - `plot_ivg_with_transconductance()` - Side-by-side I-V and gm comparison
     - `segment_voltage_sweep()` - Helper that detects forward/reverse sweeps to avoid derivative artifacts
   - **ITS plots**: `plot_its_by_vg()` overlays time series at specific gate voltages (figsize=(22, 14) for wide time axis)
   - **Delta plots**: `plot_its_by_vg_delta()` plots ΔI(t) = I(t) - I(baseline_t) for photoresponse analysis
   - **Wavelength overlays**: `plot_its_wavelength_overlay_delta_for_chip()` compares different laser wavelengths
   - **GIF animation**: `ivg_sequence_gif()` creates animated IVg sequences
   - All functions use `base_dir` (e.g., `Path("raw_data")`) + `source_file` path joining
   - Output controlled by `plots.FIG_DIR` global variable (set before calling plot functions)

4. **Batch Processing** (`src/process_day.py`, `src/process_all.py`)
   - Orchestrates figure generation with organized directory structure: `figs/ChipXX_YYYY_MM_DD/IVg|ITS/...`
   - `process_all.py` auto-discovers metadata files and normalizes paths to prevent duplication bugs
   - Key insight: `fix_source_paths()` ensures source_file is always relative to raw_data root

### Supporting Modules

- **Styles** (`src/styles.py`): Matplotlib theme configurations (prism_rain, solar_flare, etc.) using scienceplots
- **Timeline** (`src/timeline.py`): Chronological experiment summaries
  - `print_day_timeline()`: Single-day experiment timeline
  - `print_chip_history()`: Complete all-time history for a specific chip
  - `generate_all_chip_histories()`: Automatically generate histories for all chips found in metadata
  - Chip group naming: Configurable prefix (default "Alisson") + chip number

## Important Conventions

### Procedure Types
- **IVg**: Gate voltage sweep (Id vs Vg characteristic)
- **ITS**: Time series measurement (Id vs time, typically with light ON/OFF cycles) - also shows as "It" in timeline
- **IV**: Source-drain voltage sweep (Id vs Vds)
- **LaserCalibration**: Wavelength calibration measurements

### Cross-Day Analysis: seq vs file_idx (Critical!)
- **`seq`**: Sequential experiment number across ALL days (1, 2, 3, ... across entire chip history)
  - **Unique globally** - Use this for cross-day experiment selection
  - First column in `print_chip_history()` output
  - Use with `combine_metadata_by_seq()` function
- **`file_idx`**: File number from CSV filename (e.g., `Alisson67_15.csv` → file_idx=15)
  - **Repeats across days** - Each day has its own #1, #2, etc.
  - Shown as `#N` at end of summary in history output
  - Only use for single-day filtering with `load_and_prepare_metadata()`
- **Common mistake**: Using file_idx for cross-day analysis will select wrong experiments!

Example from chip history:
```
seq  date        file_idx  summary
52   2025-10-15  #1        ITS ... (day 1, file 1) ← Use seq=52
57   2025-10-16  #1        ITS ... (day 2, file 1) ← Use seq=57, NOT #1!
```

### Session Model
Experiments are grouped into sessions following the pattern: `IVg (pre) → ITS... → IVg (post)`
- Used to track device state changes during stress testing
- `meta["role"]` indicates position: "pre_ivg", "its", "post_ivg"
- Session assignment logic in `load_and_prepare_metadata()`:
  - First IVg starts a new session as "pre_ivg"
  - ITS measurements continue the current session
  - Next IVg after ITS becomes "post_ivg" and closes the session
  - Back-to-back IVg measurements each start new sessions

### Path Handling (Critical!)
- Raw CSV files expected in `raw_data/<day>/` structure (e.g., `raw_data/Alisson_15_sept/`)
- Metadata `source_file` column must be relative to `raw_data/` root (not absolute)
- Plotters receive `base_dir` parameter (typically `Path("raw_data")`) and join with `source_file`
- `process_all.py` includes `fix_source_paths()` to normalize paths and prevent duplication bugs like `raw_data/raw_data/...`
- Path bugs are a common source of "file not found" errors

### Column Standardization
Raw CSVs have varying column names. `_std_rename()` in `src/utils.py` standardizes to:
- `VG`: Gate voltage (from: "Gate", "gate v", "Gate voltage")
- `VSD` or `VDS`: Source-drain voltage (from: "vds", "drain-source", "v")
- `I`: Current (from: "id", "current")
- `t`: Time (from: "time", "t s")
- `VL`: Laser voltage (from: "laser", "laser v")

### Plotting Workflow

#### Single-Day Analysis
1. Load metadata: `meta = load_and_prepare_metadata(meta_csv, chip)`
2. Filter by file_idx: `meta.filter(pl.col("file_idx").is_in([1, 2, 3]))`
3. Set plot style: `set_plot_style('prism_rain')` (optional)
4. Plot: `plot_its_overlay(meta, Path("."), "tag", legend_by="led_voltage")`

#### Cross-Day Analysis (Multiple Days)
1. View history: `print_chip_history(Path("metadata"), Path("."), chip, "Alisson", proc_filter="ITS")`
2. Note seq numbers from first column (e.g., 52, 57, 58)
3. Combine: `meta = combine_metadata_by_seq(Path("metadata"), Path("."), chip, [52, 57, 58], "Alisson")`
4. Plot: Works with ANY plot function (ITS, IVg, transconductance)

**Figure Size Convention:**
- IVg plots: (20, 20) - square format for gate sweeps
- ITS plots: (22, 14) - wide format for time series data
- Override in individual plot functions if needed

## Data Structure

Raw CSV format:
```
#Parameters:
#	Chip number: 72
#	VG: -3.0
#	Laser voltage: 3.5
#	Laser wavelength: 455.0
#Metadata:
#	Start time: 1726394856.2
#Data:
VG (V),I (A),t (s)
-3.0,1.23e-8,0.0
...
```

Metadata CSV columns (sample):
- `Chip number`, `VG`, `VDS`, `Laser voltage`, `Laser wavelength`
- `source_file`: path to raw CSV
- `start_time`: Unix timestamp
- `time_hms`: "HH:MM:SS" for timeline display

## Development Notes

### Environment Setup
- Python 3.10+ required
- Install dependencies: `pip install -r requirements.txt`
- Virtual environment at `.venv/` (recommended)

### Key Dependencies
- `polars>=0.19.0` - Fast dataframe operations with lazy evaluation
- `numpy>=1.24.0` - Numerical computing
- `scipy` - Signal processing (Savitzky-Golay filtering for transconductance)
- `matplotlib>=3.7.0` + `scienceplots>=2.0.0` - Plotting with publication-ready styles
- `imageio>=2.28.0` + `Pillow>=10.0.0` - GIF animation generation
- `jupyter>=1.0.0` - Interactive notebooks (optional)

### Common Issues
- **Missing files**: Check that `source_file` paths in metadata are relative to `raw_data/`
- **Column errors**: Ensure raw CSVs have proper headers; column name normalization is case-insensitive
- **GIF failures**: Verify `imageio` and `Pillow` versions; falls back to saving individual frames
- **Empty plots**: Verify chip numbers match between metadata and filter arguments
- **Wrong experiments in cross-day plot**: Using file_idx instead of seq! Always use `seq` from `print_chip_history()` for cross-day analysis
- **Schema mismatch errors**: `combine_metadata_by_seq()` handles this automatically by using only common columns
- **Transconductance warnings**: If seeing numpy divide-by-zero warnings, data likely has duplicate VG values or bidirectional sweeps. The segmentation functions handle this automatically.
- **Jupyter display issues**: Plots should display inline automatically. If not, check that you're not manually setting matplotlib backend after importing plots module.
- **Y-axis padding issues in ITS plots**: Padding is calculated from visible data only (after PLOT_START_TIME=20s). Y-limits applied twice for Jupyter compatibility.

### Transconductance Analysis Notes
- **Sweep segmentation**: IVg data with voltage reversals is automatically segmented into monotonic forward/reverse sections
- **Duplicate handling**: Consecutive duplicate VG values are removed before derivative calculation
- **Method choice**:
  - Use `plot_ivg_transconductance()` for quick, standard analysis (np.gradient)
  - Use `plot_ivg_transconductance_savgol()` for smoother curves when data is noisy
  - Use `plot_ivg_with_transconductance()` for detailed single-measurement debugging
- **Units**: Transconductance always plotted in µS (microsiemens) for typical FET values

## Documentation Files

- **`README.md`**: User-facing project overview and quick start guide
- **`CLAUDE.md`**: This file - technical reference for AI assistants
- **`CHIP_HISTORY_GUIDE.md`**: Complete guide for using chip history timeline functions
- **`CROSS_DAY_ITS_GUIDE.md`**: Quick reference for cross-day analysis workflow (ITS, IVg, transconductance)
- **`example_chip_history.py`**: Example script demonstrating chip history functions
- **`example_cross_day_its.ipynb`**: Interactive notebook with cross-day plotting examples
- **`requirements.txt`**: Python package dependencies

## Recent Additions (2025-10)

### Cross-Day Analysis Feature
- **Function**: `combine_metadata_by_seq()` in `src/plots.py`
- **Purpose**: Combine experiments from multiple days for unified plotting
- **Key innovation**: Uses `seq` numbers from chip history (globally unique) instead of `file_idx` (repeats across days)
- **Works with**: All plot types (ITS overlay, IVg sequence, transconductance, delta plots)
- **Automatic handling**: Schema mismatches between days, metadata file discovery, chronological sorting

### ITS Plot Improvements
- **Figure size**: Changed from (40, 35) to (22, 14) for better aspect ratio
- **Y-axis padding**: Fixed to calculate from visible data only (after PLOT_START_TIME=20s)
- **Jupyter compatibility**: Y-limits applied twice to prevent tight_layout from resetting

### Style Updates
- **Legend font**: Reduced from 35 to 30 for better fit in plots
- **Theme**: prism_rain remains default with optimized sizing
