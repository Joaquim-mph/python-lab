# ITS Preset Configuration System - Implementation Plan

**Date:** October 22, 2025
**Status:** Planning Phase
**Purpose:** Add smart preset configurations for common ITS plotting scenarios

---

## 1. Requirements Analysis

### User Requirements

**Three Main Use Cases:**

1. **Dark Experiments** (No laser/LED illumination)
   - No baseline correction needed
   - Plot starts at t = 1s (skip initial transient)
   - Legend by VG (gate voltage)
   - Purpose: Noise characterization, dark current stability

2. **Light Experiments - Same Wavelength, Different Power**
   - Baseline = (LED ON+OFF period) / 2
   - Auto-detect baseline from metadata
   - Legend by LED voltage (power indicator)
   - Purpose: Power-dependent photoresponse

3. **Light Experiments - Same Power, Different Wavelength**
   - Baseline = (LED ON+OFF period) / 2
   - Auto-detect baseline from metadata
   - Legend by wavelength
   - Purpose: Spectral response analysis

### Additional Feature: Duration Mismatch Warning

**Problem:** When plotting multiple ITS experiments with different total durations, the x-axis scaling becomes inconsistent.

**Solution:** Detect and warn user when selected experiments have significantly different durations (> 10% variation).

---

## 2. Current System Analysis

### Current ITS Plotting Parameters

From `src/plotting/its.py`:

```python
def plot_its_overlay(
    df: pl.DataFrame,
    base_dir: Path,
    tag: str,
    baseline_t: float = 60.0,              # ← User configurable
    *,
    legend_by: str = "wavelength",         # ← User configurable
    padding: float = 0.02,                 # ← User configurable
):
```

**Key Constants:**
- `PLOT_START_TIME = 20.0` - Hardcoded start time (skip initial noise)
- `LIGHT_WINDOW_ALPHA = 0.15` - Light shading transparency

**Metadata Available:**
- `Laser ON+OFF period` - Total cycle duration (used at line 265-269)
- Total measurement duration - Calculated from data (line 276-278)
- Wavelength, VG, LED voltage - Available for legend grouping

### Current Configuration Paths

**TUI Custom Config** (`src/tui/screens/its_config.py`):
- Baseline time input (default: 60.0)
- Padding input (default: 0.2)
- Legend by selector (dropdown)
- Filters: VG, wavelength, VDS, date

**CLI** (`src/cli/commands/plot_its.py`):
- `--baseline` flag (default: 60.0)
- `--legend-by` flag (default: "led_voltage")
- `--padding` flag (default: 0.02)
- Filters: `--vg`, `--wavelength`, `--vds`, `--date`

---

## 3. Proposed Preset System Architecture

### 3.1 Preset Definitions

**Storage Location:** `src/plotting/its_presets.py` (NEW FILE)

```python
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class ITSPreset:
    """ITS plotting preset configuration."""
    name: str
    description: str

    # Baseline configuration
    baseline_mode: Literal["auto", "fixed", "none"]
    baseline_value: Optional[float] = None  # Used if baseline_mode = "fixed"
    baseline_auto_divisor: float = 2.0      # Used if baseline_mode = "auto" (period / divisor)

    # Plot configuration
    plot_start_time: float = 20.0           # Override PLOT_START_TIME
    legend_by: str = "wavelength"
    padding: float = 0.02

    # Validation
    check_duration_mismatch: bool = True
    duration_tolerance: float = 0.10        # 10% tolerance


# Built-in presets
PRESETS = {
    "dark": ITSPreset(
        name="Dark Experiments",
        description="No illumination - noise/stability measurements",
        baseline_mode="none",
        plot_start_time=1.0,                # Start at 1s instead of 20s
        legend_by="vg",
        padding=0.02,
        check_duration_mismatch=True,
    ),

    "light_power_sweep": ITSPreset(
        name="Power Sweep (Same λ)",
        description="Different LED powers, same wavelength",
        baseline_mode="auto",
        baseline_auto_divisor=2.0,          # baseline = period / 2
        plot_start_time=20.0,
        legend_by="led_voltage",
        padding=0.02,
        check_duration_mismatch=True,
    ),

    "light_spectral": ITSPreset(
        name="Spectral Response (Same Power)",
        description="Different wavelengths, same LED power",
        baseline_mode="auto",
        baseline_auto_divisor=2.0,
        plot_start_time=20.0,
        legend_by="wavelength",
        padding=0.02,
        check_duration_mismatch=True,
    ),

    "custom": ITSPreset(
        name="Custom",
        description="Fully configurable parameters",
        baseline_mode="fixed",
        baseline_value=60.0,
        plot_start_time=20.0,
        legend_by="wavelength",
        padding=0.02,
        check_duration_mismatch=False,
    ),
}
```

