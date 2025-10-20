# plots.py Function Analysis for CLI Plotting Workflow

## Overview

This document analyzes all 50+ functions in `src/plots.py` to determine which are needed for the planned CLI plotting commands: `plot-its`, `plot-ivg`, and `plot-transconductance`.

**Total Functions Analyzed**: ~50 functions across 2250 lines

---

## Executive Summary

### ESSENTIAL Functions (Must Use in CLI)
These are the core plotting functions that will be called directly by CLI commands:

1. **`plot_its_overlay()`** - Main ITS plotting function for `plot-its` command
2. **`plot_ivg_sequence()`** - Main IVg plotting function for `plot-ivg` command
3. **`plot_ivg_transconductance()`** - Transconductance with gradient method for `plot-transconductance` command
4. **`plot_ivg_transconductance_savgol()`** - Transconductance with Savitzky-Golay filter for `plot-transconductance --method savgol`
5. **`combine_metadata_by_seq()`** - CRITICAL for cross-day experiment selection (recently added)
6. **`load_and_prepare_metadata()`** - Loads and enriches metadata with proc, session, role

### UTILITY Functions (Needed by Essential Functions)
These are helper functions that essential functions depend on:

7. **`_read_measurement()`** - Reads CSV measurement files (from utils.py)
8. **`get_chip_label()`** - Extracts chip number for plot titles/filenames
9. **`detect_light_on_window()`** - Detects light ON period for shading
10. **`calculate_light_window()`** - Calculates light ON window for shading
11. **`interpolate_baseline()`** - Baseline correction for ITS plots
12. **`sanitize_value_for_filename()`** - Safe filename generation
13. **`segment_voltage_sweep()`** - Segments IVg data by sweep direction
14. **`calculate_transconductance()`** - Basic gm calculation (np.gradient)
15. **`_savgol_derivative_corrected()`** - Savitzky-Golay derivative for savgol method
16. **`_raw_derivative()`** - Raw derivative using np.gradient

### OPTIONAL Functions (Advanced Features)
Could be used for enhanced CLI features later:

17. **`plot_its_by_vg()`** - Group ITS by gate voltage (more complex than overlay)
18. **`plot_its_by_vg_delta()`** - ITS with baseline subtraction grouped by VG
19. **`plot_its_wavelength_overlay_delta()`** - ITS comparison by wavelength
20. **`plot_ivg_with_transconductance()`** - Side-by-side I-V and gm plots
21. **`plot_savgol_comparison()`** - Debugging tool for transconductance methods
22. **`ivg_sequence_gif()`** - Animated GIF generation (could be `plot-gif` command)

### NOT NEEDED for CLI
Functions specific to batch processing, debugging, or special workflows:

23. **`plot_ivg_last_of_day1_vs_first_of_day2()`** - Day-to-day comparison (too specific)
24. **`set_its_figsize()`** - Jupyter-only configuration
25. **`_setup_matplotlib_backend()`** - Already runs on import
26. **All helper extraction functions** - Used internally by plot_its_overlay

---

## Detailed Function Analysis

### 1. Backend & Configuration Functions

#### `_setup_matplotlib_backend()`
**Lines**: 25-36
**Purpose**: Auto-detects environment (Jupyter vs script) and sets appropriate matplotlib backend
**Status**: ⚙️ **RUNS AUTOMATICALLY** - Executes on module import, no CLI action needed
**CLI Need**: None - already handled

#### `set_its_figsize()`
**Lines**: 67-78
**Purpose**: Sets figure size for ITS plots in Jupyter notebooks to (40, 35)
**Status**: 🚫 **NOT NEEDED** - Jupyter-only feature
**CLI Need**: None - CLI will use default or command-line specified sizes

---

### 2. Core Metadata & Data Loading

#### `load_and_prepare_metadata()` ⭐
**Lines**: 393-463
**Purpose**: Loads metadata CSV, filters by chip, infers procedure type, assigns sessions
**Returns**: Polars DataFrame with enriched metadata (proc, file_idx, session, role)
**Status**: ✅ **ESSENTIAL** - Required by ALL plotting functions
**CLI Need**: **HIGH** - Called by all three CLI commands to load experiment metadata

