# python-lab

**Automated analysis toolkit for semiconductor device characterization data (IV/ITS measurements)**

This repository provides end-to-end processing of raw measurement CSV files from lab experiments, extracting metadata, organizing data, and generating publication-ready plots with consistent styling.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Workflow Overview](#workflow-overview)
  - [1. Generate Metadata](#1-generate-metadata)
  - [2. Process Single Day](#2-process-single-day)
  - [3. Batch Process All Days](#3-batch-process-all-days)
  - [4. Interactive Analysis](#4-interactive-analysis)
- [Project Structure](#project-structure)
- [Data Format](#data-format)
- [Plotting Capabilities](#plotting-capabilities)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Features

✅ **Automated metadata extraction** from CSV headers
✅ **Session-based grouping** (IVg → ITS... → IVg blocks)
✅ **Multi-chip processing** with organized output structure
✅ **Publication-ready plots** with 10+ custom matplotlib styles
✅ **Timeline generation** for experiment chronology
✅ **Animated GIFs** for IVg sequences
✅ **Wavelength-dependent photoresponse** analysis
✅ **Baseline-corrected delta plots** (ΔI vs time)

---

## Quick Start

### Option 1: TUI (Recommended for Lab Members)

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the interactive plotting assistant
python tui_app.py

# Follow the wizard: Select chip → plot type → experiments → generate!
```

🎨 **Beautiful guided interface** with keyboard navigation, real-time progress, and interactive experiment selection.

### Option 2: CLI (For Automation)

```bash
# Clone and setup
git clone <repo-url>
cd python-lab
pip install -r requirements.txt

# Process all experiments
python src/process_all.py --raw raw_data --meta metadata

# Figures saved to: figs/<day>/<chip>/IVg|ITS/...
```

---

## Installation

### Requirements
- Python 3.10+
- Dependencies listed in `requirements.txt`

### Setup

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Key Dependencies:**
- `polars` - Fast dataframe operations
- `numpy` - Numerical computing
- `matplotlib` + `scienceplots` - Plotting and styling
- `imageio` + `Pillow` - GIF generation
- `textual` - Terminal user interface (TUI)

---

## Usage

### TUI Workflow (Interactive)

```bash
python tui_app.py
```

**8-Step Wizard:**
1. **Main Menu** - Choose action (New Plot / Recent Configs / Process Data)
2. **Chip Selection** - Auto-discover chips from metadata
3. **Plot Type** - ITS / IVg / Transconductance
4. **Config Mode** - Quick (defaults) or Custom (full control)
5. **Configuration** - Select experiments or customize parameters
6. **Preview** - Review all settings before generating
7. **Generation** - Real-time progress tracking
8. **Success** - View results, plot another, or exit

**New Features:**
- 💾 **Configuration Persistence** - Auto-save successful plots, load from Recent Configs
- ⚡ **Quick Mode** - Smart defaults for fast plotting
- 🎛️ **Custom Mode** - Full parameter control (filters, baseline, legend, savgol params)
- 📤 **Export/Import** - Share configurations as JSON files

📘 **Full guide:** See `TUI_GUIDE.md` for keyboard shortcuts, config persistence, and troubleshooting.

### CLI Workflow (Command Line)

**Complete Pipeline (Recommended):**
```bash
# Parse all raw data + generate chip histories in one command
python process_and_analyze.py full-pipeline
```

**Individual Commands:**
```bash
# Parse metadata from raw CSVs
python process_and_analyze.py parse-all --raw raw_data --meta metadata

# Generate chip timeline histories
python process_and_analyze.py chip-histories --meta metadata --group Alisson

# View specific chip history
python process_and_analyze.py show-history 67 --meta metadata --group Alisson

# Generate plots
python process_and_analyze.py plot-its 67 --seq 52,57,58
python process_and_analyze.py plot-ivg 67 --seq 2,8,14
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol

# Quick statistics
python process_and_analyze.py quick-stats --meta metadata
```

📘 **Full CLI reference:** See `CLI_GUIDE.md` for all commands and options.

**Data Pipeline:**
```
Raw CSVs → Metadata Extraction → Session Grouping → Figure Generation
   ↓              ↓                      ↓                  ↓
raw_data/    metadata.csv           load_and_prepare   figs/
```

### 1. Generate Metadata

Extract experimental parameters from raw CSV headers:

```bash
# Edit folder_name in src/parser.py first
python src/parser.py
```

**Output:** `<folder>_metadata.csv` containing chip number, voltages, laser settings, timestamps, etc.

**Alternative:** Use mirrored directory structure
```bash
python src/parser.py --raw raw_data --out metadata
# Creates: metadata/<day>/metadata.csv
```

### 2. Process Single Day

Generate all plots for one day's experiments:

```bash
# Edit configuration in src/process_day.py:
# - METADATA_CSV = "Alisson_15_sept_metadata.csv"
# - BASE_DIR = Path("raw_data")
# - CHIPS_TO_PROCESS = None  # or [68, 72, 75]

python src/process_day.py
```

**Output structure:**
```
figs/
└── Chip72_2024_09_15/
    ├── IVg/
    │   ├── sequence/          # Chronological IVg plots
    │   ├── pairs/             # Consecutive pairs
    │   ├── triplets/          # 3-measurement groups
    │   ├── gif/               # Animated sequences
    │   └── transconductance/  # dI/dVg (gm) plots
    └── ITS/
        ├── regular/     # I(t) at specific VG
        ├── delta/       # ΔI(t) baseline-corrected
        └── overlays/    # Wavelength comparisons
```

### 3. Batch Process All Days

Automatically discover and process all metadata files:

```bash
# Process everything
python src/process_all.py --raw raw_data --meta metadata

# Filter specific chips
python src/process_all.py --chips 68 75

# Skip GIFs or overlays
python src/process_all.py --no-gif --no-overlays
```

### 4. Interactive Analysis

Open Jupyter notebooks for custom exploration:

```bash
jupyter notebook encap72.ipynb
```

Example notebook workflow:
```python
from pathlib import Path
from src.plots import load_and_prepare_metadata, plot_ivg_sequence
from src.styles import set_plot_style

# Set plotting style
set_plot_style('prism_rain')

# Load data
meta = load_and_prepare_metadata('Alisson_15_sept_metadata.csv', chip=72)

# Generate plot
plot_ivg_sequence(meta, Path('raw_data'), tag='custom_analysis')
```

---

## Project Structure

```
python-lab/
├── src/                          # Core modules
│   ├── parser.py                 # Metadata extraction
│   ├── utils.py                  # Data reading & standardization
│   ├── plots.py                  # Plotting functions
│   ├── styles.py                 # Matplotlib themes
│   ├── timeline.py               # Chronological summaries
│   ├── process_day.py            # Single-day orchestrator
│   └── process_all.py            # Batch processor
├── raw_data/                     # Raw CSV files
│   ├── Alisson_04_sept/
│   ├── Alisson_15_sept/
│   └── ...
├── metadata/                     # Extracted metadata (optional)
│   └── Alisson_15_sept/
│       └── metadata.csv
├── figs/                         # Generated figures (gitignored)
├── *.ipynb                       # Interactive notebooks
├── requirements.txt              # Python dependencies
├── CLAUDE.md                     # AI assistant guide
└── README.md                     # This file
```

---

## Data Format

### Raw CSV Structure

```csv
#Procedure: <laser_setup.procedures.It.It>
#Parameters:
#	Chip number: 72
#	VG: -3.0 V
#	VDS: 0.1 V
#	Laser voltage: 3.5 V
#	Laser wavelength: 455.0 nm
#	Laser ON+OFF period: 120 s
#Metadata:
#	Start time: 1726394856.2
#Data:
t (s),I (A),VL (V),Plate T (degC),Ambient T (degC),Clock (ms)
0.0,7.23624e-06,0.0,nan,nan,nan
0.08,7.230252e-06,0.0,nan,nan,nan
...
```

### Metadata CSV Columns

| Column | Description |
|--------|-------------|
| `Chip number` | Device identifier |
| `VG` | Gate voltage (V) |
| `VDS` / `VSD` | Source-drain voltage (V) |
| `Laser voltage` | Laser power setting (V) |
| `Laser wavelength` | Wavelength (nm) |
| `start_time` | Unix timestamp |
| `time_hms` | HH:MM:SS format |
| `source_file` | Path to raw CSV (relative to BASE_DIR) |

---

## Plotting Capabilities

### Measurement Types

| Type | Description | Plot Type |
|------|-------------|-----------|
| **IVg** | Gate voltage sweep | Id vs Vg curves |
| **ITS** | Time series (photoresponse) | Id vs time with light ON/OFF |
| **IV** | Source-drain sweep | Id vs Vds |

### Available Plots

#### IVg Analysis
- **Sequence plots** - Chronological overlay of all IVg measurements
- **Pair/triplet comparisons** - Consecutive measurements for drift tracking
- **Animated GIFs** - Cumulative overlay with frame-by-frame progression

#### ITS Analysis
- **VG-filtered overlays** - Time series at specific gate voltages
- **Delta plots** - Baseline-corrected ΔI(t) = I(t) - I(t₀)
- **Wavelength comparison** - Multi-wavelength photoresponse
- **UV/blue vs longer wavelengths** - Grouped spectral analysis

### Plotting Styles

10+ custom matplotlib themes via `set_plot_style()`:
- `prism_rain` (default) - Vibrant colors, clean design
- `solar_flare` - High-contrast warm tones
- `dark_nova` - Dark background for presentations
- `cryolab` - Cool blues for cryogenic data
- `ink_sketch` - Black-and-white publication style

---

## Configuration

### Global Settings

Edit `src/process_day.py` or `src/process_all.py` for:

```python
# Metadata file
METADATA_CSV = "Alisson_15_sept_metadata.csv"

# Raw data location
BASE_DIR = Path("raw_data")

# Chip filter (None = all chips)
CHIPS_TO_PROCESS = [68, 72, 75]

# Optional outputs
GENERATE_GIFS = True
GENERATE_WAVELENGTH_OVERLAYS = True
```

### Plot Customization

```python
from src.styles import set_plot_style

# Available styles:
# prism_rain, solar_flare, dark_nova, nova,
# super_nova, cryolab, deep_forest, ink_sketch

set_plot_style('solar_flare')
```

### Session Grouping Logic

The code automatically groups measurements into sessions:

```
Session 1: IVg (pre) → ITS → ITS → IVg (post)
Session 2: IVg (pre) → ITS → IVg (post)
```

- **pre_ivg**: Initial characterization
- **its**: Stress/photoresponse measurements
- **post_ivg**: Final characterization

---

## Troubleshooting

### Path Duplication Errors

**Problem:** Files not found, paths like `raw_data/raw_data/...`

**Solution:** `process_all.py` includes `fix_source_paths()` to normalize paths. Ensure `source_file` in metadata is relative to `BASE_DIR`.

### Missing Columns

**Problem:** `KeyError: 'VG'` or similar

**Solution:** Raw CSVs have variable column names. `src/utils.py` standardizes:
- `Gate V`, `gate voltage` → `VG`
- `VSD`, `VDS`, `drain-source` → `VSD`
- `I`, `ID`, `current` → `I`

### Empty Plots

**Problem:** Figures generated but no data plotted

**Solution:** Check:
1. Chip number in metadata matches `CHIPS_TO_PROCESS`
2. `source_file` paths are correct
3. CSV files exist in `BASE_DIR`

### GIF Generation Fails

**Problem:** `imageio` errors or blank frames

**Solution:** Ensure `imageio>=2.28.0` and `Pillow>=10.0.0` installed:
```bash
pip install --upgrade imageio Pillow
```

---

## Example Workflow

Complete example for processing new data:

```bash
# 1. Add raw CSVs to raw_data/Alisson_20_sept/

# 2. Generate metadata
# Edit src/parser.py: folder_name = "Alisson_20_sept"
python src/parser.py

# 3. Process all chips
# Edit src/process_day.py: METADATA_CSV = "Alisson_20_sept_metadata.csv"
python src/process_day.py

# 4. Review outputs
open figs/Chip72_2024_09_20/IVg/sequence/*.png
open figs/Chip72_2024_09_20/ITS/overlays/*.png
```

Or use the automated batch processor:

```bash
python src/process_all.py --raw raw_data --meta metadata --chips 72
```

---

## Contributing

This is a research lab utility. For questions or improvements, contact the repository owner.

---

## License

Internal use only. Contact owner for usage permissions.