### 3.2 Modified Plotting Function

**Update `src/plotting/its.py`:**

```python
def plot_its_overlay(
    df: pl.DataFrame,
    base_dir: Path,
    tag: str,
    baseline_t: Optional[float] = 60.0,    # ← Now Optional
    *,
    baseline_mode: str = "fixed",          # ← NEW: "fixed", "auto", "none"
    plot_start_time: float = 20.0,         # ← NEW: configurable start time
    legend_by: str = "wavelength",
    padding: float = 0.02,
    check_duration_mismatch: bool = False, # ← NEW: enable duration check
    duration_tolerance: float = 0.10,      # ← NEW: tolerance for warnings
):
    """
    Overlay ITS traces with flexible baseline and preset support.

    Parameters
    ----------
    baseline_t : float, optional
        Time point for baseline correction (used if baseline_mode="fixed")
    baseline_mode : {"fixed", "auto", "none"}
        Baseline mode:
        - "fixed": Use baseline_t value
        - "auto": Calculate from LED ON+OFF period / 2
        - "none": No baseline correction (for dark experiments)
    plot_start_time : float
        Start time for x-axis (default: 20.0 s)
    check_duration_mismatch : bool
        If True, warn if experiments have different durations
    duration_tolerance : float
        Tolerance for duration mismatch (default: 0.10 = 10%)
    """
```

### 3.3 Helper Functions

**Add to `src/plotting/its.py`:**

```python
def _calculate_auto_baseline(df: pl.DataFrame) -> float:
    """
    Calculate automatic baseline from LED ON+OFF period metadata.

    Returns period / 2, or 60.0 if period not found.
    """
    if "Laser ON+OFF period" in df.columns:
        periods = []
        for row in df.iter_rows(named=True):
            try:
                period = float(row["Laser ON+OFF period"])
                if np.isfinite(period) and period > 0:
                    periods.append(period)
            except Exception:
                pass

        if periods:
            median_period = float(np.median(periods))
            return median_period / 2.0

    print("[warn] Could not auto-detect LED period, using baseline_t=60.0")
    return 60.0


def _check_duration_mismatch(
    durations: list[float],
    tolerance: float = 0.10
) -> tuple[bool, Optional[str]]:
    """
    Check if experiment durations vary beyond tolerance.

    Returns
    -------
    has_mismatch : bool
        True if durations vary > tolerance
    warning_msg : str or None
        Warning message with details, or None if OK
    """
    if not durations or len(durations) < 2:
        return False, None

    min_dur = min(durations)
    max_dur = max(durations)
    median_dur = np.median(durations)

    # Calculate variation from median
    variations = [(abs(d - median_dur) / median_dur) for d in durations]
    max_variation = max(variations)

    if max_variation > tolerance:
        warning_msg = (
            f"⚠ Duration mismatch detected!\n"
            f"  Experiments have different durations: {min_dur:.1f}s - {max_dur:.1f}s\n"
            f"  Variation: {max_variation*100:.1f}% (tolerance: {tolerance*100:.1f}%)\n"
            f"  This may cause inconsistent x-axis scaling."
        )
        return True, warning_msg

    return False, None
```

---

## 4. TUI Integration Plan

### 4.1 New Preset Selector Screen

**Create:** `src/tui/screens/its_preset_selector.py`

**Screen Flow Update:**
```
Step 3: Plot Type (ITS selected)
    ↓
Step 4: PRESET SELECTOR (NEW!)  ← User chooses preset
    ↓
Step 5a: Quick Mode (if preset = Dark/Power Sweep/Spectral)
         → Uses preset parameters
         → Shows what's pre-configured
    ↓
Step 5b: Custom Mode (if preset = Custom)
         → Shows full config screen
         → User sets all parameters manually
```

**Preset Selector UI:**

