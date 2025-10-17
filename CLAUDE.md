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

# Single folder (edit folder_name in src/parser.py first):
python src/parser.py
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
   - **IVg plots**: `plot_ivg_sequence()` shows Id vs Vg curves chronologically
   - **Transconductance plots**: Multiple functions for gm = dI/dVg analysis
     - `plot_ivg_transconductance()` - Uses `np.gradient()` with automatic sweep segmentation
     - `plot_ivg_transconductance_savgol()` - Savitzky-Golay filtered derivatives for smoother curves
     - `plot_ivg_with_transconductance()` - Side-by-side I-V and gm comparison
     - `segment_voltage_sweep()` - Helper that detects forward/reverse sweeps to avoid derivative artifacts
   - **ITS plots**: `plot_its_by_vg()` overlays time series at specific gate voltages
   - **Delta plots**: `plot_its_by_vg_delta()` plots ΔI(t) = I(t) - I(baseline_t) for photoresponse analysis
   - **Wavelength overlays**: `plot_its_wavelength_overlay_delta_for_chip()` compares different laser wavelengths
   - **GIF animation**: `ivg_sequence_gif()` creates animated IVg sequences
   - All functions use `base_dir` (e.g., `Path("raw_data")`) + `source_file` path joining

4. **Batch Processing** (`src/process_day.py`, `src/process_all.py`)
   - Orchestrates figure generation with organized directory structure: `figs/ChipXX_YYYY_MM_DD/IVg|ITS/...`
   - `process_all.py` auto-discovers metadata files and normalizes paths to prevent duplication bugs
   - Key insight: `fix_source_paths()` ensures source_file is always relative to raw_data root

### Supporting Modules

- **Styles** (`src/styles.py`): Matplotlib theme configurations (prism_rain, solar_flare, etc.) using scienceplots
- **Timeline** (`src/timeline.py`): Chronological experiment summaries with `print_day_timeline()`

## Important Conventions

### Procedure Types
- **IVg**: Gate voltage sweep (Id vs Vg characteristic)
- **ITS**: Time series measurement (Id vs time, typically with light ON/OFF cycles)
- **IV**: Source-drain voltage sweep (Id vs Vds)
- **LaserCalibration**: Wavelength calibration measurements

### Session Model
Experiments are grouped into sessions following the pattern: `IVg (pre) → ITS... → IVg (post)`
- Used to track device state changes during stress testing
- `meta["role"]` indicates position: "pre_ivg", "its", "post_ivg"

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
1. Load metadata: `meta = load_and_prepare_metadata(meta_csv, chip)`
2. Set plot style: `set_plot_style('prism_rain')` (optional, uses scienceplots)
3. Redirect output: set `plots.FIG_DIR = Path("desired/dir")`
4. Call plotting functions with `base_dir=Path("raw_data")`
5. Figures saved to `FIG_DIR` with auto-generated descriptive names

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
- **Transconductance warnings**: If seeing numpy divide-by-zero warnings, data likely has duplicate VG values or bidirectional sweeps. The segmentation functions handle this automatically.

### Transconductance Analysis Notes
- **Sweep segmentation**: IVg data with voltage reversals is automatically segmented into monotonic forward/reverse sections
- **Duplicate handling**: Consecutive duplicate VG values are removed before derivative calculation
- **Method choice**:
  - Use `plot_ivg_transconductance()` for quick, standard analysis (np.gradient)
  - Use `plot_ivg_transconductance_savgol()` for smoother curves when data is noisy
  - Use `plot_ivg_with_transconductance()` for detailed single-measurement debugging
- **Units**: Transconductance always plotted in µS (microsiemens) for typical FET values
