# has_light Metadata Field - Implementation Plan

**Date:** October 22, 2025
**Status:** Planning Phase
**Purpose:** Add persistent `has_light` boolean field to metadata for proper ITS processing

---

## 1. Problem Statement

### Current Situation

**Issue:** Dark vs Light ITS experiments require different processing, but we can't reliably distinguish them until runtime.

**Current Detection (Runtime Only):**
- `with_light` column calculated in `load_and_prepare_metadata()` (src/core/utils.py:157-160)
- Based on `Laser toggle` field from metadata
- **NOT saved to metadata CSV files** - recalculated every time
- **NOT used anywhere in codebase** - calculated but ignored!

**Why This is a Problem:**
1. Can't filter experiments by light/dark BEFORE loading full data
2. Can't show light status in experiment selector (TUI/CLI)
3. Can't validate preset selection (e.g., "Dark" preset but light experiments selected)
4. Can't auto-recommend presets based on selected experiments
5. Users must manually know which experiments are dark vs light

### Required Behavior

**What we need:**
1. `has_light` boolean column **permanently stored** in metadata CSV files
2. Auto-detected during metadata parsing (from raw CSVs)
3. Displayed in chip history and experiment selector
4. Used for preset validation and recommendations
5. Robust detection algorithm (multiple fallback methods)

---

## 2. Detection Algorithm Design

### Detection Strategy (Multi-Method Fallback)

**Method 1: Laser Voltage from Metadata** (Primary)
```python
# From CSV #Parameters section
if "Laser voltage" in params:
    laser_voltage = float(params["Laser voltage"])
    has_light = (laser_voltage > 0.0)
```
- ✅ Most reliable - comes from experiment setup
- ✅ Already extracted by parser
- ⚠️ May not exist in old data

**Method 2: VL Column from Data** (Secondary)
```python
# Read measurement data and check VL column
df = _read_measurement(csv_path)
if "VL" in df.columns:
    vl_values = df["VL"].to_numpy()
    # Has light if VL ever goes above threshold (e.g., 0.1V)
    has_light = np.any(vl_values > 0.1)
```
- ✅ Direct evidence from measurement
- ✅ Works even if metadata missing
- ⚠️ Slower (requires reading full data file)
- ⚠️ VL column may not exist in very old data

**Method 3: Laser Wavelength Presence** (Tertiary)
```python
# If wavelength is specified and non-zero, assume light
if "Laser wavelength" in params:
    wavelength = float(params["Laser wavelength"])
    has_light = (wavelength > 0.0)
```
- ✅ Simple logical inference
- ⚠️ Less reliable (wavelength may be set but laser off)

**Method 4: LED ON+OFF Period** (Quaternary)
```python
# If experiment has defined light cycle, assume light
if "Laser ON+OFF period" in params:
    period = float(params["Laser ON+OFF period"])
    has_light = (period > 0.0)
```
- ✅ Indicates light protocol was configured
- ⚠️ Period may exist but laser voltage = 0

**Fallback Chain:**
```python
has_light = (
    detect_from_laser_voltage()      # Try method 1
    ?? detect_from_vl_data()         # Else try method 2
    ?? detect_from_wavelength()      # Else try method 3
    ?? detect_from_period()           # Else try method 4
    ?? None                           # Unknown if all fail
)
```

### Conservative vs Aggressive Detection

**Conservative (Recommended):**
- `has_light = True` only if **definitive evidence** (laser voltage > 0 OR VL data shows light)
- Mark as `None` if uncertain
- Safer for avoiding false positives

**Aggressive:**
- `has_light = True` if **any indicator** (wavelength set, period exists, etc.)
- Mark as `False` only if explicitly zero
- More user-friendly (fewer unknowns)

**Recommendation:** Use **Conservative** approach - better to show "Unknown" than misclassify.

---

## 3. Implementation Plan

### 3.1 Update Parser to Detect has_light

**Modify:** `src/core/parser.py`