```
┌─────────────────────────────────────────────────────────┐
│             Choose ITS Plot Preset                      │
│           Alisson67 - ITS                               │
│                    [Step 4/8]                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Select a preset configuration:                         │
│                                                          │
│  ○ Dark Experiments                                     │
│    No illumination - noise/stability measurements       │
│    → No baseline, starts at t=1s, legend by VG         │
│                                                          │
│  ○ Power Sweep (Same λ)                                 │
│    Different LED powers, same wavelength                │
│    → Auto baseline (period/2), legend by LED voltage   │
│                                                          │
│  ○ Spectral Response (Same Power)                       │
│    Different wavelengths, same LED power                │
│    → Auto baseline (period/2), legend by wavelength    │
│                                                          │
│  ○ Custom                                               │
│    Fully configurable parameters                        │
│    → Configure all settings manually                    │
│                                                          │
│  [← Back]                 [Next →]                      │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Modified Config Screens

**Update `src/tui/screens/its_config.py`:**

When preset is NOT "Custom", show read-only summary:

```
┌─────────────────────────────────────────────────────────┐
│    Preset Configuration - Power Sweep (Same λ)          │
│           Alisson67 - ITS                               │
│                    [Step 5/8]                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✓ Preset Applied: Power Sweep (Same λ)                │
│                                                          │
│  Configuration:                                          │
│    • Baseline: Auto (LED period / 2)                    │
│    • Plot start: 20.0 s                                 │
│    • Legend by: LED voltage                             │
│    • Y-axis padding: 2%                                 │
│    • Duration check: Enabled (±10% tolerance)           │
│                                                          │
│  You can still apply filters:                           │
│    VG filter: [____]  (optional)                        │
│    Wavelength: [____] (optional)                        │
│    Date: [____]       (optional)                        │
│                                                          │
│  [← Back]  [Change Preset]  [Next: Select Experiments →]│
└─────────────────────────────────────────────────────────┘
```

### 4.3 Duration Warning in Preview Screen

**Update `src/tui/screens/preview_screen.py`:**

Add duration check before generation:

```python
# In PreviewScreen.compose() or on_mount()

# Check for duration mismatch if enabled
if config.get("check_duration_mismatch", False):
    durations = _get_experiment_durations(metadata_df, base_dir)
    has_mismatch, warning = _check_duration_mismatch(
        durations,
        tolerance=config.get("duration_tolerance", 0.10)
    )

    if has_mismatch:
        yield Static(
            f"⚠ {warning}",
            classes="warning-text"
        )
        yield Static(
            "Consider selecting experiments with similar durations.",
            classes="info-text"
        )
```

---

## 5. CLI Integration Plan

### 5.1 New `--preset` Flag

**Update `src/cli/commands/plot_its.py`:**

```python
@app.command()
def plot_its_command(
    chip: int,
    seq: Optional[str] = typer.Option(None, help="Comma-separated seq numbers"),
    # ... existing parameters ...

    # NEW preset system
    preset: Optional[str] = typer.Option(
        None,
        help="Use preset configuration: dark, light_power_sweep, light_spectral"
    ),

    # Existing parameters (overrideable)
    baseline: Optional[float] = typer.Option(None, help="Baseline time (overrides preset)"),
    legend_by: Optional[str] = typer.Option(None, help="Legend grouping (overrides preset)"),
    # ...
):
    """Generate ITS overlay plot."""

    # Load preset if specified
    if preset:
        if preset not in PRESETS:
            console.print(f"[red]Error:[/red] Unknown preset '{preset}'")
            console.print(f"Available presets: {', '.join(PRESETS.keys())}")
            raise typer.Exit(1)

        preset_config = PRESETS[preset]

        # Apply preset defaults (if not overridden by CLI flags)
        if baseline is None:
            if preset_config.baseline_mode == "none":
                baseline_mode = "none"
                baseline = None
            elif preset_config.baseline_mode == "auto":
                baseline_mode = "auto"
                baseline = None
            else:
                baseline_mode = "fixed"
                baseline = preset_config.baseline_value

        if legend_by is None:
            legend_by = preset_config.legend_by

        # Apply other preset settings
        plot_start_time = preset_config.plot_start_time
        check_duration = preset_config.check_duration_mismatch

        console.print(f"[green]✓[/green] Using preset: {preset_config.name}")
        console.print(f"  {preset_config.description}")