**Key Features**:
- Normalizes column names
- Filters by chip number
- Infers procedure (IVg, ITS, IV) from filename
- Assigns session IDs (IVg → ITS → IVg blocks)
- Adds `role` field (pre_ivg, its, post_ivg)

#### `combine_metadata_by_seq()` ⭐⭐⭐
**Lines**: 250-390
**Purpose**: Combines experiments from multiple days using seq numbers from chip history
**Returns**: Combined Polars DataFrame from multiple days
**Status**: ✅ **CRITICAL** - Core cross-day analysis function
**CLI Need**: **CRITICAL** - Primary way to select experiments for cross-day plotting

**Workflow**:
1. Builds chip history using `build_chip_history()`
2. Filters by requested seq numbers
3. Groups by day folder
4. Loads metadata for each day
5. Aligns schemas (finds common columns)
6. Concatenates and sorts chronologically

**Why Critical**: This is the breakthrough function that enables cross-day plotting by seq numbers instead of file_idx.

---

### 3. Helper Functions (Utilities)

#### `detect_light_on_window()`
**Lines**: 85-109
**Purpose**: Detects light ON period from VL column in measurement data
**Returns**: (start_time, end_time) or (None, None)
**Status**: 🔧 **UTILITY** - Used by ITS plotting functions
**CLI Need**: Medium - Used for light window shading in ITS plots

#### `interpolate_baseline()`
**Lines**: 111-128
**Purpose**: Interpolates current at baseline_t for baseline correction
**Returns**: float (baseline current value)
**Status**: 🔧 **UTILITY** - Used by ITS delta plots
**CLI Need**: Medium - Used by plot_its_overlay for baseline correction

#### `sanitize_value_for_filename()`
**Lines**: 130-136
**Purpose**: Converts numeric values to filename-safe strings (e.g., -3.0 → "m3p0")
**Returns**: Safe filename string
**Status**: 🔧 **UTILITY** - Filename generation
**CLI Need**: Low - Could use simpler filename scheme in CLI

#### `get_chip_label()`
**Lines**: 138-147
**Purpose**: Extracts chip number from DataFrame for labeling (tries multiple column names)
**Returns**: String like "Chip67"
**Status**: 🔧 **UTILITY** - Plot titles and filenames
**CLI Need**: High - Clean way to get chip labels

#### `sort_time_series()`
**Lines**: 149-156
**Purpose**: Sorts time array and corresponding data arrays by time
**Returns**: Tuple of sorted arrays
**Status**: 🔧 **UTILITY** - Data preparation
**CLI Need**: Low - Used internally, could be helpful

#### `calculate_light_window()`
**Lines**: 220-248
**Purpose**: Calculates light ON window using VL detection, metadata, or fallback
**Returns**: (t0, t1) for shading
**Status**: 🔧 **UTILITY** - Light window calculation
**CLI Need**: Medium - Used by ITS plotting

#### `load_trace_data()`
**Lines**: 198-218
**Purpose**: Loads measurement trace with validation (checks required columns exist)
**Returns**: Polars DataFrame or None
**Status**: 🔧 **UTILITY** - Safe data loading
**CLI Need**: Low - `_read_measurement()` is simpler

---

### 4. Transconductance Calculation Functions

#### `calculate_transconductance()` ⭐
**Lines**: 158-196
**Purpose**: Calculate dI/dVg using central differences (np.gradient)
**Returns**: (vg_gm, gm) arrays
**Status**: ✅ **ESSENTIAL** - Used by gradient transconductance method
**CLI Need**: High - Core function for `plot-transconductance` (gradient method)

**Features**:
- Handles duplicate VG values by averaging
- Removes NaN/Inf values
- Uses numpy gradient (central differences)

