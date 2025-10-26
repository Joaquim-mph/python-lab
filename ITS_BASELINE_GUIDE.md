# ITS Baseline Correction Guide

Complete guide to understanding and using baseline correction modes in ITS (Current vs Time) plots.

---

## Table of Contents

- [Overview](#overview)
- [The Four Baseline Modes](#the-four-baseline-modes)
- [When to Use Each Mode](#when-to-use-each-mode)
- [TUI Usage](#tui-usage)
- [CLI/Script Usage](#cliscript-usage)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

---

## Overview

ITS (Current vs Time) measurements record device current over time, typically during photoresponse experiments with LED ON/OFF cycles. Baseline correction helps isolate the photoresponse signal from drift, noise, and offset currents.

### Why Baseline Correction?

**Without correction:**
- Raw data includes device offset current
- Drift makes comparison difficult
- Y-axis range obscures small photoresponse signals

**With correction:**
- Isolates photoresponse (ΔI)
- Traces start at consistent baseline
- Easier to compare different conditions

---

## The Four Baseline Modes

### 1. Raw Data Mode (`baseline_mode="none"`)

**What it does:** Plots CSV data exactly as recorded, with no correction applied.

**Use when:**
- Analyzing noise characteristics
- Studying long-term drift
- Debugging measurement issues
- Comparing raw vs corrected data
- Need absolute current values

**TUI:** Uncheck "Apply baseline correction" checkbox

**Output filename:** Adds `_raw` suffix (e.g., `encap67_ITS_52_raw.png`)

**Example:**
```python
plot_its_overlay(
    meta,
    raw_dir,
    "experiment_tag",
    baseline_mode="none"
)
# Saved as: encap67_ITS_experiment_tag_raw.png
```

---

### 2. Baseline at t=0 (`baseline_t=0.0`)

**What it does:** Subtracts the current value at the first **visible** point (not the first CSV row).

**Key insight:** Uses first point ≥ `plot_start_time` to avoid measurement artifacts in first ~1 second.

**Use when:**
- Want each trace to start at y≈0
- Comparing drift across different conditions
- Dark experiments (no LED)
- Don't know exact baseline time but want consistent starting point

**TUI:** Check "Apply baseline correction" + enter "0"

**Output filename:** Normal filename (no `_raw` suffix)

**Example:**
```python
plot_its_overlay(
    meta,
    raw_dir,
    "drift_comparison",
    baseline_t=0.0,
    baseline_mode="fixed",  # Will be detected as "zero" mode
    plot_start_time=1.0  # Uses current at t=1s as baseline
)
```

**Important:** For Dark preset (`plot_start_time=1.0s`), baseline is taken at t=1s, not t=0s!

---

### 3. Fixed Baseline (`baseline_t=60.0`)

**What it does:** Interpolates current at specified time and subtracts it from all data.

**Use when:**
- Have consistent experimental timing
- Want baseline during known dark period
- Traditional analysis workflow
- Need reproducibility across days

**TUI:** Check "Apply baseline correction" + enter time value (e.g., "60")

**Output filename:** Normal filename (no `_raw` suffix)

**Example:**
```python
plot_its_overlay(
    meta,
    raw_dir,
    "photoresponse",
    baseline_t=60.0,
    baseline_mode="fixed"
)
# Baseline taken at t=60s for each trace
```

**Typical values:**
- Light experiments: 20-120s (after LED warmup)
- Dark experiments: 1-10s (minimal settling time needed)

---

### 4. Auto Baseline (`baseline_mode="auto"`)

**What it does:** Automatically calculates baseline from LED ON+OFF period metadata.

**Calculation:** `baseline_t = (LED_period) / baseline_auto_divisor`
- Default divisor: 2.0 → baseline at half the period
- E.g., 120s period → baseline at 60s

**Use when:**
- LED period varies between experiments
- Want consistent baseline timing relative to measurement structure
- Using preset workflows (recommended)
- Processing large datasets

**TUI:** Check "Apply baseline correction" + leave input empty

**Output filename:** Normal filename (no `_raw` suffix)

**Example:**
```python
plot_its_overlay(
    meta,
    raw_dir,
    "power_sweep",
    baseline_mode="auto",
    baseline_auto_divisor=2.0  # baseline = period / 2
)
# Auto-calculates from metadata for each measurement
```

**Presets using auto mode:**
- Light Power Sweep
- Light Spectral Response

---

## When to Use Each Mode

| Scenario | Recommended Mode | Why |
|----------|------------------|-----|
| **Photoresponse analysis** | Auto or Fixed (60s) | Consistent baseline during dark period |
| **Dark noise characterization** | Raw or t=0 | Need absolute values or relative drift |
| **Comparing different VG** | t=0 | All traces start at same point |
| **Cross-day comparison** | Auto | Handles varying LED timings |
| **Drift study** | Raw + t=0 | See absolute and relative trends |
| **Publication figure** | Fixed or Auto | Reproducible, documented baseline |
| **Debugging measurements** | Raw | See actual recorded data |
| **LED power sweep** | Auto (legend by LED voltage) | Period-aware baseline |
| **Wavelength sweep** | Auto (legend by wavelength) | Period-aware baseline |

---

## TUI Usage

### Quick Mode (Uses Presets)

1. Select chip → ITS → Quick Plot
2. Choose experiments
3. Preset automatically selects baseline mode:
   - **Dark**: Raw mode (no baseline)
   - **Light Power Sweep**: Auto mode
   - **Light Spectral**: Auto mode

### Custom Mode (Full Control)

1. Select chip → ITS → Custom Plot
2. Choose preset or "Custom"
3. Configure baseline:
   ```
   ┌─ Plot Options ────────────────┐
   │ Legend by: [Vg ▼]             │
   │ ☑ Apply baseline correction   │
   │ Baseline (s): [60.0    ]      │  ← Enter value, "0", or leave empty
   │                                │
   │ Padding: [0.05]                │
   │ Output dir: [figs]             │
   └────────────────────────────────┘
   ```
4. Baseline options:
   - **Unchecked** = Raw data (`_raw` suffix)
   - **Checked + Empty** = Auto baseline
   - **Checked + "0"** = Baseline at first visible point
   - **Checked + number** = Fixed baseline at that time

### Preview Screen

Before generating, preview shows:
```
─── Configuration ──────────────
• Baseline: None (RAW DATA - no correction)        ← Raw mode
• Baseline: 0.0 s (subtract value at t=0)          ← t=0 mode
• Baseline time: 60.0 s                            ← Fixed mode
• Baseline: Auto (LED period / 2.0)                ← Auto mode
```

---

## CLI/Script Usage

### Basic Examples

```python
from pathlib import Path
from src.plotting.its import plot_its_overlay, plot_its_dark
from src.plots import combine_metadata_by_seq

# Load data
meta = combine_metadata_by_seq(
    Path("metadata"),
    Path("raw_data"),
    chip=67,
    seq_numbers=[52, 57, 58],
    chip_group_name="Alisson"
)

# === Raw data plot ===
plot_its_overlay(
    meta,
    Path("raw_data"),
    "raw_comparison",
    baseline_mode="none"
)
# Output: encap67_ITS_raw_comparison_raw.png

# === Baseline at t=0 ===
plot_its_overlay(
    meta,
    Path("raw_data"),
    "drift_analysis",
    baseline_t=0.0,
    baseline_mode="fixed"  # Will use "zero" internally
)
# Output: encap67_ITS_drift_analysis.png

# === Fixed baseline ===
plot_its_overlay(
    meta,
    Path("raw_data"),
    "photoresponse",
    baseline_t=60.0,
    baseline_mode="fixed"
)
# Output: encap67_ITS_photoresponse.png

# === Auto baseline ===
plot_its_overlay(
    meta,
    Path("raw_data"),
    "power_sweep",
    baseline_mode="auto",
    baseline_auto_divisor=2.0
)
# Output: encap67_ITS_power_sweep.png
```

### Dark Experiments

```python
# Dark measurements use plot_its_dark() with same baseline modes
plot_its_dark(
    meta,
    Path("raw_data"),
    "noise_study",
    baseline_t=0.0,  # Uses first point at plot_start_time=1.0s
    baseline_mode="fixed",
    plot_start_time=1.0,  # Dark preset default
    legend_by="vg"
)
```

### Advanced: Dual Output (Raw + Corrected)

```python
# Generate both versions for comparison
tag = "VG_sweep"

# Raw version
plot_its_overlay(meta, raw_dir, tag, baseline_mode="none")
# → encap67_ITS_VG_sweep_raw.png

# Corrected version
plot_its_overlay(meta, raw_dir, tag, baseline_t=60.0, baseline_mode="fixed")
# → encap67_ITS_VG_sweep.png

# Both files saved without overwriting!
```

---

## Technical Details

### How `plot_start_time` Affects Baseline

The `plot_start_time` parameter controls:
1. **X-axis range:** Plot shows data from `t ≥ plot_start_time`
2. **Y-axis scaling:** Calculated from visible data only
3. **Baseline at t=0:** Uses first point ≥ `plot_start_time`

**Preset values:**
- Dark experiments: `plot_start_time = 1.0s` (minimal settling)
- Light experiments: `plot_start_time = 20.0s` (skip LED warmup)

**Example:**
```python
# Dark preset with baseline=0
plot_its_dark(
    meta, raw_dir, "dark",
    baseline_t=0.0,
    baseline_mode="fixed",
    plot_start_time=1.0  # Baseline taken at t=1s, not t=0s!
)
```

**Why?** First CSV point often has measurement artifacts (SMU settling, capacitive effects). Using first visible point ensures clean baseline.

### Baseline Correction Implementation

**Fixed mode (t ≠ 0):**
```python
I0 = interpolate_baseline(tt, yy, baseline_t=60.0)
yy_corrected = yy - I0
```

**Zero mode (t = 0):**
```python
# Find first visible point
visible_mask = tt >= plot_start_time
first_idx = np.where(visible_mask)[0][0]
I0 = yy[first_idx]
yy_corrected = yy - I0
```

**Auto mode:**
```python
period = metadata["Laser ON+OFF period"]
baseline_t = period / baseline_auto_divisor
I0 = interpolate_baseline(tt, yy, baseline_t)
yy_corrected = yy - I0
```

**Raw mode:**
```python
yy_corrected = yy  # No correction
```

### Filename Generation

```python
# Determine suffix
raw_suffix = "_raw" if baseline_mode == "none" else ""

# Build filename
filename = f"encap{chip}_ITS_{tag}{raw_suffix}.png"

# Examples:
# baseline_mode="none"  → encap67_ITS_52_57_raw.png
# baseline_mode="auto"  → encap67_ITS_52_57.png
# baseline_t=0.0        → encap67_ITS_52_57.png
# baseline_t=60.0       → encap67_ITS_52_57.png
```

---

## Troubleshooting

### Issue: Y-axis doesn't start at 0 with baseline=0

**Symptom:** Selected baseline=0, but plot shows y-axis starting at ~0.2 µA

**Cause:** You're likely using a Dark experiment with `plot_start_time=1.0s`. The baseline is correctly taken at t=1s (first visible point), but current has drifted between t=0 and t=1s.

**Solutions:**
1. **Expected behavior** - This is correct! You're seeing the drift from t=0 to t=1s.
2. **Want t=0 as baseline?** - Set `plot_start_time=0.0` (may include artifacts)
3. **Use fixed baseline instead** - Enter "1" to baseline at t=1s explicitly

### Issue: Raw plot overwrites corrected plot

**Symptom:** Both plots have same filename, one overwrites the other

**Cause:** Old code before `_raw` suffix feature

**Solution:** Update to latest version. Raw plots now automatically get `_raw` suffix.

### Issue: Auto baseline gives weird results

**Symptom:** Auto baseline produces unexpected ΔI values

**Possible causes:**
1. **Missing metadata:** "Laser ON+OFF period" not in CSV headers
   - Check with: `print(meta["Laser ON+OFF period"])`
   - Solution: Use fixed baseline instead
2. **Variable LED timing:** Period changes between measurements
   - Check: Compare periods across experiments
   - Solution: This is expected - auto mode handles this
3. **Wrong divisor:** Default divisor=2.0 may not suit your experiment
   - Solution: Adjust `baseline_auto_divisor` parameter

### Issue: Baseline checkbox is disabled

**Symptom:** Can't check/uncheck the baseline checkbox

**Cause:** Using Dark preset (baseline_mode="none" by default)

**Solution:** Switch to Custom preset or edit baseline input field (will enable checkbox automatically)

### Issue: First point has large spike

**Symptom:** All traces have spike at t=0 even with baseline correction

**Cause:** First CSV point is measurement artifact (SMU settling)

**Solution:** This is why we skip it! The baseline at t=0 mode uses first point at `plot_start_time`, not the artifact. The spike is still plotted but y-axis scaling ignores it.

---

## Best Practices

1. **Document your choice:** Note baseline mode in lab notebook/paper
2. **Consistency:** Use same mode for comparing experiments
3. **Presets for routine work:** Save time, ensure consistency
4. **Custom for special cases:** Fine-tune for specific analysis needs
5. **Keep raw data:** Always save raw files, can reprocess with different baseline later
6. **Check preview:** Verify baseline mode before generating plots
7. **Use descriptive tags:** Include baseline info in tag for clarity (`"VG_sweep_raw"`, `"photoresponse_auto"`)

---

## Summary Table

| Mode | TUI | CLI | Filename Suffix | Best For |
|------|-----|-----|-----------------|----------|
| **Raw** | Unchecked | `baseline_mode="none"` | `_raw` | Noise, drift, debugging |
| **t=0** | Checked + "0" | `baseline_t=0.0` | None | Comparative drift, dark experiments |
| **Fixed** | Checked + number | `baseline_t=60.0` | None | Traditional analysis, reproducibility |
| **Auto** | Checked + empty | `baseline_mode="auto"` | None | Variable timing, power/wavelength sweeps |

---

**See also:**
- `TUI_GUIDE.md` - Complete TUI documentation
- `CLAUDE.md` - Technical reference for developers
- `CLI_GUIDE.md` - Command-line usage examples
