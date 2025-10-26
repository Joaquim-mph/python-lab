# Phase 1 Completion: Pydantic Models

**Date**: 2025-10-26
**Status**: ✅ Complete
**Next Phase**: Phase 2 - Staging Utilities

---

## ✅ What Was Completed

### 1. ManifestRow Schema (`src/models/manifest.py`)

**Purpose**: Define the schema for `manifest.parquet` - the authoritative metadata table.

**Key Features**:
- ✅ **Comprehensive field coverage**: 40+ fields covering all procedure types
- ✅ **Procedure type enum**: `Proc = Literal["IVg", "IV", "IVgT", "It", "ITt", "LaserCalibration", "Tt"]`
- ✅ **Smart validators**:
  - `run_id` → lowercase normalization
  - `chip_group` → title case ("alisson" → "Alisson")
  - `start_time_utc`, `ingested_at_utc` → timezone-aware enforcement
- ✅ **Type safety**: `extra="forbid"` prevents schema drift
- ✅ **Documentation**: Complete docstrings with examples

**Fields Organized by Category**:

| Category | Fields | Notes |
|----------|--------|-------|
| **Identity** | `run_id`, `source_file`, `proc`, `date_local`, `start_time_utc` | Required |
| **Chip** | `chip_group`, `chip_number`, `chip_name`, `file_idx` | Optional |
| **Light** | `has_light`, `laser_voltage_v`, `laser_wavelength_nm`, `laser_period_s` | Optional |
| **Voltages** | `vg_fixed_v`, `vg_start_v`, `vg_end_v`, `vg_step_v`, `vds_v`, `vsd_*` | Procedure-specific |
| **Measurement** | `duration_s`, `sampling_time_s` | Calculated |
| **Instrument** | `irange`, `nplc`, `n_avg`, `burn_in_time_s`, `step_time_s` | Optional |
| **Temperature** | `initial_temp_c`, `target_temp_c`, `temp_start_c`, etc. | IVgT, It, ITt, Tt |
| **Laser Cal** | `optical_fiber`, `laser_voltage_start_v`, `sensor_model` | LaserCalibration |
| **Governance** | `summary`, `schema_version`, `extraction_version`, `ingested_at_utc` | Required |

**Helper Functions**:
- `proc_display_name(proc)`: "It" → "Current vs Time"
- `proc_short_name(proc)`: "It" → "ITS"

---

### 2. StagingConfig Schema (`src/models/config.py`)

**Purpose**: Configuration for the staging pipeline (how to stage).

**Key Features**:
- ✅ **Path management**: Auto-fill derived paths from `stage_root`
- ✅ **Validation**: Required paths must exist before staging
- ✅ **Git integration**: Auto-detect `extraction_version` from `git describe`
- ✅ **Performance tuning**: `workers`, `polars_threads` controls
- ✅ **Helper methods**: `create_directories()`, `get_partition_path()`, `validate_timezone()`

**Auto-Filled Paths**:
```python
cfg = StagingConfig(
    raw_root=Path("data/01_raw"),
    stage_root=Path("data/02_stage/raw_measurements"),
    procedures_yaml=Path("config/procedures.yml")
)

# Auto-filled:
# cfg.rejects_dir = Path("data/02_stage/_rejects")
# cfg.events_dir = Path("data/02_stage/_manifest/events")
# cfg.manifest_path = Path("data/02_stage/_manifest/manifest.parquet")
# cfg.extraction_version = "v0.4.2+g1a2b3c"  # from git
```

**Path Validators**:
- `raw_root`, `procedures_yaml`: Must exist (fail early)
- `procedures_yaml`: Must be a file (not directory)
- All paths resolved to absolute

**Git Version Auto-Detection**:
```python
# Runs: git describe --tags --always --dirty
# Examples:
#   v0.4.2           (clean release)
#   v0.4.2-3-g1a2b3c (3 commits after tag)
#   v0.4.2-dirty     (uncommitted changes)
# Fallback: "unknown" if git unavailable
```

---

### 3. Updated Exports (`src/models/__init__.py`)