#### `_savgol_derivative_corrected()`
**Lines**: 492-534
**Purpose**: Calculate dI/dVg using Savitzky-Golay filter (smoother)
**Returns**: gm array (filtered derivative)
**Status**: ✅ **ESSENTIAL** - Used by savgol transconductance method
**CLI Need**: High - Core function for `plot-transconductance --method savgol`

**Key Fix**: Preserves sign of delta for correct reverse sweep derivatives

#### `_raw_derivative()`
**Lines**: 536-542
**Purpose**: Raw derivative using np.gradient (for comparison/debugging)
**Returns**: gm array
**Status**: 🔧 **UTILITY** - Debugging/comparison
**CLI Need**: Low - Used internally by savgol comparison plots

#### `calculate_transconductance_smooth()`
**Lines**: 638-698
**Purpose**: Calculate gm with smoothing (gradient or diff method + moving average)
**Returns**: (vg_gm, gm) arrays
**Status**: ⚠️ **DUPLICATE** - Overlaps with calculate_transconductance
**CLI Need**: Low - Redundant with other functions

#### `segment_voltage_sweep()` ⭐
**Lines**: 465-490, 576-636 (duplicate definition)
**Purpose**: Segments voltage sweep into monotonic sections (forward/reverse)
**Returns**: List of (vg_segment, i_segment, direction) tuples
**Status**: 🔧 **UTILITY** - Critical for transconductance
**CLI Need**: High - Prevents derivative artifacts at sweep reversals

**Note**: Function is defined twice (code smell, but both are identical)

---

### 5. Main IVg Plotting Functions

#### `plot_ivg_sequence()` ⭐⭐
**Lines**: 548-574
**Purpose**: Plot all IVg measurements chronologically (Id vs Vg)
**Output**: Single PNG with all IVg curves overlaid
**Status**: ✅ **ESSENTIAL** - Main function for `plot-ivg` command
**CLI Need**: **CRITICAL** - Direct call from `plot-ivg` CLI command

**Features**:
- Plots all IVg in chronological order
- Labels show file_idx and light/dark status
- Auto-scales y-axis (with ylim bottom=0)
- Uses metadata to determine light status

#### `plot_ivg_transconductance()` ⭐⭐
**Lines**: 700-805
**Purpose**: Plot transconductance (dI/dVg) for all IVg using numpy.gradient
**Output**: Single PNG with all gm curves
**Status**: ✅ **ESSENTIAL** - Main function for `plot-transconductance` (gradient method)
**CLI Need**: **CRITICAL** - Default method for `plot-transconductance` command

**Features**:
- Segments sweeps to avoid reversal artifacts
- Uses np.gradient per segment (matches PyQtGraph)
- Joins segments with NaN separators
- Shows gm in µS units
- Handles duplicate VG values

#### `plot_ivg_transconductance_savgol()` ⭐⭐
**Lines**: 1990-2148
**Purpose**: Plot transconductance using Savitzky-Golay filter (smoother curves)
**Output**: Single PNG with filtered gm curves
**Status**: ✅ **ESSENTIAL** - Savgol method for `plot-transconductance --method savgol`
**CLI Need**: **HIGH** - Alternative method for transconductance

**Features**:
- Optionally shows raw derivative as transparent background
- Uses corrected Savitzky-Golay derivative
- Auto-adjusts window length if needed
- Respects matplotlib color cycle

#### `plot_ivg_with_transconductance()`
**Lines**: 807-915
**Purpose**: Side-by-side I-V and gm plots for a single measurement
**Output**: PNG with 2 subplots (I-V and gm)
**Status**: 💡 **OPTIONAL** - Debugging/detailed analysis
**CLI Need**: Low - Could be future enhancement (e.g., `--detailed` flag)

---

### 6. Main ITS Plotting Functions

#### `plot_its_overlay()` ⭐⭐⭐
**Lines**: 1675-1988
**Purpose**: Overlay ITS traces with baseline correction at baseline_t
**Output**: Single PNG with all ITS traces overlaid
**Status**: ✅ **ESSENTIAL** - Main function for `plot-its` command
**CLI Need**: **CRITICAL** - Direct call from `plot-its` CLI command