```

### 5.2 CLI Examples

```bash
# Dark experiments
python process_and_analyze.py plot-its 67 --seq 60,61,62 --preset dark

# Power sweep
python process_and_analyze.py plot-its 67 --seq 52,57,58 --preset light_power_sweep

# Spectral response
python process_and_analyze.py plot-its 67 --seq 10,11,12 --preset light_spectral

# Preset with override
python process_and_analyze.py plot-its 67 --seq 52,57,58 --preset light_spectral --baseline 80.0

# Show available presets
python process_and_analyze.py plot-its --list-presets
```

---

## 6. Implementation Phases

### Phase 1: Core Preset System (Backend)
**Files to create/modify:**
- ✅ Create `src/plotting/its_presets.py` - Preset definitions
- ✅ Modify `src/plotting/its.py`:
  - Add `baseline_mode`, `plot_start_time`, `check_duration_mismatch` parameters
  - Implement `_calculate_auto_baseline()`
  - Implement `_check_duration_mismatch()`
  - Update plotting logic to use configurable `plot_start_time`
  - Add duration warning to console output

**Testing:**
- Test auto baseline calculation from metadata
- Test duration mismatch detection
- Test all three baseline modes (fixed, auto, none)
- Test configurable plot_start_time

### Phase 2: CLI Integration
**Files to modify:**
- ✅ `src/cli/commands/plot_its.py`:
  - Add `--preset` option
  - Add `--list-presets` command
  - Add preset parameter mapping
  - Add CLI-specific duration warnings

**Testing:**
- Test all preset options via CLI
- Test parameter overrides
- Test duration warnings in console output

### Phase 3: TUI Integration - Preset Selector
**Files to create/modify:**
- ✅ Create `src/tui/screens/its_preset_selector.py`
- ✅ Modify `src/tui/screens/config_mode_selector.py`:
  - Route to preset selector instead of direct to config
- ✅ Modify `src/tui/app.py`:
  - Add preset to `plot_config` state

**Testing:**
- Test preset selector UI
- Test navigation flow
- Test state persistence

### Phase 4: TUI Integration - Config Screens
**Files to modify:**
- ✅ `src/tui/screens/its_config.py`:
  - Add preset-aware UI mode
  - Show read-only summary for presets
  - Allow filter configuration
- ✅ `src/tui/screens/preview_screen.py`:
  - Add duration mismatch warning display
  - Show preset name in configuration summary

**Testing:**
- Test preset display in config screen
- Test duration warnings in preview
- Test full wizard flow with presets

### Phase 5: Configuration Persistence
**Files to modify:**
- ✅ `src/tui/config_manager.py`:
  - Save preset name with configuration
  - Generate descriptions including preset info

**Testing:**
- Test config save/load with presets
- Test recent configs display

### Phase 6: Documentation
**Files to update:**
- ✅ `TUI_GUIDE.md` - Add preset selector step, update flow
- ✅ `CLI_GUIDE.md` - Add preset examples
- ✅ `CLAUDE.md` - Add preset system documentation
- ✅ `README.md` - Mention preset feature

---

## 7. Edge Cases and Considerations

### Edge Case 1: Mixed Experiment Types in Selection
**Problem:** User selects both dark and light experiments
**Solution:**
- Preset selector only appears after experiment selection
- Or: Allow preset, but warn if experiments don't match (e.g., "Dark preset but light experiments selected")

**Recommendation:** Keep preset selection BEFORE experiment selection, so user can filter appropriately.

### Edge Case 2: Missing LED Period Metadata
**Problem:** Auto baseline selected but "Laser ON+OFF period" not in metadata
**Solution:** Fall back to default 60.0s, show warning

### Edge Case 3: Duration Mismatch with Different Protocols
**Problem:** User mixing ITS experiments with different LED ON/OFF periods
**Solution:**
- Warning shows range of durations
- Suggest filtering by specific period
- Allow user to proceed anyway

### Edge Case 4: Preset Override in TUI
**Problem:** User wants to modify just one parameter from preset
**Solution:**
- "Change Preset" button to go back
- Or: Add "Advanced" toggle to show all fields as editable

**Recommendation:** Start with "Change Preset" button, add advanced toggle in future if needed.

---

## 8. Data Flow Diagram

```
┌─────────────────┐
│  User starts    │
│  ITS plotting   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Select Chip &   │
│  Plot Type      │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│  Preset Selector (NEW!)                 │
│  ○ Dark                                  │
│  ○ Power Sweep                           │
│  ○ Spectral                              │
│  ○ Custom                                │
└────┬────────────────────────────────────┘
     │
     ├─── Dark/Power/Spectral ────┐
     │                             │
     │                             v
     │                    ┌────────────────┐
     │                    │ Quick Config   │
     │                    │ (Preset params │
     │                    │  + filters)    │
     │                    └────────┬───────┘
     │                             │
     └─── Custom ─────────┐        │
                          │        │
                          v        │
                 ┌────────────────┐│
                 │ Full Config    ││
                 │ (All params)   ││
                 └────────┬───────┘│
                          │        │
                          v        v
                 ┌───────────────────┐
                 │ Experiment        │
                 │ Selection         │
                 └─────────┬─────────┘
                           │
                           v
                 ┌───────────────────┐
                 │ Preview           │
                 │ + Duration Check  │ ← NEW WARNING
                 └─────────┬─────────┘
                           │
                           v
                 ┌───────────────────┐
                 │ Generate Plot     │
                 │ (with preset      │
                 │  parameters)      │
                 └───────────────────┘
