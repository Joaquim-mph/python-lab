# CLI Tool Guide: process_and_analyze.py

Beautiful command-line interface for automated data processing and chip history generation.

---

## Installation

```bash
# Install dependencies (includes typer and rich)
pip install -r requirements.txt
```

---

## Quick Start

### Run Complete Pipeline (Most Common)

```bash
# Parse all raw data AND generate chip histories in one command
python process_and_analyze.py full-pipeline

# With custom paths and chip group
python process_and_analyze.py full-pipeline \
    --raw raw_data \
    --meta metadata \
    --group Alisson \
    --min 5
```

**This single command:**
1. Scans `raw_data/` for all folders with CSV files
2. Parses each CSV header and extracts metadata
3. Saves metadata to `metadata/<folder>/metadata.csv`
4. Discovers all unique chips in metadata
5. Generates complete timeline history for each chip
6. Saves `<ChipName>_history.csv` for each chip
7. Shows beautiful statistics and summaries

---

## Individual Commands

### 1. Parse All Raw Data

Extract metadata from all raw CSV files:

```bash
python process_and_analyze.py parse-all
```

**Options:**
- `--raw`, `-r`: Raw data directory (default: `raw_data`)
- `--meta`, `-m`: Output metadata directory (default: `metadata`)

**Example:**
```bash
python process_and_analyze.py parse-all --raw raw_data --meta metadata
```