**Key Parameters**:
- `baseline_t`: Time point for baseline correction (default 60.0s)
- `legend_by`: How to label curves ("wavelength", "vg", "led_voltage")
- `padding`: Y-axis padding fraction (default 0.02)

**Features**:
- Baseline subtraction: ΔI(t) = I(t) - I(baseline_t)
- Flexible legend labeling (wavelength, VG, or LED voltage)
- Auto-detects light ON window for shading
- Smart y-axis padding based on visible data only (after PLOT_START_TIME)
- Handles metadata from multiple days seamlessly

**Why Critical**: This is THE function for ITS plotting in the CLI. It's simple, powerful, and already handles all the complexity.

#### `plot_its_by_vg()`
**Lines**: 917-1078
**Purpose**: Overlay ITS traces grouped by (Vg, wavelength) from metadata
**Output**: Multiple PNGs (one per VG/wavelength combination)
**Status**: 💡 **OPTIONAL** - More complex than overlay
**CLI Need**: Low - `plot_its_overlay` is simpler and more flexible

**Difference from plot_its_overlay**:
- Groups by VG and wavelength automatically
- Creates separate figures for each combination
- More automated but less flexible

#### `plot_its_by_vg_delta()`
**Lines**: 1139-1322
**Purpose**: Overlay ITS traces with baseline subtraction, grouped by (Vg, wavelength)
**Output**: Multiple PNGs
**Status**: 💡 **OPTIONAL** - Similar to plot_its_overlay but with auto-grouping
**CLI Need**: Low - `plot_its_overlay` already does baseline subtraction

#### `plot_its_wavelength_overlay_delta()`
**Lines**: 1334-1498
**Purpose**: Overlay ITS traces (ΔI) comparing different wavelengths
**Output**: Single PNG with wavelength comparison
**Status**: 💡 **OPTIONAL** - Specialized wavelength comparison
**CLI Need**: Medium - Could be useful for `--wavelength-compare` flag

**Features**:
- Can ignore VG constraint
- Flexible filtering (include_idx, exclude_idx)
- Label deduplication
- Custom title/filename suffixes

#### `plot_its_wavelength_overlay_delta_for_chip()`
**Lines**: 1500-1551
**Purpose**: Convenience wrapper for wavelength overlay, filters to one chip
**Status**: 💡 **OPTIONAL** - Just a wrapper
**CLI Need**: Low - CLI already filters by chip

---

### 7. Specialized Plotting Functions

#### `plot_ivg_last_of_day1_vs_first_of_day2()`
**Lines**: 1080-1137
**Purpose**: Compare last IVg of day 1 vs first IVg of day 2
**Output**: PNG with 2 curves
**Status**: 🚫 **NOT NEEDED** - Too specific for general CLI
**CLI Need**: None - Very specific use case

#### `ivg_sequence_gif()` ⭐
**Lines**: 1553-1673
**Purpose**: Create animated GIF from IVg sequence
**Output**: Animated GIF file
**Status**: 💡 **OPTIONAL** - Could be future `plot-gif` command
**CLI Need**: Medium - Nice-to-have feature

**Features**:
- Cumulative or single-frame mode
- Adjustable FPS
- Global axis limits across all frames
- Uses PIL for reliable GIF generation

#### `plot_savgol_comparison()` ⭐
**Lines**: 2150-2249
**Purpose**: Compare raw vs filtered transconductance (debugging)
**Output**: PNG with 3 subplots (I-V, raw gm, filtered gm)
**Status**: 💡 **OPTIONAL** - Debugging tool
**CLI Need**: Low - Could be `--debug` or `--compare` flag

---

### 8. Helper Extraction Functions (Internal)

These functions are used internally by `plot_its_overlay()` to extract metadata:

#### `_get_wavelength_nm()`
**Lines**: 1714-1736 (inside plot_its_overlay)
**Purpose**: Extract wavelength from metadata row (tries multiple column names)
**Status**: 🔧 **INTERNAL** - Used by plot_its_overlay
**CLI Need**: None - internal helper