**Add new function:**
```python
def _detect_has_light(params: Dict[str, object], csv_path: Path) -> bool | None:
    """
    Detect if experiment has light illumination.

    Detection strategy (in order):
    1. Laser voltage > 0
    2. VL column in data shows light (any value > 0.1V)
    3. Laser wavelength > 0 (less reliable)
    4. LED ON+OFF period > 0 (least reliable)

    Returns
    -------
    bool or None
        True if light detected, False if explicitly dark, None if unknown
    """
    import numpy as np

    # Method 1: Laser voltage (most reliable)
    laser_voltage = params.get("Laser voltage")
    if isinstance(laser_voltage, (int, float)):
        if laser_voltage > 0.0:
            return True
        else:
            return False  # Explicitly set to 0 = dark

    # Method 2: Check VL column in data (requires reading file)
    try:
        df = _read_measurement(csv_path)
        if "VL" in df.columns:
            vl_values = df["VL"].to_numpy()
            # Remove NaN values
            vl_clean = vl_values[~np.isnan(vl_values)]
            if len(vl_clean) > 0:
                # Has light if any VL value > 0.1V
                if np.any(vl_clean > 0.1):
                    return True
                # All values <= 0.1V = dark
                elif np.all(vl_clean <= 0.1):
                    return False
    except Exception as e:
        # If data read fails, continue to other methods
        print(f"[debug] Could not read VL data from {csv_path.name}: {e}")
        pass

    # Method 3: Laser wavelength (less reliable)
    wavelength = params.get("Laser wavelength")
    if isinstance(wavelength, (int, float)) and wavelength > 0:
        # Wavelength set, likely has light (but not certain)
        return True

    # Method 4: LED period (least reliable, but indicates light protocol)
    period = params.get("Laser ON+OFF period")
    if isinstance(period, (int, float)) and period > 0:
        # Period exists, suggests light experiment (but not guaranteed)
        return True

    # Unknown if all methods fail
    return None
```

**Update `parse_iv_metadata()`:**
```python
def parse_iv_metadata(csv_path: Path) -> Dict[str, object]:
    """
    Read the '#Parameters' and '#Metadata' header blocks of a .csv and return a flat dict.
    """
    # ... existing code ...

    # Derive optional fields (existing logic)
    lv = params.get("Laser voltage")
    if isinstance(lv, (int, float)):
        params["Laser toggle"] = (lv != 0.0)

    # NEW: Detect has_light
    params["has_light"] = _detect_has_light(params, csv_path)

    # Add file path always
    params["source_file"] = str(csv_path)

    # ... rest of existing code ...
```

### 3.2 Update Metadata Schema

**Current metadata columns:**
- Chip number, VG, VDS, Laser voltage, Laser wavelength, Laser ON+OFF period
- start_time, time_hms, source_file
- Laser toggle (derived, boolean)

**NEW column to add:**
- `has_light` (boolean or None)

**Polars schema:**
```python
# In write_metadata_csv()
df = pl.DataFrame(records)

# Ensure has_light column is properly typed
if "has_light" in df.columns:
    df = df.with_columns(
        pl.col("has_light").cast(pl.Boolean)  # or pl.Utf8 if allowing None
    )
```

**Handling None values:**

Option 1: Boolean + Null
```python
# has_light: bool | null
# Polars: pl.Boolean with nulls allowed
```

Option 2: String ("True", "False", "Unknown")
```python
# has_light: str
# Easier to display, but less type-safe
```

**Recommendation:** Use **Boolean with nulls** for storage, convert to string for display.

### 3.3 Update Timeline/History Functions

**Modify:** `src/core/timeline.py`

**Add has_light to chip history output:**
```python
def build_chip_history(
    metadata_dir: Path,
    raw_data_dir: Path,
    chip_number: int,
    chip_group_name: str = "Alisson",
    proc_filter: Optional[str] = None,
) -> pl.DataFrame:
    """Build complete chronological history for a specific chip."""
    # ... existing code ...

    # Add has_light column if available
    if "has_light" in combined.columns:
        summary_parts.append(_format_has_light(row))

    # ... existing code ...

def _format_has_light(row: dict) -> str:
    """Format has_light for display."""
    has_light = row.get("has_light")
    if has_light is True:
        return "💡"  # Light bulb emoji
    elif has_light is False:
        return "🌙"  # Moon emoji (dark)
    else:
        return "❓"  # Question mark (unknown)
```

**Display in chip history table:**
```
seq  date        time      proc  VG    λ     💡/🌙  summary
52   2025-10-15  14:23:45  ITS  -3.0  455nm  💡    ITS @ Vg=-3.0V, λ=455nm, P=3.5V ...
60   2025-10-16  09:15:22  ITS  -3.0   -     🌙    ITS @ Vg=-3.0V (dark) ...
```

### 3.4 Update Experiment Selector (TUI)

