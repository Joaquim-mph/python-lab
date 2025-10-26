# Plot Output System Documentation

**Date:** October 21, 2025
**Status:** Analysis for Output Directory Restructuring

---

## Overview

This document explains how plot filenames are generated and where files are saved in the current system. This analysis reveals inconsistencies between the CLI (which uses flat `figs/` directory) and TUI (which was designed for chip subdirectories but isn't working).

---

## Current System Architecture

### 1. **Plotting Modules** (`src/plotting/`)

Each plotting module has a global `FIG_DIR` variable that controls where plots are saved:

```python
# src/plotting/ivg.py, its.py, transconductance.py
FIG_DIR = Path("figs")  # Default value
```

The CLI overrides this before calling plot functions:
```python
# src/cli/commands/plot_its.py (line 383)
its.FIG_DIR = output_dir
```

### 2. **Output Filename Patterns**

Each plot type uses a different naming pattern:

#### **IVg Plots** (`src/plotting/ivg.py:56`)
```python
out = FIG_DIR / f"Encap{int(df['Chip number'][0])}_IVg_sequence_{tag}.png"
```
**Example:** `Encap67_IVg_sequence_seq_2_8_14.png`

#### **ITS Plots** (`src/plotting/its.py:335`)
```python
chipnum = int(df["Chip number"][0])
out = FIG_DIR / f"chip{chipnum}_ITS_overlay_{tag}.png"
```
**Example:** `chip67_ITS_overlay_seq_52_57_58.png`

#### **ITS Dark Plots** (`src/plotting/its.py:589`)
```python
out = FIG_DIR / f"chip{chipnum}_ITS_dark_{tag}.png"
```
**Example:** `chip67_ITS_dark_seq_60_61.png`

#### **Transconductance Gradient** (`src/plotting/transconductance.py:141`)
```python
chip_label = get_chip_label(df, default="Chip")  # Returns "Chip{number}"
out = FIG_DIR / f"{chip_label}_gm_sequence_{tag}.png"
```
**Example:** `Chip67_gm_sequence_seq_2_8_14.png`

#### **Transconductance Savgol** (`src/plotting/transconductance.py:303`)
```python
out = FIG_DIR / f"{chip_label}_gm_savgol_{tag}.png"
```
**Example:** `Chip67_gm_savgol_seq_2_8_14.png`

---

## Current Directory Structure

### **CLI Behavior** (Working, but uses flat directory)

The CLI uses `setup_output_dir()` helper:

```python
# src/cli/helpers.py:118-144
def setup_output_dir(output_dir: Path, chip: int, chip_group: str) -> Path:
    """Create and return appropriate output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
```

**Current CLI Flow:**
```
User runs: python process_and_analyze.py plot-its 67 --seq 52,57,58 --output figs

CLI calls: setup_output_dir(Path("figs"), 67, "Alisson")
           → Returns: Path("figs")

CLI sets: its.FIG_DIR = Path("figs")

Plot saves to: figs/chip67_ITS_overlay_seq_52_57_58.png
```

**Result:** All plots go to flat `figs/` directory, no chip subdirectories.

---

### **TUI Behavior** (Not Working as Intended)

The TUI config screens set chip-specific output directories:

```python
# src/tui/screens/its_config.py:133-137
yield Input(
    placeholder=f"Default: figs/{self.chip_group}{self.chip_number}/",
    value=f"figs/{self.chip_group}{self.chip_number}/",
    id="output-dir-input",
)
```

**TUI Flow:**
```
User selects: Chip 67, ITS plot type, custom config

Config screen defaults to: "figs/Alisson67/"

User proceeds → plot_generation.py gets config

But then... where does FIG_DIR get set?
```

Let me check `plot_generation.py` to see how it uses the output directory.

---

## The Problem

### **Issue 1: TUI Doesn't Use Config Output Directory**

Looking at the TUI plot generation screen (`src/tui/screens/plot_generation.py`), the output directory from config is passed but **not actually used** to set `FIG_DIR`:

```python
# src/tui/screens/plot_generation.py:146
# This is the DEFAULT but doesn't come from config!
output_dir = Path(f"figs/{self.chip_group}{self.chip_number}/")
```

**The config value is collected but ignored!**

### **Issue 2: CLI Uses Flat Directory**

The CLI's `setup_output_dir()` function doesn't create chip subdirectories:

```python
# Current implementation
def setup_output_dir(output_dir: Path, chip: int, chip_group: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir  # Just returns the base dir!
```

**Should be:**
```python
def setup_output_dir(output_dir: Path, chip: int, chip_group: str) -> Path:
    chip_subdir = output_dir / f"{chip_group}{chip}"
    chip_subdir.mkdir(parents=True, exist_ok=True)
    return chip_subdir
```

### **Issue 3: Inconsistent and Verbose Naming**

Different plot types use different formats, making files hard to find:

- **IVg:** `Encap67_IVg_sequence_seq_2_8_14.png` (capital E, "sequence" is redundant)
- **ITS:** `chip67_ITS_overlay_seq_52_57_58.png` (lowercase chip, "overlay" is redundant)
- **Transconductance:** `Chip67_gm_sequence_seq_2_8_14.png` (capital C, "sequence" is redundant)

**Problems:**
- ❌ Three different chip prefixes: `Encap`, `chip`, `Chip`
- ❌ Mixed case makes typing error-prone
- ❌ Redundant words ("sequence", "overlay") add clutter
- ❌ Hard to search/sort files by chip

**Solution:** Standardize to `encap{N}_plottype_seq_...` format

---

## Plot Tag Generation

The CLI generates unique tags based on seq numbers to prevent overwriting:

```python
# src/cli/helpers.py:69-115
def generate_plot_tag(seq_numbers: list[int], custom_tag: str | None = None) -> str:
    """Generate unique plot tag based on seq numbers."""
    sorted_seqs = sorted(seq_numbers)

    # Short lists: readable format
    if len(sorted_seqs) <= 5:
        seq_str = "_".join(str(s) for s in sorted_seqs)
        tag = f"seq_{seq_str}"
    # Long lists: first 3 + count + hash
    else:
        first_three = "_".join(str(s) for s in sorted_seqs[:3])
        seq_hash = hashlib.md5("_".join(str(s) for s in sorted_seqs).encode()).hexdigest()[:6]
        tag = f"seq_{first_three}_plus{len(sorted_seqs)-3}_{seq_hash}"

    if custom_tag:
        tag = f"{tag}_{custom_tag}"

    return tag
```

**Examples:**
- `[52, 57, 58]` → `"seq_52_57_58"`
- `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` → `"seq_1_2_3_plus7_a3b2c1"`

**This system works well and should be preserved.**

---

## Desired Directory Structure

We want to organize plots by chip with standardized naming:

```
figs/
├── Alisson67/
│   ├── encap67_ITS_seq_52_57_58.png
│   ├── encap67_ITS_dark_seq_60_61.png
│   ├── encap67_gm_seq_2_8_14.png
│   ├── encap67_gm_savgol_seq_2_8_14.png
│   └── encap67_IVg_seq_2_8_14.png
├── Alisson72/
│   ├── encap72_ITS_seq_10_15_20.png
│   └── encap72_IVg_seq_5_10.png
└── Alisson81/
    └── encap81_ITS_seq_1_2_3.png
```

**Benefits:**
- **Cleaner:** No more 100+ files in flat `figs/` directory
- **Organized:** All plots for a chip in one place
- **Scalable:** Works well with many chips
- **Clear:** Easy to find plots for a specific chip

---

## Files That Need Changes

### **1. CLI Helper** (`src/cli/helpers.py`)

**Change `setup_output_dir()` to create chip subdirectories:**

```python
def setup_output_dir(output_dir: Path, chip: int, chip_group: str) -> Path:
    """
    Create and return chip-specific output directory.

    Creates: output_dir/{chip_group}{chip}/

    Examples
    --------
    >>> setup_output_dir(Path("figs"), 67, "Alisson")
    PosixPath('figs/Alisson67')
    """
    chip_subdir = output_dir / f"{chip_group}{chip}"
    chip_subdir.mkdir(parents=True, exist_ok=True)
    return chip_subdir
```

**Impact:** All CLI commands will automatically use chip subdirectories.

---

### **2. TUI Plot Generation** (`src/tui/screens/plot_generation.py`)

**Use the output_dir from config instead of hardcoding:**

```python
# BEFORE (line 146):
output_dir = Path(f"figs/{self.chip_group}{self.chip_number}/")

# AFTER:
# Get output_dir from config, or use default with chip subdir
output_dir = Path(self.config.get("output_dir", f"figs/{self.chip_group}{self.chip_number}/"))
```

**Impact:** TUI will respect the output directory from custom config screens.

---

### **3. TUI Config Screens** (Already Fixed!)

These are already correct:

- ✅ `src/tui/screens/its_config.py:133-137` - Defaults to chip subdirectory
- ✅ `src/tui/screens/ivg_config.py:132-137` - Defaults to chip subdirectory
- ✅ `src/tui/screens/transconductance_config.py:179-185` - Defaults to chip subdirectory

**No changes needed here.**

---

### **4. Plotting Modules - Standardize to "encap{N}" Format** ⭐ **REQUIRED**

**Standardize all plot filenames to use lowercase `encap{N}` prefix and simplified names:**

#### **New Standardized Format:**
- **IVg:** `encap67_IVg_seq_2_8_14.png` (removed "sequence")
- **ITS:** `encap67_ITS_seq_52_57_58.png` (removed "overlay")
- **ITS Dark:** `encap67_ITS_dark_seq_60_61.png` (kept "dark" qualifier)
- **Transconductance (gradient):** `encap67_gm_seq_2_8_14.png` (removed "sequence")
- **Transconductance (savgol):** `encap67_gm_savgol_seq_2_8_14.png` (kept "savgol" qualifier)

**Benefits:**
- ✅ **Consistent:** All files use `encap{N}_` prefix
- ✅ **Lowercase:** Easier to type, no case confusion
- ✅ **Cleaner:** Removed redundant words ("sequence", "overlay")
- ✅ **Clear:** Plot type immediately visible in filename
- ✅ **Sortable:** All files for same chip sort together

**Changes needed:**

```python
# src/plotting/ivg.py:56
# BEFORE:
out = FIG_DIR / f"Encap{int(df['Chip number'][0])}_IVg_sequence_{tag}.png"

# AFTER:
chipnum = int(df['Chip number'][0])
out = FIG_DIR / f"encap{chipnum}_IVg_{tag}.png"

# src/plotting/its.py:335
# BEFORE:
out = FIG_DIR / f"chip{chipnum}_ITS_overlay_{tag}.png"

# AFTER:
out = FIG_DIR / f"encap{chipnum}_ITS_{tag}.png"

# src/plotting/its.py:589
# BEFORE:
out = FIG_DIR / f"chip{chipnum}_ITS_dark_{tag}.png"

# AFTER:
out = FIG_DIR / f"encap{chipnum}_ITS_dark_{tag}.png"

# src/plotting/transconductance.py:141
# BEFORE:
chip_label = get_chip_label(df, default="Chip")  # Returns "Chip{number}"
out = FIG_DIR / f"{chip_label}_gm_sequence_{tag}.png"

# AFTER:
chipnum = int(df['Chip number'][0])
out = FIG_DIR / f"encap{chipnum}_gm_{tag}.png"

# src/plotting/transconductance.py:303
# BEFORE:
chip_label = get_chip_label(df, default="Chip")
out = FIG_DIR / f"{chip_label}_gm_savgol_{tag}.png"

# AFTER:
chipnum = int(df['Chip number'][0])
out = FIG_DIR / f"encap{chipnum}_gm_savgol_{tag}.png"
```

---

## Implementation Plan

### **Phase 1: Minimal Fix (TUI Only)** ⭐ RECOMMENDED

Fix the TUI to use chip subdirectories without breaking CLI:

1. **Update `src/tui/screens/plot_generation.py`:**
   - Use `output_dir` from config instead of hardcoding
   - Create directory if it doesn't exist before plotting

**Impact:** TUI uses chip subdirectories, CLI unchanged

**Testing:** Run TUI plot generation, verify files go to `figs/Chip67/`

---

### **Phase 2: Full Organization (CLI + TUI)**

Update both CLI and TUI to use chip subdirectories:

1. **Update `src/cli/helpers.py`:**
   - Change `setup_output_dir()` to create chip subdirectories

2. **Test all CLI commands:**
   ```bash
   python process_and_analyze.py plot-its 67 --seq 52,57,58
   python process_and_analyze.py plot-ivg 67 --seq 2,8,14
   python process_and_analyze.py plot-transconductance 67 --seq 2,8,14
   ```

3. **Verify plots go to `figs/Alisson67/` for all commands**

**Impact:** All plots organized by chip

**Testing:** Run full test suite with both CLI and TUI

---

### **Phase 3: Standardize Names to "encap" Format** ⭐ **REQUIRED**

Standardize chip label format and simplify names across all plot types:

1. **Update `src/plotting/ivg.py:56`** - Change to `encap{N}_IVg_{tag}.png`
2. **Update `src/plotting/its.py:335`** - Change to `encap{N}_ITS_{tag}.png`
3. **Update `src/plotting/its.py:589`** - Change to `encap{N}_ITS_dark_{tag}.png`
4. **Update `src/plotting/transconductance.py:141`** - Change to `encap{N}_gm_{tag}.png`
5. **Update `src/plotting/transconductance.py:303`** - Change to `encap{N}_gm_savgol_{tag}.png`

**Impact:** Consistent, clean filenames across all plot types

**Testing:** Generate all plot types, verify names match standard format

---

## Migration Guide

Existing scripts will need updates for both directory structure and naming changes:

### **Before (Old System - Flat Directory, Mixed Names):**
```python
# Old locations and names varied by plot type:
its_file = Path("figs") / "chip67_ITS_overlay_seq_52_57_58.png"
ivg_file = Path("figs") / "Encap67_IVg_sequence_seq_2_8_14.png"
gm_file = Path("figs") / "Chip67_gm_sequence_seq_2_8_14.png"
```

### **After (New System - Chip Subdirectories, Standardized Names):**
```python
# New locations use chip subdirectories and consistent naming:
its_file = Path("figs") / "Alisson67" / "encap67_ITS_seq_52_57_58.png"
ivg_file = Path("figs") / "Alisson67" / "encap67_IVg_seq_2_8_14.png"
gm_file = Path("figs") / "Alisson67" / "encap67_gm_seq_2_8_14.png"
```

### **Backward-Compatible Helper Function:**

Add this to help transition scripts that reference old plot files:

```python
def find_plot_file(chip: int, chip_group: str, plot_type: str, tag: str) -> Path:
    """
    Find plot file in new or old location with new or old naming.

    Searches in this order:
    1. New location with new naming (figs/Alisson67/encap67_ITS_seq_52_57_58.png)
    2. Old location with old naming (figs/chip67_ITS_overlay_seq_52_57_58.png)

    Parameters
    ----------
    chip : int
        Chip number (e.g., 67)
    chip_group : str
        Chip group name (e.g., "Alisson")
    plot_type : str
        Plot type: "ITS", "IVg", "gm", etc.
    tag : str
        Plot tag (e.g., "seq_52_57_58")

    Returns
    -------
    Path
        Path to the plot file

    Raises
    ------
    FileNotFoundError
        If plot not found in any location
    """
    # Build new format filename
    new_filename = f"encap{chip}_{plot_type}_{tag}.png"
    new_path = Path("figs") / f"{chip_group}{chip}" / new_filename

    if new_path.exists():
        return new_path

    # Build old format filenames (varied by plot type)
    old_filenames = {
        "ITS": f"chip{chip}_ITS_overlay_{tag}.png",
        "IVg": f"Encap{chip}_IVg_sequence_{tag}.png",
        "gm": f"Chip{chip}_gm_sequence_{tag}.png",
    }

    old_filename = old_filenames.get(plot_type, f"chip{chip}_{plot_type}_{tag}.png")
    old_path = Path("figs") / old_filename

    if old_path.exists():
        print(f"[warn] Using old plot location: {old_path}")
        print(f"[info] Expected new location: {new_path}")
        return old_path

    raise FileNotFoundError(
        f"Plot file not found.\n"
        f"  Tried new: {new_path}\n"
        f"  Tried old: {old_path}"
    )
```

### **Example Migration:**

```python
# Old script (before migration):
its_plot = Path("figs") / "chip67_ITS_overlay_seq_52_57_58.png"
if its_plot.exists():
    display(its_plot)

# Migrated script (after changes):
# Option 1: Direct path (recommended)
its_plot = Path("figs") / "Alisson67" / "encap67_ITS_seq_52_57_58.png"
if its_plot.exists():
    display(its_plot)

# Option 2: Using helper function (for transition period)
its_plot = find_plot_file(67, "Alisson", "ITS", "seq_52_57_58")
display(its_plot)
```

---

## Summary

### **Implementation Status (October 21, 2025):**

All three phases have been **COMPLETED**:

1. ✅ **Phase 1 (TUI):** TUI now automatically appends chip subdirectory
   - `src/tui/screens/plot_generation.py:145-164` always appends `{chip_group}{chip}/` to user's output path
   - Config screens show "figs" → "figs/Alisson67/" to indicate automatic subdirectory

2. ✅ **Phase 2 (CLI):** CLI now uses chip subdirectories
   - `src/cli/helpers.py:143-145` creates `output_dir/{chip_group}{chip}/`

3. ✅ **Phase 3 (Naming):** All plot types use standardized `encap{N}_` format
   - `src/plotting/ivg.py:57` → `encap{N}_IVg_{tag}.png`
   - `src/plotting/its.py:335` → `encap{N}_ITS_{tag}.png`
   - `src/plotting/its.py:589` → `encap{N}_ITS_dark_{tag}.png`
   - `src/plotting/transconductance.py:141` → `encap{N}_gm_{tag}.png`
   - `src/plotting/transconductance.py:303` → `encap{N}_gm_savgol_{tag}.png`
   - All CLI dry-run/preview modes updated

### **TUI Behavior:**

The TUI now **always creates chip subdirectories**, regardless of what the user enters:

- User enters: `"figs"` → Plots saved to: `figs/Alisson67/`
- User enters: `"my_plots"` → Plots saved to: `my_plots/Alisson67/`
- User enters: `"figs/Alisson67/"` → Plots saved to: `figs/Alisson67/` (no duplication)

This ensures consistency between CLI and TUI, and prevents accidentally saving all chips' plots to the same directory.

### **Previous Problems (RESOLVED):**
1. ✅ ~~TUI ignores user-configured output directory~~ → **FIXED**
2. ✅ ~~CLI uses flat `figs/` directory~~ → **FIXED** (now creates chip subdirectories)
3. ✅ ~~Inconsistent chip label formats (`Encap`, `chip`, `Chip`)~~ → **FIXED** (all use `encap`)
4. ✅ ~~Redundant words in filenames ("sequence", "overlay")~~ → **FIXED** (removed)

### **New Standardized Format:**
- **IVg:** `encap67_IVg_seq_2_8_14.png`
- **ITS:** `encap67_ITS_seq_52_57_58.png`
- **ITS Dark:** `encap67_ITS_dark_seq_60_61.png`
- **Transconductance:** `encap67_gm_seq_2_8_14.png`
- **Transconductance (Savgol):** `encap67_gm_savgol_seq_2_8_14.png`

### **Recommendation:**

Implement all three phases together as they are interconnected:
- **Phase 1** fixes TUI config usage
- **Phase 2** organizes files into chip subdirectories
- **Phase 3** standardizes naming for consistency and clarity

This will result in a clean, organized, and consistent plotting system.

---

## Next Steps

1. Review this document with the team
2. Decide on implementation phases
3. Update code according to chosen phases
4. Test thoroughly with both CLI and TUI
5. Update user documentation
6. Migrate existing plots to new structure (if needed)

---

## Testing Checklist

To verify the implementation is working correctly, run these tests:

### **CLI Testing:**

```bash
# Test ITS plot generation
python process_and_analyze.py plot-its 67 --seq 52,57,58 --dry-run
# Expected output: figs/Alisson67/encap67_ITS_seq_52_57_58.png

# Test IVg plot generation
python process_and_analyze.py plot-ivg 67 --seq 2,8,14 --dry-run
# Expected output: figs/Alisson67/encap67_IVg_seq_2_8_14.png

# Test Transconductance plot generation
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --dry-run
# Expected output: figs/Alisson67/encap67_gm_seq_2_8_14.png
```

### **Verify:**
1. ✅ All filenames use lowercase `encap` prefix
2. ✅ No redundant words ("sequence", "overlay")
3. ✅ Files go to `figs/{ChipGroup}{ChipNumber}/` subdirectory
4. ✅ Plot tag format is `seq_X_Y_Z` for short lists

### **TUI Testing:**

1. Launch TUI: `python process_and_analyze.py wizard`
2. Select a chip and plot type
3. Use custom configuration
4. Verify output directory shows: `figs/Alisson67/`
5. Generate plot and verify file location

---

**Document Version:** 2.0 (Updated after implementation)
**Author:** Claude Code
**Status:** Implementation Complete - Testing Required