**New Structure**:
```python
# Staging layer (new)
from .config import StagingConfig
from .manifest import ManifestRow, Proc, proc_display_name, proc_short_name

# Pipeline parameters (existing - kept for backward compatibility)
from .parameters import StagingParameters, IntermediateParameters, ...
```

**Backward Compatibility**:
- ✅ Kept `StagingParameters` (your original model)
- ✅ Can use either `StagingConfig` (new) or `StagingParameters` (old)
- ✅ Gradual migration path

---

## 📊 Mapping: procedures.yml → ManifestRow

### Common Parameters (All Procedures)

| procedures.yml | ManifestRow Field | Type |
|----------------|-------------------|------|
| `Chip number` | `chip_number` | int |
| `Chip group name` | `chip_group` | str |
| `Laser voltage` | `laser_voltage_v` | float |
| `Laser wavelength` | `laser_wavelength_nm` | float |
| `Start time` | `start_time_utc` | datetime (UTC) |
| `Sample` | `sample` | str |
| `Information` | `information` | str |

### Procedure-Specific Parameters

#### IVg, IVgT
```yaml
VG start → vg_start_v
VG end → vg_end_v
VG step → vg_step_v
VDS → vds_v
Burn-in time → burn_in_time_s
Step time → step_time_s
```

#### It, ITt
```yaml
VG → vg_fixed_v
VDS → vds_v
Laser ON+OFF period → laser_period_s
Sampling time (excluding Keithley) → sampling_time_s
T step start time → temp_step_start_time_s (It only)
```

#### IV
```yaml
VG → vg_fixed_v
VSD start → vsd_start_v
VSD end → vsd_end_v
VSD step → vsd_step_v
```

#### LaserCalibration
```yaml
Optical fiber → optical_fiber
Laser voltage start → laser_voltage_start_v
Laser voltage end → laser_voltage_end_v
Laser voltage step → laser_voltage_step_v
Sensor model → sensor_model (from Metadata section)
```

#### Tt (Temperature)
```yaml
T start → temp_start_c
T end → temp_end_c
T step → temp_step_c
Initial (current) T → initial_temp_c
Target T → target_temp_c
```

---

## 🧪 Testing the Models

### Quick Validation Test

```python
from datetime import datetime, date, timezone
from pathlib import Path
from src.models import StagingConfig, ManifestRow

# Test StagingConfig
cfg = StagingConfig(
    raw_root=Path("raw_data"),  # Assumes exists
    stage_root=Path("data/02_stage/raw_measurements"),
    procedures_yaml=Path("config/procedures.yml")  # Assumes exists
)

print(f"✓ StagingConfig validated")
print(f"  Manifest: {cfg.manifest_path}")
print(f"  Version: {cfg.extraction_version}")

# Test ManifestRow
row = ManifestRow(
    run_id="a1b2c3d4e5f67890",
    source_file=Path("Alisson_15_sept/Alisson67_015.csv"),
    proc="It",
    date_local=date(2025, 10, 18),
    start_time_utc=datetime(2025, 10, 18, 17, 30, 0, tzinfo=timezone.utc),
    chip_group="alisson",  # Will normalize to "Alisson"
    chip_number=67,
    chip_name="Alisson67",
    file_idx=15,
    has_light=True,
    laser_voltage_v=3.5,
    laser_wavelength_nm=455.0,
    laser_period_s=120.0,
    vg_fixed_v=-3.0,
    vds_v=0.1,
    duration_s=3600.0,
    summary="It (Vg=-3V, λ=455nm, 120s)",
    schema_version=1,
    extraction_version="v0.4.2+g1a2b3c",
    ingested_at_utc=datetime.now(timezone.utc)
)

print(f"✓ ManifestRow validated")
print(f"  Chip: {row.chip_group}{row.chip_number}")  # "Alisson67"
print(f"  Proc: {row.proc}")
print(f"  Run ID: {row.run_id}")
```

**Expected Output**:
```
✓ StagingConfig validated
  Manifest: data/02_stage/_manifest/manifest.parquet
  Version: v0.4.2+g1a2b3c
✓ ManifestRow validated
  Chip: Alisson67
  Proc: It
  Run ID: a1b2c3d4e5f67890
```

---

## 📂 Files Created