**Modify:** `src/tui/screens/experiment_selector.py`

**Add has_light column to table:**
```python
# In _populate_table()
table.add_column("💡", width=3)  # Light/dark indicator
table.add_column("seq", width=5)
table.add_column("date", width=12)
# ... existing columns ...

# When adding rows:
light_indicator = _get_light_indicator(row["has_light"])
table.add_row(
    light_indicator,  # 💡 or 🌙 or ❓
    str(seq),
    date_str,
    # ... existing columns ...
)

def _get_light_indicator(has_light: bool | None) -> str:
    """Get emoji indicator for light status."""
    if has_light is True:
        return "💡"
    elif has_light is False:
        return "🌙"
    else:
        return "❓"
```

**Filter options:**
```python
# Add filter buttons
with Horizontal():
    yield Button("All", id="filter-all")
    yield Button("💡 Light Only", id="filter-light")
    yield Button("🌙 Dark Only", id="filter-dark")
```

### 3.5 Update CLI Experiment Display

**Modify:** `src/cli/commands/history.py`

**Add has_light to history display:**
```python
# In show_history_command()
# Add column to rich table
table.add_column("💡", justify="center", width=3)

# Add data
for row in history.iter_rows(named=True):
    light_indicator = get_light_indicator(row.get("has_light"))
    table.add_row(
        light_indicator,
        str(row["seq"]),
        # ... existing columns ...
    )
```

### 3.6 Integration with Preset System

**Modify:** `src/plotting/its_presets.py` (from previous plan)

**Add preset validation:**
```python
def validate_preset_for_experiments(
    preset: ITSPreset,
    df: pl.DataFrame
) -> tuple[bool, Optional[str]]:
    """
    Validate that selected experiments match preset expectations.

    Returns
    -------
    is_valid : bool
        True if experiments match preset
    warning_msg : str or None
        Warning message if mismatch detected
    """
    if "has_light" not in df.columns:
        return True, None  # Can't validate, allow

    has_light_values = df["has_light"].to_list()

    # Dark preset should only have dark experiments
    if preset.name == "Dark Experiments":
        if any(hl is True for hl in has_light_values):
            light_count = sum(1 for hl in has_light_values if hl is True)
            return False, (
                f"⚠ Dark preset selected but {light_count} light experiment(s) detected!\n"
                f"   Consider using 'Light' preset or filtering for dark experiments only."
            )

    # Light presets should only have light experiments
    elif "Light" in preset.name:
        if any(hl is False for hl in has_light_values):
            dark_count = sum(1 for hl in has_light_values if hl is False)
            return False, (
                f"⚠ Light preset selected but {dark_count} dark experiment(s) detected!\n"
                f"   Consider using 'Dark' preset or filtering for light experiments only."
            )

    return True, None
```

**Add auto-preset recommendation:**
```python
def recommend_preset(df: pl.DataFrame) -> str:
    """
    Recommend preset based on selected experiments.

    Returns
    -------
    str
        Preset key ("dark", "light_power_sweep", "light_spectral", "custom")
    """
    if "has_light" not in df.columns:
        return "custom"

    has_light_values = df["has_light"].to_list()

    # All dark → recommend dark preset
    if all(hl is False for hl in has_light_values if hl is not None):
        return "dark"

    # All light → check if power sweep or spectral
    if all(hl is True for hl in has_light_values if hl is not None):
        # Check if wavelengths are same (power sweep)
        if "Laser wavelength" in df.columns:
            wavelengths = df["Laser wavelength"].unique().to_list()
            if len(wavelengths) == 1:
                return "light_power_sweep"
            elif len(wavelengths) > 1:
                return "light_spectral"

    # Mixed or unknown → custom
    return "custom"
```

---

## 4. Migration Strategy for Existing Metadata

### Problem: Existing metadata files don't have has_light column

**Options:**

**Option 1: Regenerate All Metadata (Recommended)**
```bash
# Use existing parse-all command
python process_and_analyze.py parse-all --raw raw_data --meta metadata

# This will overwrite existing metadata with updated schema
```
- ✅ Clean, ensures consistency
- ✅ Uses updated detection algorithm
- ⚠️ Overwrites existing metadata (backup first!)

**Option 2: Backfill has_light Column**