#### `_get_vg_V()`
**Lines**: 1739-1781 (inside plot_its_overlay)
**Purpose**: Extract gate voltage from metadata or data trace
**Status**: 🔧 **INTERNAL** - Used by plot_its_overlay
**CLI Need**: None - internal helper

#### `_get_led_voltage_V()`
**Lines**: 1784-1817 (inside plot_its_overlay)
**Purpose**: Extract LED/laser voltage from metadata
**Status**: 🔧 **INTERNAL** - Used by plot_its_overlay
**CLI Need**: None - internal helper

#### `_first_chip_label()`
**Lines**: 1324-1332
**Purpose**: Extract chip label from DataFrame (simpler than get_chip_label)
**Status**: 🔧 **UTILITY** - Redundant with get_chip_label
**CLI Need**: Low - get_chip_label is better

---

## Conclusions & Recommendations

### For `plot-its` Command

**Required Functions**:
1. ✅ `combine_metadata_by_seq()` - Select experiments by seq numbers
2. ✅ `plot_its_overlay()` - Main plotting function
3. 🔧 `get_chip_label()` - Chip labels
4. 🔧 `detect_light_on_window()` - Light shading (used internally)
5. 🔧 `calculate_light_window()` - Light shading (used internally)

**CLI Workflow**:
```python
# Step 1: Get metadata by seq numbers
meta = combine_metadata_by_seq(
    metadata_dir, raw_data_dir, chip, seq_numbers, chip_group
)

# Step 2: Plot
plot_its_overlay(
    meta, raw_data_dir, tag,
    baseline_t=60.0,
    legend_by="led_voltage",  # or "wavelength", "vg"
    padding=0.05
)
```

**Optional Enhancements**:
- `--wavelength-compare` flag → use `plot_its_wavelength_overlay_delta()`
- `--group-by-vg` flag → use `plot_its_by_vg()`

---

### For `plot-ivg` Command

**Required Functions**:
1. ✅ `combine_metadata_by_seq()` - Select experiments
2. ✅ `plot_ivg_sequence()` - Main plotting function
3. 🔧 `get_chip_label()` - Chip labels

**CLI Workflow**:
```python
# Step 1: Get metadata
meta = combine_metadata_by_seq(
    metadata_dir, raw_data_dir, chip, seq_numbers, chip_group
)

# Step 2: Plot
plot_ivg_sequence(meta, raw_data_dir, tag)
```

**Optional Enhancements**:
- `--gif` flag → use `ivg_sequence_gif()`
- `--detailed` flag → use `plot_ivg_with_transconductance()`

---

### For `plot-transconductance` Command

**Required Functions**:
1. ✅ `combine_metadata_by_seq()` - Select experiments
2. ✅ `plot_ivg_transconductance()` - Gradient method (DEFAULT)
3. ✅ `plot_ivg_transconductance_savgol()` - Savgol method (--method savgol)
4. 🔧 `segment_voltage_sweep()` - Sweep segmentation (used internally)
5. 🔧 `calculate_transconductance()` - Core gm calculation (gradient)
6. 🔧 `_savgol_derivative_corrected()` - Savgol derivative
7. 🔧 `get_chip_label()` - Chip labels

**CLI Workflow**:
```python
# Step 1: Get metadata (MUST be IVg experiments)
meta = combine_metadata_by_seq(
    metadata_dir, raw_data_dir, chip, seq_numbers, chip_group
)

# Validate: ensure all are IVg
if not all(meta["proc"] == "IVg"):
    raise ValueError("All experiments must be IVg for transconductance")

# Step 2: Plot based on method
if method == "gradient":
    plot_ivg_transconductance(meta, raw_data_dir, tag)
elif method == "savgol":
    plot_ivg_transconductance_savgol(
        meta, raw_data_dir, tag,
        window_length=9, polyorder=3
    )
```

**Optional Enhancements**:
- `--compare` flag → use `plot_savgol_comparison()` for debugging
- `--detailed` flag → use `plot_ivg_with_transconductance()`

---

## Summary Table