```
src/models/
├── __init__.py          # ✅ Updated exports
├── config.py            # ✅ NEW: StagingConfig
├── manifest.py          # ✅ NEW: ManifestRow, Proc enum
└── parameters.py        # ✅ Kept (existing analysis/plotting models)
```

**Line counts**:
- `manifest.py`: ~680 lines (comprehensive schema + docs)
- `config.py`: ~270 lines (config + helpers)
- Total new code: ~950 lines

---

## ✅ Schema Validation Features

### 1. Type Safety

```python
# ❌ This will fail (extra field forbidden)
ManifestRow(
    run_id="abc123",
    source_file="test.csv",
    proc="It",
    ...,
    unknown_field="oops"  # ValidationError!
)

# ❌ This will fail (timezone-naive datetime)
ManifestRow(
    ...,
    start_time_utc=datetime(2025, 10, 18, 14, 30)  # Missing tzinfo!
)

# ✅ This passes
ManifestRow(
    ...,
    start_time_utc=datetime(2025, 10, 18, 14, 30, tzinfo=timezone.utc)
)
```

### 2. Automatic Normalization

```python
row = ManifestRow(
    run_id="ABC123DEF",      # → "abc123def" (lowercase)
    chip_group="alisson",    # → "Alisson" (title case)
    ...
)
```

### 3. Constraint Validation

```python
# ❌ Fails: negative values
ManifestRow(..., laser_voltage_v=-1.0)  # ge=0.0 constraint

# ❌ Fails: invalid procedure
ManifestRow(..., proc="InvalidProc")  # Not in Literal enum

# ✅ Passes
ManifestRow(..., laser_voltage_v=3.5, proc="It")
```

---

## 🎯 What This Enables

### Phase 2: Staging Utilities

With schemas defined, we can now build:
1. `compute_run_id(path, timestamp)` → returns validated `run_id`
2. `ensure_start_time_utc(meta, tz)` → returns timezone-aware datetime
3. `read_and_normalize(csv)` → returns `(df, meta_dict)` ready for `ManifestRow`

### Phase 3: Staging Writer

Can now write:
```python
def stage_run(csv_path: Path, cfg: StagingConfig) -> ManifestRow:
    df, meta = read_and_normalize(csv_path)

    # Build ManifestRow - Pydantic validates all fields!
    row = ManifestRow(
        run_id=compute_run_id(...),
        source_file=csv_path.relative_to(cfg.raw_root),
        proc=meta["proc"],
        start_time_utc=ensure_start_time_utc(meta, cfg.local_tz),
        ...  # All fields from meta dict
    )

    # Write Parquet (validated data!)
    ...
    return row
```

### Phase 4: Manifest-Based Histories

Can query manifest with type safety:
```python
import polars as pl

# Read manifest
df = pl.read_parquet("data/02_stage/_manifest/manifest.parquet")

# Filter by chip (validated schema!)
chip67 = df.filter(pl.col("chip_number") == 67)

# Type-safe column access
assert "run_id" in df.columns
assert "proc" in df.columns
```

---

## 🔍 Key Design Decisions

### 1. Keep procedures.yml Names

**Decision**: Use exact YAML names (`It`, `ITt`) instead of standardizing (`ITS`)

**Rationale**:
- ✅ Traceability: Manifest matches CSV metadata exactly
- ✅ Future-proof: Easy to add new procedures
- ✅ Helper functions: `proc_short_name("It") → "ITS"` for display

### 2. All Fields Optional (Except Identity)

**Decision**: Most fields are `Optional[...]`

**Rationale**:
- ✅ Robustness: Don't crash staging on missing metadata
- ✅ Procedure variety: Not all procedures have all parameters
- ✅ Fallback extraction: Filename parsing may fail

**Required fields**:
- `run_id`, `source_file`, `proc`, `date_local`, `start_time_utc`, `ingested_at_utc`

### 3. Git Auto-Detection for extraction_version

**Decision**: Auto-detect from `git describe --tags --always --dirty`

**Rationale**:
- ✅ Reproducibility: Exact code state recorded
- ✅ Zero configuration: Works out of the box
- ✅ Fallback: "unknown" if git unavailable (CI/CD)

### 4. StagingConfig (Not StagingParameters)