Create migration script:
```python
# tools/migrate_add_has_light.py
"""
Add has_light column to existing metadata files.
"""

def migrate_metadata_file(meta_csv: Path, raw_data_dir: Path):
    """Add has_light column to existing metadata CSV."""
    df = pl.read_csv(meta_csv)

    # Skip if already has column
    if "has_light" in df.columns:
        print(f"✓ {meta_csv.name} already has has_light column")
        return

    # Calculate has_light for each row
    has_light_values = []
    for row in df.iter_rows(named=True):
        source_file = row["source_file"]
        csv_path = raw_data_dir / source_file

        # Re-parse to detect has_light
        params = parse_iv_metadata(csv_path)
        has_light_values.append(params.get("has_light"))

    # Add column
    df = df.with_columns(
        pl.Series("has_light", has_light_values)
    )

    # Save
    df.write_csv(meta_csv)
    print(f"✓ Updated {meta_csv.name} with has_light column")

# Run on all metadata files
for meta_file in Path("metadata").rglob("metadata.csv"):
    migrate_metadata_file(meta_file, Path("raw_data"))
```

**Option 3: Dynamic Calculation (Fallback)**

If metadata missing column, calculate at runtime:
```python
# In load_and_prepare_metadata()
if "has_light" not in df.columns:
    print("[info] has_light column missing, calculating from Laser toggle...")
    df = df.with_columns([
        pl.when(pl.col("Laser toggle").cast(pl.Utf8).str.to_lowercase() == "true")
          .then(pl.lit(True))
          .otherwise(pl.lit(False))
          .alias("has_light")
    ])
```

**Recommendation:** Use **Option 1** (regenerate) for clean migration.

---

## 5. Testing Plan

### Unit Tests

**Test detection algorithm:**
```python
# test_has_light_detection.py

def test_detect_light_from_voltage():
    params = {"Laser voltage": 3.5}
    result = _detect_has_light(params, dummy_path)
    assert result is True

def test_detect_dark_from_voltage():
    params = {"Laser voltage": 0.0}
    result = _detect_has_light(params, dummy_path)
    assert result is False

def test_detect_from_vl_data():
    # Mock CSV with VL column showing light
    params = {}  # No laser voltage
    result = _detect_has_light(params, path_to_light_csv)
    assert result is True

def test_detect_unknown():
    params = {}  # No indicators
    result = _detect_has_light(params, path_to_minimal_csv)
    assert result is None
```

**Test preset validation:**
```python
def test_validate_dark_preset_with_light_data():
    dark_preset = PRESETS["dark"]
    df = pl.DataFrame({"has_light": [True, True]})
    is_valid, msg = validate_preset_for_experiments(dark_preset, df)
    assert is_valid is False
    assert "Dark preset" in msg
```

### Integration Tests

**Test full metadata pipeline:**
```python
def test_metadata_generation_includes_has_light():
    # Parse raw CSV
    params = parse_iv_metadata(test_csv_path)

    # Check has_light exists
    assert "has_light" in params
    assert isinstance(params["has_light"], (bool, type(None)))

def test_chip_history_shows_light_status():
    history = build_chip_history(meta_dir, raw_dir, 67, "Alisson")
    assert "has_light" in history.columns
```

### Manual Testing

**Checklist:**
- [ ] Parse metadata from raw CSVs → has_light populated
- [ ] View chip history → light/dark indicators shown
- [ ] TUI experiment selector → 💡🌙 column visible
- [ ] CLI history command → light indicators shown
- [ ] Filter experiments by light/dark in TUI
- [ ] Preset validation warns on mismatch
- [ ] Auto-recommend preset based on selection

---

## 6. Implementation Phases

### Phase 1: Parser Update (1-2 hours)
- ✅ Add `_detect_has_light()` function
- ✅ Update `parse_iv_metadata()` to call detection
- ✅ Test detection with sample CSVs (light, dark, unknown)
- ✅ Regenerate metadata for one test folder

### Phase 2: Display Integration (1-2 hours)
- ✅ Update chip history to show light indicators
- ✅ Update CLI history command
- ✅ Test display in terminal

### Phase 3: TUI Integration (2-3 hours)
- ✅ Add 💡 column to experiment selector
- ✅ Add filter buttons (All/Light/Dark)
- ✅ Test filtering and selection

### Phase 4: Preset Integration (1-2 hours)
- ✅ Add preset validation function
- ✅ Add auto-recommendation function
- ✅ Integrate into TUI preset flow
- ✅ Test validation warnings

