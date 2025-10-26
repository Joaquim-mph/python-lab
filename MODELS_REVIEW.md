# Pydantic Models Review & Recommendations

**Date**: 2025-10-26
**Status**: Phase 1 Review
**Reviewer**: Claude Code

---

## 📋 Summary

**What you have**: Excellent pipeline parameter models for staging, analysis, and plotting.
**What's missing**: **ManifestRow** schema (the core metadata schema for the manifest table).

Your `StagingParameters` is very well done! It's actually **more comprehensive** than the basic example in the implementation plan. However, for the staging-first architecture to work, we need:

1. ✅ **StagingParameters** (you have this - excellent!)
2. ❌ **ManifestRow** (missing - critical for manifest.parquet schema)
3. ⚠️ **Rename consideration**: `StagingParameters` → `StagingConfig` (aligns with plan)

---

## ✅ What You Have (Excellent!)

### `StagingParameters` (src/models/parameters.py)

**Strengths**:
- ✅ Comprehensive path handling with auto-fill defaults
- ✅ Excellent field validators (`path_must_exist`, `yaml_must_be_file`)
- ✅ `extra="forbid"` (prevents schema drift)
- ✅ Good documentation with examples
- ✅ Proper type hints and constraints (ge/le)
- ✅ Includes `procedures_yaml` path (smart addition!)
- ✅ `only_yaml_data` flag for strict schema enforcement

**Minor suggestions**:
1. **Naming**: Consider `StagingConfig` instead of `StagingParameters` to match the implementation plan
2. **extraction_version**: Add this field to track parser version (see below)

### `procedures.yml` Schema

**Excellent structure!** This maps perfectly to CSV validation. I see you have:
- ✅ Clear procedure types: `IVg`, `IV`, `IVgT`, `It`, `ITt`, `LaserCalibration`, `Tt`
- ✅ Parameter/Metadata/Data sections
- ✅ Type annotations (float, int, bool, str, datetime)

**Key insight**: This YAML will be critical for:
- Validating CSV headers during staging
- Dropping unknown columns (if `only_yaml_data=True`)
- Generating procedure-specific metadata

---

## ❌ What's Missing (Critical)

### `ManifestRow` Schema

**This is the most important missing piece!** The manifest.parquet file needs a Pydantic schema to:
1. Define what metadata is stored for each measurement run
2. Validate data before writing to manifest
3. Enforce types and constraints
4. Enable fast queries in `timeline.py`

**Where it should live**: `src/models/manifest.py`

---

## 🔧 Recommendations

### 1. Create `src/models/manifest.py`

I'll provide a complete implementation based on your procedures.yml and the implementation plan.

**Key fields needed**:

```python
class ManifestRow(BaseModel):
    """Single row in manifest.parquet - authoritative metadata for one measurement."""

    # Identity & Partitioning (required)
    run_id: str                    # SHA-1 hash
    source_file: Path              # Relative to raw_root
    proc: Literal["IVg", "IV", "IVgT", "It", "ITt", "LaserCalibration", "Tt"]
    date_local: date               # Local date (for partitioning)
    start_time_utc: datetime       # UTC timestamp

    # Chip identification (from filename + metadata)
    chip_group: Optional[str]      # "Alisson"
    chip_number: Optional[int]     # 67
    chip_name: Optional[str]       # "Alisson67"
    file_idx: Optional[int]        # 15 from Alisson67_015.csv

    # Experiment descriptors (from procedures.yml parameters)
    has_light: Optional[bool]      # Light status
    laser_voltage_v: Optional[float]
    laser_wavelength_nm: Optional[float]
    laser_period_s: Optional[float]  # "Laser ON+OFF period"

    # Voltage parameters (procedure-specific)
    vg_fixed_v: Optional[float]    # Fixed VG (ITS, IV)
    vg_start_v: Optional[float]    # IVg start
    vg_end_v: Optional[float]      # IVg end
    vg_step_v: Optional[float]     # IVg step
    vds_v: Optional[float]         # VDS
    vsd_start_v: Optional[float]   # IV start
    vsd_end_v: Optional[float]     # IV end
    vsd_step_v: Optional[float]    # IV step

    # Measurement parameters
    duration_s: Optional[float]    # Calculated from data
    sampling_time_s: Optional[float]  # From "Sampling time (excluding Keithley)"

    # Governance
    summary: Optional[str]         # Human-readable description
    schema_version: int = 1        # Schema version
    extraction_version: Optional[str]  # Parser version (git describe)
    ingested_at_utc: datetime      # Staging timestamp
```