```

---

## 9. Testing Plan

### Unit Tests
- `test_its_presets.py`:
  - Test preset definitions valid
  - Test auto baseline calculation
  - Test duration mismatch detection
  - Test baseline modes (fixed/auto/none)

### Integration Tests
- `test_its_plotting_with_presets.py`:
  - Test plot generation with each preset
  - Test parameter overrides
  - Test duration warnings

### TUI Tests
- Manual testing checklist:
  - [ ] Preset selector navigation
  - [ ] Dark preset flow
  - [ ] Power sweep preset flow
  - [ ] Spectral preset flow
  - [ ] Custom preset flow
  - [ ] Duration warning display
  - [ ] Config persistence with presets

### CLI Tests
- Manual testing checklist:
  - [ ] `--preset dark`
  - [ ] `--preset light_power_sweep`
  - [ ] `--preset light_spectral`
  - [ ] Parameter overrides
  - [ ] `--list-presets`
  - [ ] Duration warnings in console

---

## 10. Success Criteria

### Must Have
- ✅ Three working presets (Dark, Power Sweep, Spectral)
- ✅ Auto baseline calculation from metadata
- ✅ Duration mismatch warnings
- ✅ TUI preset selector screen
- ✅ CLI `--preset` flag
- ✅ Documentation updated

### Should Have
- ✅ Preset persistence in saved configs
- ✅ Clear warnings and user feedback
- ✅ Graceful fallbacks for missing metadata

### Could Have
- ⏳ User-defined custom presets (JSON file)
- ⏳ Preset recommendation based on metadata
- ⏳ "Advanced mode" toggle in TUI

---

## 11. Timeline Estimate

**Phase 1 (Backend):** 2-3 hours
- Create preset definitions
- Modify plotting function
- Implement helper functions

**Phase 2 (CLI):** 1-2 hours
- Add CLI flags
- Test CLI integration

**Phase 3 (TUI Selector):** 2-3 hours
- Create preset selector screen
- Update navigation

**Phase 4 (TUI Config):** 2-3 hours
- Modify config screens
- Add warnings

**Phase 5 (Persistence):** 1 hour
- Update config manager

**Phase 6 (Documentation):** 1-2 hours
- Update all docs

**Total Estimate:** 9-14 hours

---

## 12. Next Steps

1. **Review this plan** - Confirm requirements and approach
2. **Start Phase 1** - Implement core preset system
3. **Iterate based on testing** - Adjust as needed
4. **Gradual rollout** - Test each phase before proceeding

---

**Questions for Review:**

1. Should preset selection happen BEFORE or AFTER experiment selection?
   - **Recommendation:** BEFORE (so user can filter experiments to match preset)

2. Should "Dark" preset completely disable baseline or just set it to 0?
   - **Recommendation:** Disable (skip interpolation step entirely)

3. What duration tolerance is appropriate (currently 10%)?
   - **Recommendation:** Start with 10%, make configurable

4. Should we support user-defined presets from JSON files?
   - **Recommendation:** Phase 2 feature, not MVP

5. How to handle preset in "Plot Another" workflow?
   - **Recommendation:** Preserve preset choice for next plot

---

**Ready to proceed with implementation?**