| Function | ITS | IVg | Gm | Priority | Notes |
|----------|-----|-----|----|----------|-------|
| `combine_metadata_by_seq()` | ✅ | ✅ | ✅ | **CRITICAL** | Cross-day selection |
| `plot_its_overlay()` | ✅ | ❌ | ❌ | **CRITICAL** | Main ITS function |
| `plot_ivg_sequence()` | ❌ | ✅ | ❌ | **CRITICAL** | Main IVg function |
| `plot_ivg_transconductance()` | ❌ | ❌ | ✅ | **CRITICAL** | Gradient method |
| `plot_ivg_transconductance_savgol()` | ❌ | ❌ | ✅ | **HIGH** | Savgol method |
| `load_and_prepare_metadata()` | 🔧 | 🔧 | 🔧 | **HIGH** | Used by combine |
| `get_chip_label()` | 🔧 | 🔧 | 🔧 | **HIGH** | Labels/filenames |
| `segment_voltage_sweep()` | ❌ | ❌ | 🔧 | **MEDIUM** | Gm helper |
| `calculate_transconductance()` | ❌ | ❌ | 🔧 | **MEDIUM** | Gm helper |
| `detect_light_on_window()` | 🔧 | ❌ | ❌ | **MEDIUM** | ITS shading |
| `ivg_sequence_gif()` | ❌ | 💡 | ❌ | **LOW** | Future feature |
| `plot_its_wavelength_overlay_delta()` | 💡 | ❌ | ❌ | **LOW** | Advanced ITS |
| `plot_savgol_comparison()` | ❌ | ❌ | 💡 | **LOW** | Debug feature |

**Legend**:
- ✅ = Directly used by command
- 🔧 = Utility/helper function
- 💡 = Optional enhancement
- ❌ = Not used by command

---

## Implementation Notes

### 1. Keep It Simple

Start with the 6 CRITICAL functions:
- `combine_metadata_by_seq()`
- `plot_its_overlay()`
- `plot_ivg_sequence()`
- `plot_ivg_transconductance()`
- `plot_ivg_transconductance_savgol()`
- `get_chip_label()`

These cover 100% of the core CLI functionality described in `update_plan.md`.

### 2. Module Organization

All essential functions are already in `src/plots.py` - no refactoring needed. The CLI commands just need to:
1. Parse arguments
2. Call `combine_metadata_by_seq()`
3. Call the appropriate plot function
4. Display success message

### 3. Error Handling

Key validations needed:
- **ITS command**: Verify experiments are ITS type
- **Transconductance command**: Verify ALL experiments are IVg type (critical!)
- **All commands**: Verify chip history exists (seq numbers are valid)

### 4. Output Directory Management

The CLI should:
- Set `plots.FIG_DIR` to user-specified output directory
- Use `tag` parameter to differentiate CLI-generated plots (e.g., `tag="cli_its_20251020"`)

### 5. Functions NOT Needed

These can be safely ignored for the MVP CLI:
- `plot_its_by_vg()` - Too complex, `plot_its_overlay` is simpler
- `plot_its_by_vg_delta()` - Redundant with `plot_its_overlay`
- `plot_ivg_last_of_day1_vs_first_of_day2()` - Too specific
- `set_its_figsize()` - Jupyter only
- `_setup_matplotlib_backend()` - Runs automatically
- All internal helper functions (used automatically by main functions)

---

## Final Recommendation

**Implement the CLI with these 6 functions**:

1. `combine_metadata_by_seq()` - For experiment selection
2. `plot_its_overlay()` - For ITS plotting
3. `plot_ivg_sequence()` - For IVg plotting
4. `plot_ivg_transconductance()` - For transconductance (gradient)
5. `plot_ivg_transconductance_savgol()` - For transconductance (savgol)
6. `get_chip_label()` - For clean labels

Everything else is either:
- Used internally by these functions (will work automatically)
- Optional enhancements for future releases
- Not needed for CLI workflow

This keeps the implementation clean, focused, and aligned with the notebook workflow users already know.