**Why these fields?**
- Mapped from your `procedures.yml` parameters
- Support all procedure types (IVg, IT, IV, IVgT, etc.)
- Enable filtering by voltage, wavelength, light status
- Support chip history generation

### 2. Rename `StagingParameters` → `StagingConfig`

**Why?**
- Matches implementation plan terminology
- More intuitive: "config" vs "parameters"
- Consistency with `ManifestRow` (data) vs `StagingConfig` (settings)

**Change**:
```python
# src/models/config.py (rename from parameters.py)
class StagingConfig(BaseModel):
    """Configuration for staging pipeline."""
    # ... (same fields as your current StagingParameters)
```

**Optional**: Keep `parameters.py` for `IVAnalysisParameters`, `PlottingParameters`, etc. (those are fine as-is).

### 3. Add `extraction_version` to `StagingConfig`

```python
class StagingConfig(BaseModel):
    # ... existing fields ...

    extraction_version: Optional[str] = Field(
        default=None,
        description="Parser version (e.g., 'v0.4.2+g1a2b3c' from git describe)"
    )

    @model_validator(mode="after")
    def auto_detect_version(self) -> StagingConfig:
        """Auto-detect extraction version from git if not provided."""
        if self.extraction_version is None:
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "describe", "--tags", "--always", "--dirty"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.extraction_version = result.stdout.strip()
            except Exception:
                self.extraction_version = "unknown"
        return self
```

### 4. Procedure Type Enum

Create a shared enum for procedure types:

```python
# src/models/manifest.py
from typing import Literal

Proc = Literal["IVg", "IV", "IVgT", "It", "ITt", "LaserCalibration", "Tt"]
```

Use this in both `ManifestRow` and anywhere else procedure types are validated.

---

## 📊 Mapping procedures.yml → ManifestRow

Here's how your YAML maps to manifest fields:

### Common Fields (All Procedures)

| YAML Parameter | ManifestRow Field | Type | Notes |
|----------------|-------------------|------|-------|
| `Chip number` | `chip_number` | int | Also extracted from filename |
| `Chip group name` | `chip_group` | str | Also extracted from filename |
| `Laser voltage` | `laser_voltage_v` | float | Used for `has_light` detection |
| `Laser wavelength` | `laser_wavelength_nm` | float | |
| `Procedure version` | _(ignored)_ | - | Use `extraction_version` instead |
| `Start time` | `start_time_utc` | datetime | Convert to UTC |

### IVg-specific

| YAML Parameter | ManifestRow Field |
|----------------|-------------------|
| `VG start` | `vg_start_v` |
| `VG end` | `vg_end_v` |
| `VG step` | `vg_step_v` |
| `VDS` | `vds_v` |

### ITS/It-specific

| YAML Parameter | ManifestRow Field |
|----------------|-------------------|
| `VG` | `vg_fixed_v` |
| `VDS` | `vds_v` |
| `Laser ON+OFF period` | `laser_period_s` |
| `Sampling time (excluding Keithley)` | `sampling_time_s` |

### IV-specific

| YAML Parameter | ManifestRow Field |
|----------------|-------------------|
| `VG` | `vg_fixed_v` |
| `VSD start` | `vsd_start_v` |
| `VSD end` | `vsd_end_v` |
| `VSD step` | `vsd_step_v` |

---

## 🎯 Action Items

### High Priority (Phase 1)

1. **Create `src/models/manifest.py`** with `ManifestRow` schema
   - I'll provide complete implementation in next message
   - Include all fields from procedures.yml
   - Add validators for `run_id`, `chip_group`, timezone

2. **Optionally rename** `StagingParameters` → `StagingConfig`
   - Not critical, but improves consistency
   - Update imports in `__init__.py`

3. **Add `extraction_version`** to `StagingConfig`
   - Auto-detect from `git describe`
   - Fallback to "unknown" if git unavailable

### Medium Priority (Phase 2)

4. **Create procedure type enum** (`Proc`)
   - Shared between `ManifestRow` and staging code
   - Validates against procedures.yml

5. **Add YAML loader** to validate procedures.yml at runtime
   - Load YAML in staging pipeline
   - Validate CSV headers against YAML schema

### Low Priority (Phase 3+)

