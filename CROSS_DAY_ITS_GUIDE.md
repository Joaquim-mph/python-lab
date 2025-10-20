# Cross-Day Plotting Guide (ITS, IVg, Transconductance)

Quick reference for selecting and plotting experiments across multiple days.

Works for:
- ✅ ITS (time series)
- ✅ IVg (gate voltage sweeps)
- ✅ Transconductance (gm plots)

---

## The Problem: file_idx Repeats Across Days

When viewing chip history, you'll see something like this:

```
─── 2025-10-15 (2025-10-15) ────────────────────────────
  52  10:47:50  ITS  Alisson67  VG=-0.4 V  ...  #1
  53  10:52:30  ITS  Alisson67  VG=-0.5 V  ...  #2

─── 2025-10-16 (2025-10-16) ────────────────────────────
  57  12:03:23  ITS  Alisson67  VG=-0.4 V  ...  #1  ← Same #1!
  58  12:07:19  ITS  Alisson67  VG=-0.4 V  ...  #2  ← Same #2!
```

**The `#N` numbers (file_idx) repeat across days!** This is because each day's files are numbered independently (e.g., `Alisson67_1.csv`, `Alisson67_2.csv`).

---

## The Solution: Use `seq` Numbers

The **`seq`** column (first column) is unique across all days:

```
seq=52 → 2025-10-15, file #1
seq=57 → 2025-10-16, file #1  ← Different day, different seq!
```

---

## Workflow

### Step 1: View Chip History

```python
from pathlib import Path
from src.timeline import print_chip_history

print_chip_history(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("."),
    chip_number=67,
    chip_group_name="Alisson",
    proc_filter="ITS"  # Optional: only show ITS experiments
)
```

**Output:**
```
seq  date        time_hms  proc  summary
 52  2025-10-15  10:47:50  ITS   Alisson67  VG=-0.4 V  VDS=0.1 V  ...  #1
 53  2025-10-15  10:52:30  ITS   Alisson67  VG=-0.5 V  VDS=0.1 V  ...  #2
 57  2025-10-16  12:03:23  ITS   Alisson67  VG=-0.4 V  VDS=0.1 V  ...  #1
 58  2025-10-16  12:07:19  ITS   Alisson67  VG=-0.4 V  VDS=0.1 V  ...  #2
```

### Step 2: Note the `seq` Numbers

From the output above, identify which experiments you want by their **`seq`** number (first column):
- Want experiments 52, 57, 58? ✅ Use `seq_numbers=[52, 57, 58]`
- Don't use file_idx (#1, #2, etc.) ❌

### Step 3: Combine Metadata by seq

```python
from src.plots import combine_metadata_by_seq

meta = combine_metadata_by_seq(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("."),
    chip=67.0,
    seq_numbers=[52, 57, 58],  # Use seq from Step 1
    chip_group_name="Alisson"
)
```

### Step 4: Plot

The combined metadata works with **all plot types**:

#### ITS Overlay
```python
from src.plots import plot_its_overlay
from src.styles import set_plot_style

set_plot_style('prism_rain')

plot_its_overlay(
    meta,
    Path("."),
    tag="cross_day_comparison",
    legend_by="led_voltage",  # or "wavelength", "vg", "date"
    padding=0.05
)
```

#### IVg Sequence
```python
from src.plots import plot_ivg_sequence

# Select IVg experiments from chip history
meta_ivg = combine_metadata_by_seq(
    Path("metadata"),
    Path("."),
    chip=67.0,
    seq_numbers=[51, 56, 60],  # IVg measurements from different days
    chip_group_name="Alisson"
)

plot_ivg_sequence(meta_ivg, Path("."), tag="cross_day_ivg")
```

#### Transconductance
```python
from src.plots import plot_ivg_transconductance

# Same metadata works for transconductance
plot_ivg_transconductance(
    meta_ivg,
    Path("."),
    tag="cross_day_gm"
)
```

---

## When to Use What

### Cross-Day Analysis (Multiple Days)
✅ **Use `combine_metadata_by_seq()`**
- Automatically finds the right metadata files
- Uses `seq` numbers from chip history
- Handles schema differences between days

```python
meta = combine_metadata_by_seq(
    metadata_dir=Path("metadata"),
    raw_data_dir=Path("."),
    chip=67.0,
    seq_numbers=[52, 57, 58],
    chip_group_name="Alisson"
)
```

### Single-Day Analysis (One Day Only)
✅ **Use `load_and_prepare_metadata()` + filter**
- Your original workflow
- Uses `file_idx` (safe within one day)