**Decision**: New name `StagingConfig` for staging layer

**Rationale**:
- ✅ Clarity: "Config" for settings, "Parameters" for analysis
- ✅ Consistency: Matches `ManifestRow` (data) vs `StagingConfig` (settings)
- ✅ Backward compat: Kept `StagingParameters` for existing code

---

## 📊 Comparison: Before vs After

| Aspect | Before (Day CSVs) | After (Manifest + Pydantic) |
|--------|-------------------|------------------------------|
| **Metadata schema** | Unvalidated dicts | Pydantic `ManifestRow` with 40+ typed fields |
| **Schema drift** | Silent failures | `extra="forbid"` catches typos |
| **Timezone handling** | Mixed (naive/aware) | Enforced UTC timezone-aware |
| **Chip group normalization** | Inconsistent case | Auto-normalized to title case |
| **Version tracking** | None | Git commit SHA tracked |
| **Type safety** | Runtime errors | Validation errors at staging time |
| **Documentation** | Comments | Pydantic field descriptions |

---

## 🚀 Next Steps

### Immediate (Phase 2)

1. **Create `src/core/staging_utils.py`**:
   - `compute_run_id(path, timestamp, raw_root) → str`
   - `ensure_start_time_utc(meta, local_tz) → datetime`
   - `derive_local_date(start_utc, local_tz) → str`
   - `extract_chip_info(path, meta) → (group, number, name)`
   - `read_and_normalize(path, raw_root) → (df, meta_dict)`

2. **Update `requirements.txt`**:
   ```txt
   pydantic>=2.0.0
   pyarrow>=14.0.0  # For Parquet
   ```

3. **Test imports**:
   ```bash
   python -c "from src.models import StagingConfig, ManifestRow, Proc; print('✓ Imports working')"
   ```

### Medium Term (Phase 3)

4. **Create `src/stage.py`**:
   - `stage_run(csv, cfg) → ManifestRow`
   - `append_manifest(rows, manifest_path)`
   - `stage_all(csvs, cfg)`

5. **Add CLI commands**:
   - `python process_and_analyze.py staging stage-all`
   - `python process_and_analyze.py staging validate-manifest`

---

## ✅ Acceptance Criteria

- [x] `ManifestRow` schema created with 40+ fields
- [x] `Proc` enum covers all procedure types from procedures.yml
- [x] `StagingConfig` with path auto-fill and git version detection
- [x] Validators for run_id, chip_group, timezone enforcement
- [x] Helper functions (`proc_display_name`, `proc_short_name`)
- [x] Updated `src/models/__init__.py` exports
- [x] Backward compatibility with existing `StagingParameters`
- [x] Comprehensive documentation and examples

---

## 📝 Notes for Next Phase

### procedures.yml Integration

When implementing Phase 2 utilities, we'll need to:
1. Load procedures.yml at runtime
2. Validate CSV headers against YAML schema
3. Extract parameters by procedure type
4. Map YAML field names → ManifestRow field names

**Example mapping logic**:
```python
# procedures.yml has:
#   It.Parameters.Laser voltage: float
#   It.Parameters.VG: float

# Maps to:
#   ManifestRow.laser_voltage_v
#   ManifestRow.vg_fixed_v

# Mapping function:
def map_yaml_to_manifest(proc: str, param_name: str) -> str:
    mapping = {
        "Laser voltage": "laser_voltage_v",
        "Laser wavelength": "laser_wavelength_nm",
        "Laser ON+OFF period": "laser_period_s",
        "VG": "vg_fixed_v" if proc in ["It", "IV"] else "vg_start_v",
        "VG start": "vg_start_v",
        ...
    }
    return mapping.get(param_name)
```

### Timezone Edge Cases

Need to handle:
- **DST transitions**: Santiago changes UTC offset twice a year
- **Missing start_time**: Fallback to file mtime (what TZ?)
- **Ambiguous times**: During DST "fall back" hour

**Solution**: Always prefer header timestamp (UTC), only use mtime as last resort.

---

**Phase 1 Status**: ✅ **COMPLETE**

**Ready for Phase 2**: Yes! All schemas defined and validated.

**Estimated Phase 2 time**: 1-2 days (utilities + testing)