6. **Procedure-specific models** (optional)
   - `IVgManifestRow`, `ITSManifestRow`, etc.
   - More type-safe, but adds complexity
   - Defer until you need per-procedure validation

---

## ✅ What's Good About Your Approach

### 1. Pipeline-Oriented Models

Your models (`StagingParameters`, `IVAnalysisParameters`, etc.) are **excellent** for:
- End-to-end pipeline orchestration
- JSON config files (loading/saving)
- Cross-layer consistency validation

This is **better** than the minimal approach in the implementation plan!

### 2. YAML Schema

Having `procedures.yml` is **brilliant** for:
- Self-documenting data format
- CSV validation during staging
- Column name standardization
- Type coercion hints

### 3. Path Validation

Your `path_must_exist` validators are **smart** - they catch errors early before expensive operations run.

---

## ⚠️ Potential Issues

### 1. ManifestRow vs StagingParameters

**Confusion**: Your current `StagingParameters` is for **configuration** (how to stage), but we also need **ManifestRow** for **data** (what to store).

**Solution**: Two separate models:
- `StagingConfig` (or `StagingParameters`) - pipeline settings
- `ManifestRow` - metadata schema for manifest.parquet

### 2. Procedure Type Literal

Your procedures.yml has 7 procedure types:
- `IVg`, `IV`, `IVgT`, `It`, `ITt`, `LaserCalibration`, `Tt`

But the implementation plan only mentions:
- `IV`, `IVg`, `ITS`

**Decision needed**: Should we:
- **Option A**: Map procedures.yml names → standard names (e.g., `It` → `ITS`)
- **Option B**: Use procedures.yml names as-is (more accurate, but more types)

I recommend **Option B** (keep exact names) for traceability.

### 3. Nullable Fields

Almost all `ManifestRow` fields should be `Optional[...]` because:
- Not all procedures have all parameters
- Fallback extraction may fail (e.g., chip group from filename)
- Robustness: don't crash staging on missing metadata

**Only required fields**:
- `run_id`
- `source_file`
- `proc`
- `date_local`
- `start_time_utc`
- `ingested_at_utc`

Everything else: `Optional[...]`

---

## 🚀 Next Steps

### Immediate (I'll provide)

1. **Complete `ManifestRow` implementation** in next message
2. **Updated `StagingConfig`** with `extraction_version`
3. **Procedure type enum** (`Proc`)

### Your Decision Points

1. **Rename `StagingParameters` → `StagingConfig`?**
   - Pros: Consistency with plan, clearer naming
   - Cons: Need to update imports/docs
   - **Recommendation**: Yes, rename

2. **Keep procedures.yml names or standardize?**
   - Example: `It` vs `ITS`, `ITt` vs `ITS_temp`?
   - **Recommendation**: Keep exact YAML names for traceability

3. **Include all procedures.yml parameters in ManifestRow?**
   - Or only "essential" ones (chip, voltages, laser)?
   - **Recommendation**: Include all (disk is cheap, flexibility is valuable)

4. **Auto-detect extraction_version from git?**
   - Or require manual specification?
   - **Recommendation**: Auto-detect with fallback

---

## 📝 File Structure Recommendation

```
src/models/
├── __init__.py           # Export all models
├── config.py             # StagingConfig (renamed from parameters)
├── manifest.py           # ManifestRow (NEW - critical!)
├── parameters.py         # Analysis, Plotting, Pipeline params (keep as-is)
└── procedures.py         # (optional) YAML schema loader
```

**Why separate files?**
- `config.py`: Pipeline configuration (how to run)
- `manifest.py`: Metadata schema (what to store)
- `parameters.py`: Domain-specific params (analysis, plotting)
- Clear separation of concerns

---

## 🎯 Summary

**Your models are excellent!** You've gone beyond the basic plan with:
- ✅ Comprehensive pipeline orchestration models
- ✅ Smart path validation
- ✅ JSON config loading/saving
- ✅ Cross-layer consistency checks

**What's needed**:
- ❌ `ManifestRow` schema (critical!)
- ⚠️ `extraction_version` in `StagingConfig`
- ⚠️ Rename consideration (`StagingParameters` → `StagingConfig`)

**I'll provide in next message**:
1. Complete `ManifestRow` implementation
2. Updated `StagingConfig` with `extraction_version`
3. Procedure type enum

---

**Ready to proceed?** Let me know your answers to the decision points and I'll create the complete `manifest.py` file!