```python
from src.plots import load_and_prepare_metadata
import polars as pl

meta = load_and_prepare_metadata("metadata/2025-10-16/metadata.csv", 67.0)

meta_filtered = meta.filter(
    (pl.col("proc") == "ITS") & pl.col("file_idx").is_in([1, 2, 3, 4])
)

plot_its_overlay(meta_filtered, Path("."), "single_day", legend_by="led_voltage")
```

---

## Key Points

| Concept | Description | Unique? |
|---------|-------------|---------|
| **seq** | Sequential number across entire history | ✅ Yes (across all days) |
| **file_idx** | File number from CSV filename | ❌ No (repeats each day) |
| **date** | Date of experiment | ❌ No (multiple experiments per day) |
| **source_file** | Full path to CSV file | ✅ Yes (unique identifier) |

---

## Troubleshooting

**Q: I used file_idx and got wrong experiments**
- A: file_idx repeats across days. Use `seq` from chip history instead.

**Q: The function says "no metadata found for day_folder"**
- A: Check that your metadata files are in `metadata/<day_folder>/metadata.csv` or `metadata/<day_folder>_metadata.csv`

**Q: Column schema mismatch error**
- A: This is handled automatically. The function uses only common columns across all days.

**Q: How do I know which seq to use?**
- A: Run `print_chip_history()` first and look at the first column (seq)

---

## Complete Examples

### Example 1: Cross-Day ITS Analysis

```python
from pathlib import Path
from src.timeline import print_chip_history
from src.plots import combine_metadata_by_seq, plot_its_overlay
from src.styles import set_plot_style

# 1. View ITS history
print_chip_history(Path("metadata"), Path("."), 67, "Alisson", proc_filter="ITS")

# Output shows seq numbers in first column
# seq=52, 53, 57, 58, ...

# 2. Select interesting ITS experiments
selected_its = [52, 57, 58]  # Based on what I saw in history

# 3. Combine
meta_its = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, selected_its, "Alisson"
)

# 4. Plot
set_plot_style('prism_rain')
plot_its_overlay(meta_its, Path("."), "cross_day_its", legend_by="led_voltage")
```

### Example 2: Cross-Day IVg Analysis

```python
from pathlib import Path
from src.timeline import print_chip_history
from src.plots import combine_metadata_by_seq, plot_ivg_sequence
from src.styles import set_plot_style

# 1. View IVg history
print_chip_history(Path("metadata"), Path("."), 67, "Alisson", proc_filter="IVg")

# Output shows:
# seq  date        time     proc  summary
#  51  2025-10-15  10:45:00  IVg  Alisson67 VDS=0.1 V ...
#  56  2025-10-16  11:55:00  IVg  Alisson67 VDS=0.1 V ...
#  60  2025-10-17  09:30:00  IVg  Alisson67 VDS=0.1 V ...

# 2. Select IVg measurements across days
selected_ivg = [51, 56, 60]

# 3. Combine
meta_ivg = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, selected_ivg, "Alisson"
)

# 4. Plot IVg sequence
set_plot_style('prism_rain')
plot_ivg_sequence(meta_ivg, Path("."), tag="cross_day_ivg")
```

### Example 3: Cross-Day Transconductance

```python
from pathlib import Path
from src.plots import combine_metadata_by_seq, plot_ivg_transconductance
from src.styles import set_plot_style

# Use same IVg metadata from Example 2
meta_ivg = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, [51, 56, 60], "Alisson"
)

# Plot transconductance
set_plot_style('prism_rain')
plot_ivg_transconductance(meta_ivg, Path("."), tag="cross_day_gm")
```

### Example 4: Mixed Analysis (IVg + ITS)

```python
from pathlib import Path
from src.timeline import print_chip_history
from src.plots import (
    combine_metadata_by_seq,
    plot_ivg_sequence,
    plot_its_overlay
)
from src.styles import set_plot_style

set_plot_style('prism_rain')

# View full history (no proc_filter)
print_chip_history(Path("metadata"), Path("."), 67, "Alisson")

# Select IVg measurements: seq 51, 56, 60
meta_ivg = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, [51, 56, 60], "Alisson"
)
plot_ivg_sequence(meta_ivg, Path("."), "device_evolution_ivg")

# Select ITS measurements: seq 52, 57, 58
meta_its = combine_metadata_by_seq(
    Path("metadata"), Path("."), 67.0, [52, 57, 58], "Alisson"
)
plot_its_overlay(meta_its, Path("."), "device_evolution_its", legend_by="date")
```

---

## See Also

- `example_cross_day_its.ipynb` - Complete notebook example
- `CHIP_HISTORY_GUIDE.md` - Guide for chip history functions
- `src/plots.py:combine_metadata_by_seq()` - Function documentation
- `src/timeline.py:print_chip_history()` - History function documentation