### Phase 5: Migration (1 hour)
- ✅ Backup existing metadata
- ✅ Regenerate all metadata with has_light
- ✅ Verify all files have column

### Phase 6: Documentation (1 hour)
- ✅ Update CLAUDE.md with has_light field
- ✅ Update TUI_GUIDE.md with filter options
- ✅ Update CLI_GUIDE.md with light indicators

**Total: 7-11 hours**

---

## 7. Example Outputs

### Before (Current)
```bash
$ python process_and_analyze.py show-history 67

seq  date        time      proc  VG    λ      summary
52   2025-10-15  14:23:45  ITS  -3.0  455nm  ITS @ Vg=-3.0V, λ=455nm...
60   2025-10-16  09:15:22  ITS  -3.0   -     ITS @ Vg=-3.0V...
```

### After (With has_light)
```bash
$ python process_and_analyze.py show-history 67

💡  seq  date        time      proc  VG    λ      summary
💡  52   2025-10-15  14:23:45  ITS  -3.0  455nm  ITS @ Vg=-3.0V, λ=455nm...
🌙  60   2025-10-16  09:15:22  ITS  -3.0   -     ITS @ Vg=-3.0V (dark)...
❓  61   2025-10-16  10:30:11  ITS  -2.0   -     ITS @ Vg=-2.0V...
```

### TUI Experiment Selector (After)
```
┌─────────────────────────────────────────────────────────────┐
│  Select ITS Experiments - Chip 67                          │
├─────────────────────────────────────────────────────────────┤
│  [All] [💡 Light Only] [🌙 Dark Only]                      │
├─────────────────────────────────────────────────────────────┤
│  💡  seq  date        time      VG    λ      summary        │
│  ✓💡  52   2025-10-15  14:23:45 -3.0  455nm  ITS...        │
│   💡  57   2025-10-16  08:15:22 -3.0  455nm  ITS...        │
│  ✓🌙  60   2025-10-16  09:15:22 -3.0   -     ITS (dark)... │
│   ❓  61   2025-10-16  10:30:11 -2.0   -     ITS...        │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Success Criteria

### Must Have
- ✅ `has_light` column in all metadata CSV files
- ✅ Auto-detection working (laser voltage + VL data)
- ✅ Display in chip history (💡🌙❓ indicators)
- ✅ Display in TUI experiment selector
- ✅ Display in CLI history output

### Should Have
- ✅ Filter experiments by light/dark in TUI
- ✅ Preset validation based on has_light
- ✅ Auto-recommend preset based on experiments
- ✅ Graceful handling of None/unknown values

### Could Have
- ⏳ Auto-detect from experiment duration patterns
- ⏳ Machine learning classification (overkill!)
- ⏳ Edit light status in TUI (manual override)

---

## 9. Edge Cases

### Edge Case 1: VL Data Noisy
**Problem:** VL column has noise, small non-zero values even when dark
**Solution:** Use threshold (0.1V) instead of exact zero check

### Edge Case 2: Missing Laser Voltage
**Problem:** Old data doesn't have "Laser voltage" parameter
**Solution:** Fall back to VL data reading, then wavelength

### Edge Case 3: Contradictory Indicators
**Problem:** Laser voltage = 0 but VL data shows light
**Solution:** VL data takes precedence (actual measurement > metadata)

### Edge Case 4: Very Slow Detection
**Problem:** Reading VL data from thousands of files is slow
**Solution:**
- Cache results during initial parse
- Only read VL if laser voltage missing
- Add progress bar for bulk regeneration

---

## 10. Questions for Review

1. **Detection method priority:** Is "Laser voltage → VL data → Wavelength → Period" the right order?
   - **Recommendation:** Yes - most reliable to least reliable

2. **Threshold for VL:** Is 0.1V a good threshold for detecting light?
   - **Recommendation:** Yes, but make configurable

3. **None vs False:** Should we use `None` for unknown or default to `False`?
   - **Recommendation:** Use `None` - more explicit about uncertainty

4. **Migration strategy:** Regenerate all metadata or backfill?
   - **Recommendation:** Regenerate (cleaner)

5. **Performance:** OK to read VL data during parsing (slower) or skip for speed?
   - **Recommendation:** Read VL as fallback only, cache results

---

**Ready to proceed with implementation?**

This feature will integrate perfectly with the preset system - we can validate that "Dark" preset is only used with dark experiments, and auto-recommend presets based on the selected experiments' light status!