**What it does:**
- Scans for folders containing CSV files
- Parses CSV headers (#Parameters, #Metadata)
- Extracts: chip number, voltages, laser settings, timestamps
- Creates mirrored directory structure in metadata/
- Shows progress bar and summary table

**Output:**
```
metadata/
├── Alisson_04_sept/
│   └── metadata.csv
├── Alisson_15_sept/
│   └── metadata.csv
└── 2025-10-16/
    └── metadata.csv
```

---

### 2. Generate Chip Histories

Build complete timeline for each chip:

```bash
python process_and_analyze.py chip-histories
```

**Options:**
- `--meta`, `-m`: Metadata directory (default: `metadata`)
- `--raw`, `-r`: Raw data directory (default: `.`)
- `--group`, `-g`: Chip group name prefix (default: `Alisson`)
- `--min`: Minimum experiments per chip (default: `1`)
- `--save/--no-save`: Save individual CSV files (default: `--save`)
- `--history-dir`, `-o`: Output directory for history files (default: `chip_histories`)

**Example:**
```bash
python process_and_analyze.py chip-histories \
    --meta metadata \
    --group Alisson \
    --min 10 \
    --save
```

**What it does:**
- Scans all metadata files
- Discovers unique chip numbers
- Builds complete history for each chip (all days)
- Calculates statistics (total experiments, by procedure, date ranges)
- Shows detailed tables with per-chip breakdowns

**Output:**
```
chip_histories/
├── Alisson67_history.csv
├── Alisson72_history.csv
├── Alisson81_history.csv
└── ...
```

---

### 3. Show Chip History

Display the complete history of a specific chip in the terminal:

```bash
python process_and_analyze.py show-history 67
```

**Options:**
- `chip_number`: Chip number to display (positional argument, required)
- `--group`, `-g`: Chip group name prefix (default: `Alisson`)
- `--history-dir`, `-d`: Directory with history files (default: `chip_histories`)
- `--proc`, `-p`: Filter by procedure type (IVg, ITS, IV, etc.)
- `--limit`, `-n`: Show only last N experiments

**Examples:**
```bash
# Show complete history for chip 67
python process_and_analyze.py show-history 67

# Show only ITS experiments for chip 72
python process_and_analyze.py show-history 72 --proc ITS

# Show last 20 experiments for chip 81
python process_and_analyze.py show-history 81 --limit 20

# Different chip group
python process_and_analyze.py show-history 100 --group Device
```

**What it displays:**
- Summary cards with timeline and procedure breakdown
- Chronological table of all experiments
- Date, time, procedure type, and description for each
- Visual separation between different days
- File source information

**Output Example:**
```
╭──────────────────────────────────────╮
│   Alisson67 Experiment History       │
│ Total experiments: 66                │
╰──────────────────────────────────────╯

╭─── Timeline ───╮  ╭─── Procedures ───╮
│ Date Range:    │  │ ITS:  41         │
│   2025-10-14   │  │ IVg:  15         │
│   to           │  │ IV:   10         │
│   2025-10-16   │  │                  │
│ Days: 3        │  │                  │
╰────────────────╯  ╰──────────────────╯

╭───────── Experiments ─────────╮
│ Seq  Date      Time   Proc  Description                     │
├───────────────────────────────────────────────────────────┤
│  52  2025-10-15  10:47  ITS  VG=-0.4 V  VDS=0.1 V  ...    │
│  57  2025-10-16  12:03  ITS  VG=-0.4 V  VDS=0.1 V  ...    │
│  58  2025-10-16  12:07  ITS  VG=-0.4 V  VDS=0.1 V  ...    │
╰───────────────────────────────────────────────────────────╯

Data source: chip_histories/Alisson67_history.csv
```

---

### 4. Quick Statistics

Fast overview without generating full histories:

```bash
python process_and_analyze.py quick-stats
```

**Options:**
- `--meta`, `-m`: Metadata directory (default: `metadata`)
- `--group`, `-g`: Chip group name (default: `Alisson`)

**What it does:**
- Scans metadata files (fast!)
- Shows: total chips, total experiments, approximate procedure counts
- No CSV files created
- Perfect for quick sanity checks

---

## Example Output

### Full Pipeline Output

```
╭───────────────────────────────────────────────────────────╮
│       Complete Data Processing Pipeline                  │
│ Step 1: Parse raw CSV files → metadata                   │
│ Step 2: Generate chip histories from metadata            │
╰───────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────╮
│            Step 1: Metadata Extraction                  │
│ Parsing raw CSV headers and extracting parameters      │
╰─────────────────────────────────────────────────────────╯

Scanning raw_data for experiment folders...
✓ Found 3 folder(s) with CSV files

raw_data
├── Alisson_04_sept (45 CSV files)
├── 2025-10-15 (15 CSV files)
└── 2025-10-16 (12 CSV files)

Processing folders... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:05

╭─────────────────────── Metadata Generation Summary ──────────────────────╮
│ Folder             CSV Files  Parsed  Output File                        │
├────────────────────────────────────────────────────────────────────────────┤
│ Alisson_04_sept           45      45  metadata/Alisson_04_sept/metad...  │
│ 2025-10-15               15      15  metadata/2025-10-15/metadata.csv   │
│ 2025-10-16               12      12  metadata/2025-10-16/metadata.csv   │
├────────────────────────────────────────────────────────────────────────────┤
│ TOTAL                     72      72  3 file(s)                          │
╰────────────────────────────────────────────────────────────────────────────╯

✓ Metadata extraction complete!

================================================================================

╭─────────────────────────────────────────────────────────╮
│        Step 2: Chip History Generation                  │
│ Building complete experiment timelines for all chips    │
╰─────────────────────────────────────────────────────────╯

Scanning metadata for metadata files...
✓ Found 3 metadata file(s)

Discovering chips...
Scanning metadata... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
✓ Found 3 unique chip(s): [67, 72, 81]

Building chip histories...
Processing chips... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02

╭───────────────────────────────────────────────────────────╮
│ Successfully generated histories for 3 chip(s)           │
╰───────────────────────────────────────────────────────────╯

╭─────────────────── Overall Summary ────────────────────╮
│ Metric               Value                             │
├───────────────────────────────────────────────────────────┤
│ Chip Group           Alisson                           │
│ Total Chips          3                                 │
│ Total Experiments    234                               │
├───────────────────────────────────────────────────────────┤
│   IVg experiments    45                                │
│   ITS experiments    156                               │
│   IV experiments     33                                │
╰───────────────────────────────────────────────────────────╯

╭──────────────────────── Per-Chip Statistics ─────────────────────────╮
│ Chip       Total  Days  Date Range              Procedure Breakdown  │
│            Expts                                                      │
├───────────────────────────────────────────────────────────────────────┤
│ Alisson67     66     3  2025-10-14 to 2025-10-  ITS: 41             │
│                         16                       IVg: 15             │
│                                                  IV: 10              │
├───────────────────────────────────────────────────────────────────────┤
│ Alisson72    156     8  2025-09-04 to 2025-09-  ITS: 120            │
│                         20                       IVg: 25             │
│                                                  IV: 11              │
├───────────────────────────────────────────────────────────────────────┤
│ Alisson81     12     2  2025-10-08 to 2025-10-  ITS: 8              │
│                         09                       IVg: 4              │
╰───────────────────────────────────────────────────────────────────────╯

✓ Chip history CSV files saved:
  • Alisson67_history.csv
  • Alisson72_history.csv
  • Alisson81_history.csv

✓ Chip history generation complete!

================================================================================

╭────────────────────────────────────────╮
│        Pipeline Complete!              │
│ Total time: 12.3 seconds               │
╰────────────────────────────────────────╯
```

---

## Common Workflows

### Workflow 1: New Data Arrives

```bash
# Put new CSV files in raw_data/2025-10-20/
# Then run:
python process_and_analyze.py full-pipeline
```

### Workflow 2: Regenerate Histories Only

```bash
# If metadata already exists, just regenerate histories:
python process_and_analyze.py chip-histories --min 5
```

### Workflow 3: Different Chip Group

```bash
# For a different chip naming convention:
python process_and_analyze.py full-pipeline --group Device --min 10
```

### Workflow 4: Quick Check

```bash
# Just see what's there:
python process_and_analyze.py quick-stats
```

---

## Command Reference

| Command | Purpose | Speed | Output Files |
|---------|---------|-------|--------------|
| `full-pipeline` | Complete workflow | Slow | metadata/*.csv + *_history.csv |
| `parse-all` | Extract metadata only | Medium | metadata/*.csv |
| `chip-histories` | Generate histories only | Medium | chip_histories/*_history.csv |
| `show-history` | Display chip timeline | Instant | None (terminal display) |
| `quick-stats` | Fast overview | Fast | None (terminal only) |

---

## Tips

1. **Always run `full-pipeline` for new data** - It's the simplest and most reliable

2. **Use `--min` to filter noise** - Set `--min 10` to only include well-characterized chips

3. **Check output** - Look for the CSV files:
   - `metadata/<folder>/metadata.csv` - Parsed metadata
   - `Alisson67_history.csv` - Complete chip history

4. **Customize chip group** - If your chips are named "Device72" instead of "Alisson72":
   ```bash
   python process_and_analyze.py full-pipeline --group Device
   ```

5. **Dry run with quick-stats** - Before processing, check what's there:
   ```bash
   python process_and_analyze.py quick-stats
   ```

---

## Integration with Existing Workflow

This CLI tool fits into your analysis pipeline:

```
Raw CSVs  →  [CLI: parse + histories]  →  Jupyter notebooks
                      ↓
              metadata/*.csv
              *_history.csv
                      ↓
              [Notebooks use combine_metadata_by_seq()]
                      ↓
              Cross-day plots
```

**Example notebook workflow after CLI:**
```python
# After running: python process_and_analyze.py full-pipeline
from pathlib import Path
from src.plots import combine_metadata_by_seq, plot_its_overlay

# Use the generated histories to select experiments
meta = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, [52, 57, 58], "Alisson"
)

plot_its_overlay(meta, Path("."), "analysis", legend_by="led_voltage")
```

---

## Troubleshooting

**Problem**: "No metadata files found"
- **Solution**: Run `parse-all` first, or check `--meta` path

**Problem**: "No folders with CSV files found"
- **Solution**: Check `--raw` path points to directory containing experiment folders

**Problem**: Different chip naming
- **Solution**: Use `--group` flag: `--group YourChipPrefix`

**Problem**: Too many chips with few experiments
- **Solution**: Use `--min 10` to filter out poorly-characterized chips

---

---

## CLI Plotting Commands

### 5. Plot ITS Overlay

Generate ITS (current vs time) overlay plots directly from the terminal:

```bash
python process_and_analyze.py plot-its 67 --seq 52,57,58
```

**Options:**
- `chip_number` (positional, required): Chip number
- `--seq`, `-s`: Comma-separated seq numbers (required unless `--auto`)
- `--auto`: Automatically select all ITS experiments
- `--legend`, `-l`: Legend grouping (`led_voltage`, `wavelength`, `vg`) [default: `led_voltage`]
- `--tag`, `-t`: Custom tag for output filename
- `--output`, `-o`: Output directory [default: `figs`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--padding`: Y-axis padding fraction [default: `0.05`]
- `--baseline`: Baseline time in seconds [default: `60.0`]
- `--vg`: Filter by gate voltage (V)
- `--wavelength`: Filter by wavelength (nm)
- `--date`: Filter by date (YYYY-MM-DD)
- `--preview`: Preview mode - show what will be plotted without generating files
- `--dry-run`: Dry run mode - ultra-fast validation showing only output filename

**Examples:**

```bash
# Plot specific experiments
python process_and_analyze.py plot-its 67 --seq 52,57,58

# Auto-select all ITS with wavelength legend
python process_and_analyze.py plot-its 67 --auto --legend wavelength

# Filter by gate voltage
python process_and_analyze.py plot-its 67 --auto --vg -0.4

# Filter by wavelength
python process_and_analyze.py plot-its 72 --auto --wavelength 365

# Custom output location
python process_and_analyze.py plot-its 67 --seq 52,57,58 --output results/

# Custom baseline and padding
python process_and_analyze.py plot-its 67 --seq 52,57,58 --baseline 30 --padding 0.1

# Preview mode - see what will be plotted without generating files
python process_and_analyze.py plot-its 67 --seq 52,57,58 --preview

# Dry run mode - fastest validation (only shows output filename)
python process_and_analyze.py plot-its 67 --seq 52,57,58 --dry-run
```

**Preview Mode:**

Use `--preview` to validate experiments and see what will be plotted **without** generating the actual plot file:

```bash
python process_and_analyze.py plot-its 67 --auto --preview
```

Preview mode will:
- Validate all experiments and apply filters
- Load and display experiment metadata
- Show plot settings
- Display the output filename that would be created
- Exit without generating any files

This is useful for:
- Verifying experiment selection before plotting
- Checking output filename before running
- Quick validation without waiting for matplotlib
- Testing filters and auto-selection

**Dry Run Mode:**

Use `--dry-run` for the **fastest** validation - it only validates experiments and shows the output filename:

```bash
python process_and_analyze.py plot-its 67 --auto --dry-run
```

Dry run mode will:
- Validate all experiments exist in chip history
- Calculate and display the output filename
- Check if the file already exists (shows "file exists - will overwrite" or "new file")
- Exit immediately without loading any metadata

This is useful for:
- Ultra-fast filename checking (much faster than preview)
- Batch scripting to check what files will be created
- Quick validation of seq numbers
- Checking for potential overwrites before running

**Mode Comparison:**
- **Normal mode**: Validates → Loads metadata → Generates plot
- **Preview mode**: Validates → Loads metadata → Shows settings → Exits (no plot)
- **Dry run mode**: Validates → Shows filename → Exits (fastest, no metadata loading)

```

**Output:**
- Saves PNG file with unique name based on seq numbers
- Example: `figs/chip67_ITS_overlay_seq_52_57_58.png`
- Same experiments always produce same filename (no overwrites)
- Different experiments produce different filenames (never overwrites)

**What it displays:**
- Header with chip name
- Auto-selection or validation messages
- Table of experiments being plotted
- Plot settings panel
- Success message with output file path

**Output Example:**
```
╭─────────────────────────────────────╮
│ ITS Overlay Plot: Alisson67         │
╰─────────────────────────────────────╯

✓ Auto-selected 3 ITS experiment(s)

Validating experiments...
✓ All seq numbers valid

Loading experiment metadata...
[info] combined 3 experiment(s) from 2 day(s)
[info] using 45 common column(s)

           ITS Experiments to Plot
┌──────┬──────┬─────────┬────────┬───────┬──────────┐
│ File │ Proc │  VG (V) │  λ (nm)│ LED V │   File   │
├──────┼──────┼─────────┼────────┼───────┼──────────┤
│  52  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
│  57  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
│  58  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
└──────┴──────┴─────────┴────────┴───────┴──────────┘

Total: 3 experiment(s)

╭─────── Plot Settings ────────╮
│ Legend by: led_voltage       │
│ Baseline time: 60.0 s        │
│ Padding: 5.00%               │
│ Output directory: figs       │
╰──────────────────────────────╯

Generating plot...
saved figs/chip67_ITS_overlay_seq_52_57_58.png

✓ Plot generated successfully!
Output: figs/chip67_ITS_overlay_seq_52_57_58.png
```

**Preview Mode Output Example:**
```
╭─────────────────────────────────────╮
│ ITS Overlay Plot: Alisson67         │
╰─────────────────────────────────────╯

Using specified seq numbers: [52, 57, 58]

Validating experiments...
✓ All seq numbers valid

Loading experiment metadata...
[info] combined 3 experiment(s) from 2 day(s)

           ITS Experiments to Plot
┌──────┬──────┬─────────┬────────┬───────┬──────────┐
│ File │ Proc │  VG (V) │  λ (nm)│ LED V │   File   │
├──────┼──────┼─────────┼────────┼───────┼──────────┤
│  52  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
│  57  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
│  58  │ ITS  │  -0.40  │  365   │  2.50 │ ...csv   │
└──────┴──────┴─────────┴────────┴───────┴──────────┘

Total: 3 experiment(s)

╭─────── Plot Settings ────────╮
│ Legend by: led_voltage       │
│ Baseline time: 60.0 s        │
│ Padding: 5.00%               │
│ Output directory: figs       │
╰──────────────────────────────╯

╭────────── Output File ───────────╮
│ Output file:                     │
│ figs/chip67_ITS_overlay_seq_52_5 │
│ 7_58.png                         │
╰──────────────────────────────────╯

✓ Preview complete - no files generated
  Run without --preview to generate plot
```

---

### 6. Plot IVg Sequence

Generate IVg (current vs gate voltage) sequence plots directly from the terminal:

```bash
python process_and_analyze.py plot-ivg 67 --seq 2,8,14
```

**Options:**
- `chip_number` (positional, required): Chip number
- `--seq`, `-s`: Comma-separated seq numbers (required unless `--auto`)
- `--auto`: Automatically select all IVg experiments
- `--tag`, `-t`: Custom tag for output filename
- `--output`, `-o`: Output directory [default: `figs`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--vds`: Filter by VDS voltage (V)
- `--date`: Filter by date (YYYY-MM-DD)
- `--preview`: Preview mode - show what will be plotted without generating files
- `--dry-run`: Dry run mode - ultra-fast validation showing only output filename

**Examples:**

```bash
# Plot specific IVg experiments
python process_and_analyze.py plot-ivg 67 --seq 2,8,14

# Auto-select all IVg
python process_and_analyze.py plot-ivg 67 --auto

# Filter by date
python process_and_analyze.py plot-ivg 67 --auto --date 2025-10-15

# Filter by VDS
python process_and_analyze.py plot-ivg 72 --auto --vds 0.1

# Custom output location
python process_and_analyze.py plot-ivg 67 --seq 5,10,15 --output results/

# Preview mode - see what will be plotted without generating files
python process_and_analyze.py plot-ivg 67 --auto --preview

# Dry run mode - fastest validation (only shows output filename)
python process_and_analyze.py plot-ivg 67 --auto --dry-run
```

**Preview Mode:**

Use `--preview` to validate experiments and see what will be plotted **without** generating the actual plot file. Preview mode works the same as for `plot-its` - it validates experiments, loads metadata, displays settings, shows the output filename, and exits without creating any files.

**Dry Run Mode:**

Use `--dry-run` for ultra-fast validation - see `plot-its` section above for full details. Works identically for all plotting commands.

```

**Output:**
- Saves PNG file with unique name based on seq numbers
- Example: `figs/Encap67_IVg_sequence_seq_2_8_14.png`
- Same experiments always produce same filename (no overwrites)
- Different experiments produce different filenames (never overwrites)

**What it displays:**
- Header with chip name
- Auto-selection or validation messages
- Table of experiments being plotted
- Plot settings panel
- Success message with output file path

**What the plot shows:**
- All IVg curves overlaid in chronological order
- Each curve labeled with file index and light/dark status
- X-axis: Gate voltage (V)
- Y-axis: Current (µA)
- Legend shows which curve corresponds to which measurement
- Y-axis starts at 0 for clarity

**Output Example:**
```
╭─────────────────────────────────────╮
│ IVg Sequence Plot: Alisson67        │
╰─────────────────────────────────────╯

Using specified seq numbers: [2, 8, 14]

Validating experiments...
✓ All seq numbers valid

Loading experiment metadata...
[info] combined 3 experiment(s) from 1 day(s)
[info] using 48 common column(s)

           IVg Experiments to Plot
┌──────┬──────┬─────────┬────────┬───────┬──────────┐
│ File │ Proc │  VG (V) │  λ (nm)│ LED V │   File   │
├──────┼──────┼─────────┼────────┼───────┼──────────┤
│   2  │ IVg  │  sweep  │   N/A  │  N/A  │ ...csv   │
│   8  │ IVg  │  sweep  │   365  │  2.50 │ ...csv   │
│  14  │ IVg  │  sweep  │   N/A  │  N/A  │ ...csv   │
└──────┴──────┴─────────┴────────┴───────┴──────────┘

Total: 3 experiment(s)

╭─────── Plot Settings ────────╮
│ Plot type: IVg sequence      │
│            (Id vs Vg)        │
│ Curves: 3 measurement(s)     │
│ Output directory: figs       │
╰──────────────────────────────╯

Generating plot...
saved figs/Encap67_IVg_sequence_seq_2_8_14.png

✓ Plot generated successfully!
Output: figs/Encap67_IVg_sequence_seq_2_8_14.png
```

---

### 7. Plot Transconductance

Generate transconductance (gm = dI/dVg) plots from IVg experiments:

```bash
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14
```

**IMPORTANT:** Only IVg experiments can be used for transconductance. Use `show-history --proc IVg` to find valid seq numbers.

**Options:**
- `chip_number` (positional, required): Chip number
- `--seq`, `-s`: Comma-separated seq numbers of **IVg experiments** (required unless `--auto`)
- `--auto`: Automatically select all IVg experiments
- `--method`, `-m`: Derivative method [default: `gradient`]
  - `gradient`: numpy.gradient (central differences, matches PyQtGraph)
  - `savgol`: Savitzky-Golay filter (smoother curves)
- `--window`: Savitzky-Golay window length (odd number) [default: `9`]
- `--polyorder`: Savitzky-Golay polynomial order [default: `3`]
- `--tag`, `-t`: Custom tag for output filename
- `--output`, `-o`: Output directory [default: `figs`]
- `--group`, `-g`: Chip group name [default: `Alisson`]
- `--vds`: Filter by VDS voltage (V)
- `--date`: Filter by date (YYYY-MM-DD)
- `--preview`: Preview mode - show what will be plotted without generating files
- `--dry-run`: Dry run mode - ultra-fast validation showing only output filename

**Examples:**

```bash
# Plot transconductance with default gradient method
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14

# Use Savitzky-Golay filter for smoother curves
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol

# Auto-select all IVg with custom Savitzky-Golay parameters
python process_and_analyze.py plot-transconductance 67 --auto --method savgol --window 11 --polyorder 5

# Filter by date
python process_and_analyze.py plot-transconductance 67 --auto --date 2025-10-15

# Custom output location
python process_and_analyze.py plot-transconductance 72 --seq 5,10,15 --output results/

# Preview mode - see what will be plotted without generating files
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol --preview

# Dry run mode - fastest validation (only shows output filename)
python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --dry-run
```

**Preview Mode:**

Use `--preview` to validate experiments and see what will be plotted **without** generating the actual plot file:

```bash
python process_and_analyze.py plot-transconductance 67 --auto --method savgol --preview
```

Preview mode is especially useful for transconductance plots because:
- It performs the strict IVg-only validation
- Shows the method-specific output filename (different for gradient vs savgol)
- Allows you to verify experiment selection without waiting for computations
- Helps avoid accidentally running with wrong method or experiments

**Dry Run Mode:**

Use `--dry-run` for ultra-fast validation - it validates experiments and shows the output filename (including method-specific naming for gradient vs savgol). See `plot-its` section above for full details.

```

**Output:**
- Gradient method: `figs/Chip67_gm_sequence_seq_2_8_14.png`
- Savgol method: `figs/Chip67_gm_savgol_seq_2_8_14.png`
- Same experiments + same method → same filename (no overwrites)
- Different experiments or different method → different filenames

**What it displays:**
- Header with chip name
- Method validation
- Strict IVg type validation (fails if any non-IVg found)
- Table of experiments being plotted
- Plot settings panel with method details
- Success message with output file path

**What the plot shows:**
- Transconductance (gm = dI/dVg) vs gate voltage
- Each curve corresponds to one IVg measurement
- X-axis: Gate voltage (V)
- Y-axis: Transconductance (µS)
- Zero line for reference
- Segmented to avoid artifacts at sweep reversals

**Method Comparison:**
- **gradient**: Faster, matches PyQtGraph behavior, suitable for clean data
- **savgol**: Smoother curves, better for noisy data, adjustable parameters

**Output Example:**
```
╭─────────────────────────────────────╮
│ Transconductance Plot: Alisson67    │
╰─────────────────────────────────────╯

Using specified seq numbers: [2, 8, 14]

Validating experiments...
✓ All seq numbers valid

Loading experiment metadata...
[info] combined 3 experiment(s) from 1 day(s)
[info] using 48 common column(s)

Validating experiment types...
✓ All 3 experiment(s) are IVg type

     IVg Experiments for Transconductance
┌──────┬──────┬─────────┬────────┬───────┬──────────┐
│ File │ Proc │  VG (V) │  λ (nm)│ LED V │   File   │
├──────┼──────┼─────────┼────────┼───────┼──────────┤
│   2  │ IVg  │  sweep  │   N/A  │  N/A  │ ...csv   │
│   8  │ IVg  │  sweep  │   365  │  2.50 │ ...csv   │
│  14  │ IVg  │  sweep  │   N/A  │  N/A  │ ...csv   │
└──────┴──────┴─────────┴────────┴───────┴──────────┘

Total: 3 experiment(s)

╭─────── Plot Settings ────────╮
│ Plot type: Transconductance  │
│            (gm = dI/dVg)     │
│ Method: numpy.gradient       │
│         (central differences)│
│ Curves: 3 IVg measurement(s) │
│ Output directory: figs       │
╰──────────────────────────────╯

Generating transconductance plot...
saved figs/Chip67_gm_sequence_seq_2_8_14.png

✓ Plot generated successfully!
Output: figs/Chip67_gm_sequence_seq_2_8_14.png
```

**Error Handling Example:**
```bash
# If you accidentally include non-IVg experiments:
python process_and_analyze.py plot-transconductance 67 --seq 2,52,8

Error: Found 1 non-IVg experiment(s)
Transconductance can only be computed from IVg experiments!

Non-IVg experiments found:
  • Seq 52: ITS

Hint: Use show-history 67 --proc IVg to find valid IVg experiments
```

---

## See Also

- `CROSS_DAY_ITS_GUIDE.md` - Using the generated histories for cross-day plotting
- `CHIP_HISTORY_GUIDE.md` - Understanding the timeline functions
- `example_cross_day_its.ipynb` - Interactive notebook examples
- `plots_functions_analysis.md` - Analysis of plotting functions for CLI workflow
