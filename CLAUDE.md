# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Utilities for parsing and plotting IV/ITS measurement data from semiconductor device characterization experiments. Processes raw CSV files with embedded metadata to generate organized plots for analysis.

## User Interfaces

### TUI (Terminal User Interface) - Recommended for Lab Members

```bash
# Launch the interactive plotting assistant
python tui_app.py
```

**Features:**
- 🎨 Beautiful guided wizard interface (Tokyo Night theme)
- 🧭 Step-by-step plot generation workflow
- ⌨️ Full keyboard navigation (arrows, tab, enter)
- 🔄 Real-time progress tracking
- 📊 Interactive experiment selection from chip history
- 🎯 Quick workflow for multiple plots

**Perfect for:**
- Lab members who prefer visual interfaces
- Quick plot generation without remembering CLI syntax
- Exploring available chips and experiments
- Generating multiple plots of the same type

See **`TUI_GUIDE.md`** for complete documentation.

### CLI (Command Line Interface) - For Scripts and Automation

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

### TUI Architecture (Textual Framework)

The TUI is built with [Textual 6.3.0](https://textual.textualize.io/), a modern Python framework for terminal user interfaces.

**Main Components:**

1. **Application (`src/tui/app.py`)**
   - `PlotterApp` - Main app class managing screen stack and global config
   - Tokyo Night theme with focus indicators
   - Global keyboard shortcuts (Ctrl+Q to quit)
   - Shared state via `plot_config` dictionary

2. **Screens (`src/tui/screens/`)**
   - `MainMenuScreen` - Entry point with main actions (New Plot, Recent Configs, Process Data)
   - `ChipSelectorScreen` - Auto-discover chips from metadata
   - `PlotTypeSelectorScreen` - Choose ITS/IVg/Transconductance
   - `ConfigModeSelectorScreen` - Choose Quick (defaults) vs Custom (full config)
   - `RecentConfigsScreen` - Load, view, export, import, delete saved configurations
   - `ExperimentSelectorScreen` - Interactive multi-select from chip history
   - `ITSConfigScreen` / `IVgConfigScreen` / `TransconductanceConfigScreen` - Custom configuration screens
   - `PreviewScreen` - Review config before generation
   - `PlotGenerationScreen` - Real-time progress with background threading
   - `PlotSuccessScreen` / `PlotErrorScreen` - Results and error handling with retry/edit options
   - `ProcessConfirmationScreen` / `ProcessLoadingScreen` / `ProcessSuccessScreen` / `ProcessErrorScreen` - Metadata generation workflow

3. **Key Patterns**
   - **Screen Navigation**: Stack-based with `push_screen()` / `pop_screen()`
   - **Focus Management**: Custom arrow key handlers + CSS `:focus` styling
   - **Background Threading**: Plot generation runs in daemon thread with `call_from_thread()` for UI updates
   - **State Passing**: Constructor params + global `plot_config` dict
   - **Visual Feedback**: Arrow indicators (→), color changes, bold text on focus

3. **Supporting Modules**
   - `ConfigManager` (`src/tui/config_manager.py`) - Configuration persistence
     - Save/load plot configurations
     - Auto-generate descriptions
     - Export/import configs as JSON
     - Search and statistics
   - `src/tui/utils.py` - TUI utility functions
   - `src/tui/widgets/` - Custom widgets (if any)

**Critical TUI Implementation Details:**

- **Thread Safety**: NEVER update UI from background thread directly
  - ❌ `self.call_from_thread()` (AttributeError - Screen doesn't have this)
  - ✅ `self.app.call_from_thread()` (App has this method)
- **Screen Stack**: Base screen (0) + MainMenuScreen (1) + wizard screens (2+)
  - Return to menu: `while len(stack) > 2: pop_screen()`
- **Focus Styling**: Use CSS `:focus` pseudo-class + `on_button_focus()` for arrows
- **Arrow Navigation**: Implement `on_key()` handler with `event.prevent_default()`
- **Button Variants**: Use `variant="default"` for uniform styling (not "primary")
- **Config Persistence**: Automatically save successful plot configs via `ConfigManager`
  - Saved after successful plot generation in `PlotSuccessScreen`
  - Config includes all parameters: chip, plot type, filters, legend settings
  - Stored in `~/.lab_plotter_configs.json`

**Entry Point:** `tui_app.py` - Launches PlotterApp with default paths

**Configuration Persistence:**
- **`ConfigManager`** (`src/tui/config_manager.py`) - Manages saved plot configurations
  - Stores configurations as JSON in `~/.lab_plotter_configs.json`
  - Auto-generates descriptions from config parameters
  - Supports export/import of individual configs
  - Maximum 20 recent configs (configurable)
  - Search by description or parameters
- **Recent Configurations** - Load and reuse previous plot settings
  - Access via Main Menu → "Recent Configurations"
  - View all saved configs in sortable table
  - Load config directly to preview screen
  - Export/import configs as JSON files
  - Delete unwanted configs

**Configuration Modes:**
- **Quick Plot** - Smart defaults, just select experiments interactively
  - Goes directly to experiment selector with multi-select table
  - Uses sensible defaults for all parameters
  - Best for routine plotting
- **Custom Plot** - Full parameter control
  - ITS: baseline, padding, filters, legend style
  - IVg: VDS filter, date filter, selection mode
  - Transconductance: method (gradient/savgol), savgol parameters, filters
  - All validations with user-friendly error messages

See **`TUI_GUIDE.md`** for complete TUI documentation including:
- Wizard workflow (now 8 steps with config mode selection)
- Keyboard navigation reference
- Configuration persistence guide
- Focus management patterns
- Background threading guide
- Troubleshooting common issues

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
   - **ITS plots**: `plot_its_overlay()` and `plot_its_dark()` for time series analysis
     - Four baseline correction modes:
       - `baseline_mode="fixed"` with `baseline_t=60.0`: Standard interpolation at specific time
       - `baseline_mode="fixed"` with `baseline_t=0.0`: Subtract first visible point (avoids CSV artifacts)
       - `baseline_mode="auto"`: Calculate from LED ON+OFF period metadata
       - `baseline_mode="none"`: Raw data (no correction), adds `_raw` suffix to filename
     - `plot_start_time` parameter controls visible x-axis range (default 20s for light, 1s for dark)
     - Baseline at t=0 uses first point ≥ `plot_start_time` to avoid measurement artifacts
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

**Core Analysis:**
- `polars>=0.19.0` - Fast dataframe operations with lazy evaluation
- `numpy>=1.24.0` - Numerical computing
- `scipy>=1.11.0` - Signal processing (Savitzky-Golay filtering for transconductance)
- `matplotlib>=3.7.0` + `scienceplots>=2.0.0` - Plotting with publication-ready styles
- `imageio>=2.28.0` + `Pillow>=10.0.0` - GIF animation generation

**CLI:**
- `typer>=0.9.0` - Command-line interface framework
- `rich>=13.0.0` - Rich terminal output (tables, progress bars, styling)

**TUI:**
- `textual==6.3.0` - Terminal user interface framework
- `rich>=13.0.0` - Rich text and formatting (used by Textual)

**Optional:**
- `ipython>=8.0.0` - Enhanced Python shell
- `jupyter>=1.0.0` - Interactive notebooks for exploratory analysis

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
- **`TUI_GUIDE.md`**: **NEW!** Complete TUI documentation (wizard flow, keyboard nav, troubleshooting)
- **`CHIP_HISTORY_GUIDE.md`**: Complete guide for using chip history timeline functions
- **`CROSS_DAY_ITS_GUIDE.md`**: Quick reference for cross-day analysis workflow (ITS, IVg, transconductance)
- **`example_chip_history.py`**: Example script demonstrating chip history functions
- **`example_cross_day_its.ipynb`**: Interactive notebook with cross-day plotting examples
- **`requirements.txt`**: Python package dependencies

## Recent Additions (2025-10)

### TUI Implementation (Oct 2025)
- **Framework**: Textual 0.60.0 with Tokyo Night theme
- **Features**:
  - Complete wizard workflow for plot generation (7 screens)
  - Interactive experiment selection with multi-select DataTable
  - Real-time progress tracking with background threading
  - Full keyboard navigation (arrows, tab, enter, escape)
  - Visual focus indicators (color change, arrows, bold text)
  - "Plot Another" quick workflow for batch plotting
  - Process new data dialog for metadata generation
- **Technical achievements**:
  - Thread-safe UI updates via `app.call_from_thread()`
  - Custom arrow key navigation with CSS `:focus` styling
  - Stack-based screen navigation with proper state management
  - Lazy matplotlib initialization for background threads
  - Dynamic button labels with arrow indicators (→)
- **Documentation**: Complete guide in `TUI_GUIDE.md`

### Cross-Day Analysis Feature (Sep 2025)
- **Function**: `combine_metadata_by_seq()` in `src/plots.py`
- **Purpose**: Combine experiments from multiple days for unified plotting
- **Key innovation**: Uses `seq` numbers from chip history (globally unique) instead of `file_idx` (repeats across days)
- **Works with**: All plot types (ITS overlay, IVg sequence, transconductance, delta plots)
- **Automatic handling**: Schema mismatches between days, metadata file discovery, chronological sorting

### ITS Baseline System Overhaul (Oct 2025)
- **Four baseline modes** for flexible data analysis:
  - **Raw data mode** (`baseline_mode="none"`): Plots CSV data exactly as recorded
    - Checkbox unchecked in TUI
    - Adds `_raw` suffix to filename (e.g., `encap67_ITS_52_raw.png`)
    - No correction applied - true raw data for noise/drift analysis
  - **Baseline at t=0** (`baseline_t=0.0`): Subtract first visible point
    - Checkbox checked + enter "0"
    - Uses first point at `plot_start_time` to avoid CSV artifacts
    - Each trace starts at y≈0 for comparative analysis
  - **Fixed baseline** (`baseline_t=60.0`): Standard interpolation at specific time
    - Checkbox checked + enter time value
    - Traditional baseline correction method
  - **Auto baseline** (`baseline_mode="auto"`): Calculate from LED period
    - Checkbox checked + leave empty
    - Smart baseline = (ON+OFF period) / 2
- **Smart first-point handling**: `baseline_t=0` now uses first point ≥ `plot_start_time` instead of very first CSV row
  - Avoids measurement artifacts in first ~1 second
  - Dark preset uses plot_start_time=1.0s, Light presets use 20.0s
- **Filename differentiation**: Raw plots automatically get `_raw` suffix to prevent overwriting
- **TUI Integration**: Checkbox toggle for baseline enable/disable with input field
- **Backward compatible**: All existing code continues to work with new defaults

### ITS Plot Improvements (Sep 2025)
- **Figure size**: Changed from (40, 35) to (22, 14) for better aspect ratio
- **Y-axis padding**: Fixed to calculate from visible data only (after PLOT_START_TIME=20s)
- **Jupyter compatibility**: Y-limits applied twice to prevent tight_layout from resetting

### Style Updates (Sep 2025)
- **Legend font**: Reduced from 35 to 30 for better fit in plots
- **Theme**: prism_rain remains default with optimized sizing
