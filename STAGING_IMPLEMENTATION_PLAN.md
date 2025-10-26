# Staging Layer Implementation Plan

> **Status**: Planning Phase
> **Target**: Staging-first architecture with Parquet + Pydantic + Manifest
> **Timeline**: Phased rollout (4 weeks estimated)
> **Backward Compatibility**: Full (TUI/CLI interfaces unchanged)

---

## 📋 Table of Contents

- [Executive Summary](#executive-summary)
- [Architecture Changes](#architecture-changes)
- [Directory Structure](#directory-structure)
- [Implementation Phases](#implementation-phases)
  - [Phase 0: Project Setup](#phase-0-project-setup)
  - [Phase 1: Pydantic Models](#phase-1-pydantic-models)
  - [Phase 2: Staging Utilities](#phase-2-staging-utilities)
  - [Phase 3: Staging Writer](#phase-3-staging-writer)
  - [Phase 4: Manifest-Based Histories](#phase-4-manifest-based-histories)
  - [Phase 5: CLI Integration](#phase-5-cli-integration)
  - [Phase 6: Validation & Testing](#phase-6-validation--testing)
  - [Phase 7: Data Migration](#phase-7-data-migration)
  - [Phase 8: Cutover & Documentation](#phase-8-cutover--documentation)
- [Technical Specifications](#technical-specifications)
- [Risk Mitigation](#risk-mitigation)
- [Success Criteria](#success-criteria)

---

## 🎯 Executive Summary

### Current State

```
raw_data/*.csv → parser.py → metadata/**/metadata.csv → timeline.py → histories → TUI/plots
                                         ↑
                                    (scattered, slow)
```

**Pain Points**:
- Chip histories require scanning multiple day-level metadata CSVs (slow)
- No schema validation (silent failures from typos/drift)
- Metadata CSVs are authoritative but hard to query
- No timezone consistency guarantees
- Cross-day analysis requires manual stitching

### Target State

```
data/01_raw/*.csv → stage.py → data/02_stage/parquet + manifest.parquet → histories → TUI/plots
                                              ↑                                 ↓
                                      (single source, fast)              (optional) metadata CSVs (export)
```

**Benefits**:
- ✅ Single source of truth: `manifest.parquet`
- ✅ Fast queries: Polars lazy scan, partitioned Parquet
- ✅ Type safety: Pydantic validation, `extra="forbid"`
- ✅ Idempotent: SHA-1 run IDs, atomic writes
- ✅ Timezone-aware: UTC storage, local partitioning
- ✅ Reproducible: VCS-backed extraction version
- ✅ Backward compatible: TUI/CLI unchanged

---

## 🏗️ Architecture Changes

### Before (Current)

```
📁 python-lab/
├── raw_data/                    # Raw CSVs
│   ├── Alisson_15_sept/
│   │   ├── Alisson67_001.csv
│   │   └── Alisson67_002.csv
│   └── Alisson_16_sept/
├── metadata/                    # Day-level metadata (authoritative)
│   ├── Alisson_15_sept/
│   │   └── metadata.csv         # ← Scan all these
│   └── Alisson_16_sept/
│       └── metadata.csv
└── src/
    ├── core/
    │   ├── parser.py            # Extract headers
    │   ├── utils.py             # Load CSVs
    │   └── timeline.py          # Build histories (scan metadata/)
    └── ...
```

**Issues**:
- `timeline.py` scans every `metadata/**/metadata.csv` (O(days))
- No validation (dict with `object` types)
- Timezone handling inconsistent
- Metadata CSVs can drift from raw data

### After (Staging-First)

```
📁 python-lab/
├── data/
│   ├── 01_raw/                  # Moved from raw_data/
│   │   ├── Alisson_15_sept/
│   │   │   ├── Alisson67_001.csv
│   │   │   └── Alisson67_002.csv
│   │   └── Alisson_16_sept/
│   ├── 02_stage/
│   │   ├── raw_measurements/    # Partitioned Parquet
│   │   │   ├── proc=IVg/
│   │   │   │   └── date=2025-10-18/
│   │   │   │       └── run_id=a1b2c3d4e5f6/
│   │   │   │           └── part-000.parquet
│   │   │   └── proc=ITS/
│   │   │       └── date=2025-10-18/
│   │   │           └── run_id=7g8h9i0j1k2/
│   │   │               └── part-000.parquet
│   │   ├── _manifest/
│   │   │   ├── manifest.parquet  # ← Single source of truth
│   │   │   └── events/           # Optional: per-run JSON logs
│   │   │       ├── a1b2c3d4e5f6.json
│   │   │       └── 7g8h9i0j1k2.json
│   │   └── _rejects/             # Failed staging attempts
│   │       ├── bad_file_001.json
│   │       └── corrupt_002.json
│   ├── 03_intermediate/          # (future) Pre-segmented data
│   └── 04_analysis/              # (future) Fit results, stats
├── histories/                    # Exported chip histories (views)
│   ├── Alisson67_history.csv
│   └── Alisson68_history.csv
├── metadata/                     # (optional) Exported day views
│   └── Alisson_15_sept/
│       └── metadata.csv          # Generated FROM manifest
└── src/
    ├── models/                   # NEW: Pydantic schemas
    │   ├── __init__.py
    │   ├── config.py             # StagingConfig
    │   └── manifest.py           # ManifestRow
    ├── stage.py                  # NEW: Staging writer
    ├── core/
    │   ├── parser.py             # (minor updates)
    │   ├── utils.py              # (minor updates)
    │   ├── staging_utils.py      # NEW: run_id, tz, wrappers
    │   └── timeline.py           # UPDATED: read manifest
    └── cli/
        └── main.py               # UPDATED: add staging commands
```

**Key Changes**:
1. **`data/01_raw/`**: Centralized raw data directory (moved from `raw_data/`)
2. **`data/02_stage/`**: Parquet storage with Hive-style partitioning
3. **`manifest.parquet`**: Single authoritative metadata table
4. **`src/models/`**: Pydantic schemas for validation
5. **`src/stage.py`**: Idempotent staging writer
6. **`histories/`**: Exported chip history CSVs (TUI reads these)

---

## 📂 Directory Structure

### Complete New Layout

```
python-lab/
├── data/
│   ├── 01_raw/                          # Raw CSVs (moved from raw_data/)
│   │   ├── Alisson_15_sept/
│   │   │   ├── Alisson67_001.csv
│   │   │   ├── Alisson67_002.csv
│   │   │   └── ...
│   │   ├── Alisson_16_sept/
│   │   └── ...
│   │
│   ├── 02_stage/
│   │   ├── raw_measurements/            # Partitioned Parquet data
│   │   │   ├── proc=IVg/
│   │   │   │   ├── date=2025-10-15/
│   │   │   │   │   └── run_id=a1b2c3d4e5f6/
│   │   │   │   │       └── part-000.parquet
│   │   │   │   └── date=2025-10-16/
│   │   │   │       └── run_id=f6e5d4c3b2a1/
│   │   │   │           └── part-000.parquet
│   │   │   ├── proc=ITS/
│   │   │   │   ├── date=2025-10-15/
│   │   │   │   │   └── run_id=7g8h9i0j1k2/
│   │   │   │   │       └── part-000.parquet
│   │   │   │   └── date=2025-10-16/
│   │   │   │       └── run_id=2k1j0i9h8g7/
│   │   │   │           └── part-000.parquet
│   │   │   └── proc=IV/
│   │   │       └── ...
│   │   │
│   │   ├── _manifest/
│   │   │   ├── manifest.parquet         # Authoritative metadata table
│   │   │   └── events/                  # Optional: per-run staging logs
│   │   │       ├── a1b2c3d4e5f6.json
│   │   │       ├── 7g8h9i0j1k2.json
│   │   │       └── ...
│   │   │
│   │   └── _rejects/                    # Failed staging attempts
│   │       ├── corrupt_file_001.json    # Error reason + metadata
│   │       ├── bad_header_002.json
│   │       └── ...
│   │
│   ├── 03_intermediate/                 # (future) Pre-segmented data
│   │   └── ivg_segments/
│   │
│   └── 04_analysis/                     # (future) Analysis outputs
│       ├── fits/
│       └── statistics/
│
├── histories/                           # Exported chip histories (views)
│   ├── Alisson67_history.csv
│   ├── Alisson68_history.csv
│   └── ...
│
├── metadata/                            # (optional) Exported day-level CSVs
│   ├── Alisson_15_sept/
│   │   └── metadata.csv                 # Generated FROM manifest (not authoritative)
│   └── ...
│
├── config/
│   └── chip_params.yaml                 # NEW: Chip-specific parameters
│
├── src/
│   ├── models/                          # NEW: Pydantic schemas
│   │   ├── __init__.py
│   │   ├── config.py                    # StagingConfig
│   │   └── manifest.py                  # ManifestRow
│   │
│   ├── stage.py                         # NEW: Staging writer
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parser.py                    # (minor updates for manifest fields)
│   │   ├── utils.py                     # (keep existing)
│   │   ├── staging_utils.py             # NEW: run_id, tz, wrappers
│   │   └── timeline.py                  # UPDATED: read from manifest
│   │
│   ├── plotting/                        # (unchanged)
│   ├── tui/                             # (unchanged)
│   └── cli/
│       ├── main.py                      # UPDATED: add staging commands
│       └── commands/
│           ├── staging.py               # NEW: stage-all, stage-incremental
│           └── ...
│
├── tests/
│   ├── test_manifest_validation.py      # NEW: Pydantic schema tests
│   ├── test_staging_writer.py           # NEW: Idempotency, atomic writes
│   ├── test_history_from_manifest.py    # NEW: Seq assignment
│   └── test_timezone_handling.py        # NEW: UTC conversion
│
├── STAGING_IMPLEMENTATION_PLAN.md       # This file
├── MIGRATION_TO_STAGING.md              # Original migration guide
└── requirements.txt                     # (add pydantic>=2.0)
```

---

## 🚀 Implementation Phases

### Phase 0: Project Setup

**Goal**: Prepare repository structure and dependencies.

**Tasks**:
1. ✅ Create directory structure (preserve existing `raw_data/` temporarily)
2. ✅ Update `requirements.txt` with new dependencies
3. ✅ Create `config/chip_params.yaml` template
4. ✅ Set up `data/` directory with symlinks for backward compatibility

**New Dependencies**:
```txt
# requirements.txt additions
pydantic>=2.0.0           # Schema validation
pyarrow>=14.0.0           # Parquet support for Polars
pyyaml>=6.0               # YAML config parsing
```

**Directory Creation**:
```bash
# Create new structure
mkdir -p data/01_raw
mkdir -p data/02_stage/raw_measurements
mkdir -p data/02_stage/_manifest/events
mkdir -p data/02_stage/_rejects
mkdir -p histories
mkdir -p config

# Symlink for backward compatibility (temporary)
ln -s data/01_raw raw_data_new  # Test with new location first
```

**Config Template** (`config/chip_params.yaml`):
```yaml
# Chip-specific parameters for staging validation
# Format: chip_number → parameters

67:
  chip_group: "Alisson"
  notes: "Primary test device"
  expected_procs: ["IVg", "ITS"]

68:
  chip_group: "Alisson"
  notes: "Secondary device"

# Global defaults
defaults:
  local_tz: "America/Santiago"
  extraction_version: "v0.4.2+g1a2b3c"  # Update from git describe
  workers: 6
  polars_threads: 1
```

**Deliverables**:
- ✅ Directory structure created
- ✅ Dependencies installed
- ✅ YAML config template created
- ✅ Symlinks tested

---

### Phase 1: Pydantic Models

**Goal**: Define type-safe schemas for manifest and configuration.

**Priority**: **HIGH** (everything depends on this)

#### 1.1 Create `src/models/manifest.py`

**Schema Requirements**:
```python
from __future__ import annotations
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

Proc = Literal["IV", "IVg", "ITS"]

class ManifestRow(BaseModel):
    """
    Single row in the authoritative manifest table.

    Each row represents one measurement run with complete metadata.
    Schema version 1 - bump for breaking changes.
    """
    model_config = ConfigDict(
        extra="forbid",           # Fail on unknown fields (prevent drift)
        validate_assignment=True  # Validate on field updates
    )

    # ═══════════════════════════════════════════════════════════
    # Identity & Partitioning
    # ═══════════════════════════════════════════════════════════
    run_id: str = Field(
        ...,
        min_length=16,
        max_length=64,
        description="SHA-1 hash (path|timestamp_utc), truncated, lowercase"
    )

    source_file: Path = Field(
        ...,
        description="Relative path from raw_root (e.g., 'Alisson_15_sept/Alisson67_001.csv')"
    )

    proc: Proc = Field(
        ...,
        description="Procedure type: IVg (gate sweep), ITS (time series), IV (drain sweep)"
    )

    date_local: date = Field(
        ...,
        description="Local calendar date (America/Santiago) for partitioning"
    )

    start_time_utc: datetime = Field(
        ...,
        description="Measurement start timestamp in UTC (timezone-aware)"
    )

    file_idx: Optional[int] = Field(
        default=None,
        ge=0,
        description="File number from filename (e.g., Alisson67_015.csv → 15)"
    )

    # ═══════════════════════════════════════════════════════════
    # Chip Identification
    # ═══════════════════════════════════════════════════════════
    chip_group: Optional[str] = Field(
        default=None,
        description="Chip group prefix (e.g., 'Alisson' from Alisson67_001.csv)"
    )

    chip_number: Optional[int] = Field(
        default=None,
        ge=0,
        description="Chip numeric ID (e.g., 67 from Alisson67_001.csv)"
    )

    chip_name: Optional[str] = Field(
        default=None,
        description="Full chip name (e.g., 'Alisson67')"
    )

    # ═══════════════════════════════════════════════════════════
    # Experiment Descriptors
    # ═══════════════════════════════════════════════════════════
    has_light: Optional[bool] = Field(
        default=None,
        description="Light illumination status: True (light), False (dark), None (unknown)"
    )

    laser_voltage_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Laser/LED voltage (V) - V < 0.1 = dark, V >= 0.1 = light"
    )

    laser_wavelength_nm: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Laser wavelength (nm) - typically 455, 530, 625, etc."
    )

    laser_period_s: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Laser ON+OFF period (s) - ITS measurements only"
    )

    vg_start_v: Optional[float] = Field(
        default=None,
        description="Gate voltage sweep start (V) - IVg measurements only"
    )

    vg_end_v: Optional[float] = Field(
        default=None,
        description="Gate voltage sweep end (V) - IVg measurements only"
    )

    vg_fixed_v: Optional[float] = Field(
        default=None,
        description="Fixed gate voltage (V) - ITS/IV measurements"
    )

    vds_v: Optional[float] = Field(
        default=None,
        description="Drain-source voltage (V) - typical values: 0.1, 1.0, 5.0"
    )

    duration_s: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Measurement duration (s) calculated from data"
    )

    # ═══════════════════════════════════════════════════════════
    # UX & Governance
    # ═══════════════════════════════════════════════════════════
    summary: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Human-readable summary (e.g., 'ITS (Vg=-3V, λ=455nm, 120s)')"
    )

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Manifest schema version - bump for breaking changes"
    )

    extraction_version: Optional[str] = Field(
        default=None,
        description="Parser version (e.g., 'v0.4.2+g1a2b3c' from git describe)"
    )

    ingested_at_utc: datetime = Field(
        ...,
        description="Staging timestamp in UTC (when this row was created)"
    )

    # ═══════════════════════════════════════════════════════════
    # Validators
    # ═══════════════════════════════════════════════════════════
    @field_validator("run_id")
    @classmethod
    def _lowercase_runid(cls, v: str) -> str:
        """Normalize run_id to lowercase for consistency."""
        return v.strip().lower()

    @field_validator("chip_group")
    @classmethod
    def _titlecase_group(cls, v: Optional[str]) -> Optional[str]:
        """Normalize chip group to title case (e.g., 'alisson' → 'Alisson')."""
        return v.strip().title() if v else None

    @field_validator("start_time_utc", "ingested_at_utc")
    @classmethod
    def _ensure_utc(cls, v: datetime) -> datetime:
        """Ensure datetime is timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError(f"Datetime must be timezone-aware: {v}")
        return v
```

#### 1.2 Create `src/models/config.py`

**Configuration Schema**:
```python
from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator

class StagingConfig(BaseModel):
    """
    Configuration for staging pipeline.

    Paths are resolved relative to project root.
    Derived paths (rejects, events, manifest) auto-fill from stage_root.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True
    )

    # ═══════════════════════════════════════════════════════════
    # Paths
    # ═══════════════════════════════════════════════════════════
    raw_root: Path = Field(
        ...,
        description="Root of raw CSV files (e.g., data/01_raw)"
    )

    stage_root: Path = Field(
        ...,
        description="Root of staged Parquet files (e.g., data/02_stage/raw_measurements)"
    )

    rejects_dir: Optional[Path] = Field(
        default=None,
        description="Failed staging attempts (default: data/02_stage/_rejects)"
    )

    events_dir: Optional[Path] = Field(
        default=None,
        description="Per-run staging event logs (default: data/02_stage/_manifest/events)"
    )

    manifest_path: Optional[Path] = Field(
        default=None,
        description="Manifest Parquet file (default: data/02_stage/_manifest/manifest.parquet)"
    )

    # ═══════════════════════════════════════════════════════════
    # Performance
    # ═══════════════════════════════════════════════════════════
    workers: int = Field(
        default=6,
        ge=1,
        le=32,
        description="Parallel staging workers (multiprocessing)"
    )

    polars_threads: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Polars internal thread pool size (per worker)"
    )

    # ═══════════════════════════════════════════════════════════
    # Localization
    # ═══════════════════════════════════════════════════════════
    local_tz: str = Field(
        default="America/Santiago",
        description="Acquisition timezone for timestamp localization"
    )

    extraction_version: Optional[str] = Field(
        default=None,
        description="Parser version (e.g., 'v0.4.2+g1a2b3c')"
    )

    # ═══════════════════════════════════════════════════════════
    # Validators
    # ═══════════════════════════════════════════════════════════
    @field_validator("raw_root", "stage_root")
    @classmethod
    def _resolve_paths(cls, v: Path) -> Path:
        """Resolve paths to absolute."""
        return v.resolve()

    @model_validator(mode="after")
    def _fill_defaults(self):
        """Auto-fill derived paths from stage_root if not provided."""
        stage_parent = self.stage_root.parent

        if self.rejects_dir is None:
            self.rejects_dir = stage_parent / "_rejects"

        if self.events_dir is None:
            self.events_dir = stage_parent / "_manifest" / "events"

        if self.manifest_path is None:
            self.manifest_path = stage_parent / "_manifest" / "manifest.parquet"

        return self
```

#### 1.3 Create `src/models/__init__.py`

```python
"""
Pydantic models for type-safe configuration and manifest schema.

Usage:
    from src.models import ManifestRow, StagingConfig

    cfg = StagingConfig(raw_root="data/01_raw", stage_root="data/02_stage/raw_measurements")
    row = ManifestRow(run_id="abc123", source_file="...", ...)
"""

from .config import StagingConfig
from .manifest import ManifestRow, Proc

__all__ = ["StagingConfig", "ManifestRow", "Proc"]
```

**Deliverables**:
- ✅ `src/models/manifest.py` created
- ✅ `src/models/config.py` created
- ✅ `src/models/__init__.py` created
- ✅ Unit tests for schema validation
- ✅ Test with sample CSV data (no staging yet)

---

### Phase 2: Staging Utilities

**Goal**: Create helper functions for run ID generation, timezone handling, and CSV normalization.

#### 2.1 Create `src/core/staging_utils.py`

**Required Functions**:

```python
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import polars as pl
from typing import Tuple

from src.core.parser import parse_iv_metadata
from src.core.utils import _read_measurement, _file_index

def compute_run_id(csv_path: Path, start_utc: datetime, raw_root: Path) -> str:
    """
    Generate deterministic, collision-resistant run ID.

    Algorithm:
        1. Compute relative path from raw_root
        2. Normalize to lowercase, forward slashes
        3. Format timestamp as ISO-8601 UTC
        4. SHA-1(path|timestamp)
        5. Truncate to first 16 characters

    Parameters
    ----------
    csv_path : Path
        Absolute path to CSV file
    start_utc : datetime
        Measurement start time (UTC, timezone-aware)
    raw_root : Path
        Raw data root directory

    Returns
    -------
    str
        Lowercase hex string (16 chars)

    Example
    -------
    >>> compute_run_id(
    ...     Path("/data/01_raw/Alisson_15_sept/Alisson67_001.csv"),
    ...     datetime(2025, 10, 18, 14, 30, 0, tzinfo=timezone.utc),
    ...     Path("/data/01_raw")
    ... )
    'a1b2c3d4e5f67890'
    """
    # Normalize relative path
    rel_path = csv_path.relative_to(raw_root)
    norm_path = str(rel_path).lower().replace("\\", "/")

    # ISO-8601 timestamp
    timestamp_iso = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Hash
    payload = f"{norm_path}|{timestamp_iso}"
    hash_obj = hashlib.sha1(payload.encode("utf-8"))
    run_id = hash_obj.hexdigest()[:16]  # First 16 chars

    return run_id


def ensure_start_time_utc(meta: dict, csv_path: Path, local_tz: str) -> datetime:
    """
    Extract measurement start time and convert to UTC.

    Priority:
        1. Header 'Start time' field (Unix timestamp)
        2. Timestamp from filename pattern (if present)
        3. File modification time (fallback)

    All times are localized to local_tz, then converted to UTC.

    Parameters
    ----------
    meta : dict
        Metadata dictionary from parse_iv_metadata()
    csv_path : Path
        Path to CSV file
    local_tz : str
        Acquisition timezone (e.g., "America/Santiago")

    Returns
    -------
    datetime
        Timezone-aware datetime in UTC

    Raises
    ------
    ValueError
        If timestamp cannot be parsed from any source
    """
    tz_local = ZoneInfo(local_tz)

    # Priority 1: Header start_time (Unix timestamp)
    if "start_time" in meta and meta["start_time"] is not None:
        try:
            ts = float(meta["start_time"])
            # Unix timestamp is UTC
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt_utc
        except (ValueError, TypeError):
            pass

    # Priority 2: Filename pattern (future: if timestamp embedded)
    # Not implemented yet, would parse patterns like:
    # Alisson67_001_20251018_143000.csv

    # Priority 3: File mtime (fallback)
    mtime = csv_path.stat().st_mtime
    dt_local = datetime.fromtimestamp(mtime, tz=tz_local)
    dt_utc = dt_local.astimezone(timezone.utc)

    return dt_utc


def derive_local_date(start_utc: datetime, local_tz: str) -> str:
    """
    Derive local calendar date for partitioning.

    Parameters
    ----------
    start_utc : datetime
        Measurement start time (UTC)
    local_tz : str
        Local timezone

    Returns
    -------
    str
        Date in ISO format (YYYY-MM-DD)
    """
    tz_local = ZoneInfo(local_tz)
    dt_local = start_utc.astimezone(tz_local)
    return dt_local.date().isoformat()


def extract_chip_info(csv_path: Path, meta: dict) -> Tuple[str | None, int | None, str | None]:
    """
    Extract chip_group, chip_number, chip_name from filename and metadata.

    Filename Pattern (Preferred):
        {chip_group}{chip_number}_{file_idx}.csv
        Examples:
            - Alisson67_015.csv → ("Alisson", 67, "Alisson67")
            - alisson67_1.csv → ("Alisson", 67, "Alisson67")
            - Alisson67.csv → ("Alisson", 67, "Alisson67")

    Fallback:
        - Check metadata for 'Chip number' field
        - Use delimiter split (first token before _ or -)

    Parameters
    ----------
    csv_path : Path
        Path to CSV file
    meta : dict
        Parsed metadata dictionary

    Returns
    -------
    tuple[str | None, int | None, str | None]
        (chip_group, chip_number, chip_name)
    """
    import re

    basename = csv_path.stem  # e.g., "Alisson67_015"

    # Pattern: {letters}{digits}_{optional_idx}
    match = re.match(r"^([A-Za-z]+)(\d+)(?:_\d+)?$", basename)
    if match:
        group = match.group(1).title()  # "Alisson"
        number = int(match.group(2))    # 67
        name = f"{group}{number}"       # "Alisson67"
        return (group, number, name)

    # Fallback 1: delimiter split
    tokens = re.split(r"[_\-]", basename)
    if len(tokens) >= 1:
        first_token = tokens[0]
        # Try to extract letters + digits
        match = re.match(r"^([A-Za-z]+)(\d+)$", first_token)
        if match:
            group = match.group(1).title()
            number = int(match.group(2))
            name = f"{group}{number}"
            return (group, number, name)

    # Fallback 2: metadata
    chip_number_meta = meta.get("Chip number")
    if chip_number_meta is not None:
        try:
            number = int(chip_number_meta)
            # No group from filename, leave as None
            return (None, number, None)
        except (ValueError, TypeError):
            pass

    # Unable to extract
    return (None, None, None)


def read_and_normalize(csv_path: Path, raw_root: Path) -> Tuple[pl.DataFrame, dict]:
    """
    Read CSV and extract metadata for staging.

    Combines existing parser + utils into single call.

    Parameters
    ----------
    csv_path : Path
        Absolute path to CSV file
    raw_root : Path
        Raw data root directory

    Returns
    -------
    tuple[pl.DataFrame, dict]
        (measurement_data, metadata_dict)

    Metadata dict includes:
        - All fields from parse_iv_metadata()
        - proc: inferred procedure type
        - chip_group, chip_number, chip_name
        - file_idx
        - duration_s: calculated from data
        - summary: human-readable description
    """
    # Parse header
    meta = parse_iv_metadata(csv_path)

    # Load measurement data
    df = _read_measurement(csv_path)

    # Add derived fields
    meta["proc"] = _infer_proc(csv_path, meta)
    meta["file_idx"] = _file_index(str(csv_path))

    chip_group, chip_number, chip_name = extract_chip_info(csv_path, meta)
    meta["chip_group"] = chip_group
    meta["chip_number"] = chip_number
    meta["chip_name"] = chip_name

    # Duration from data
    if "t" in df.columns and len(df) > 0:
        meta["duration_s"] = float(df["t"].max())
    else:
        meta["duration_s"] = None

    # Generate summary
    meta["summary"] = _generate_summary(meta)

    return (df, meta)


def _infer_proc(csv_path: Path, meta: dict) -> str:
    """
    Infer procedure type from path and metadata.

    Priority:
        1. Path contains /IVg/, /It/, /IV/
        2. Metadata 'Procedure' field
        3. Heuristics (has VL column → ITS, etc.)

    Returns
    -------
    str
        "IVg", "ITS", or "IV"
    """
    from src.core.utils import _proc_from_path

    # Try path first
    proc = _proc_from_path(str(csv_path))
    if proc in {"IVg", "ITS", "IV"}:
        return proc

    # Try metadata
    proc_meta = meta.get("Procedure", "")
    if "ivg" in proc_meta.lower():
        return "IVg"
    if "its" in proc_meta.lower() or "it" in proc_meta.lower():
        return "ITS"
    if "iv" in proc_meta.lower():
        return "IV"

    # Fallback
    return "OTHER"


def _generate_summary(meta: dict) -> str:
    """
    Generate human-readable summary string.

    Examples:
        - "ITS (Vg=-3V, λ=455nm, 120s)"
        - "IVg sweep (Vg=-5 to 5V)"
        - "Dark ITS (Vg=-2V, 300s)"
    """
    proc = meta.get("proc", "Unknown")

    if proc == "ITS":
        vg = meta.get("VG")
        wavelength = meta.get("Laser wavelength")
        period = meta.get("Laser ON+OFF period")
        has_light = meta.get("has_light")

        parts = [proc]
        if has_light is False:
            parts.insert(0, "Dark")

        details = []
        if vg is not None:
            details.append(f"Vg={vg}V")
        if wavelength is not None:
            details.append(f"λ={wavelength}nm")
        if period is not None:
            details.append(f"{period}s")

        if details:
            return f"{' '.join(parts)} ({', '.join(details)})"
        return ' '.join(parts)

    elif proc == "IVg":
        vg_start = meta.get("vg_start_v")
        vg_end = meta.get("vg_end_v")

        if vg_start is not None and vg_end is not None:
            return f"IVg sweep (Vg={vg_start} to {vg_end}V)"
        return "IVg sweep"

    elif proc == "IV":
        return "IV sweep"

    return proc
```

**Deliverables**:
- ✅ `src/core/staging_utils.py` created
- ✅ Unit tests for each function
- ✅ Test timezone edge cases (DST transitions)
- ✅ Test chip name extraction patterns

---

### Phase 3: Staging Writer

**Goal**: Implement idempotent, atomic Parquet staging with manifest append.

#### 3.1 Create `src/stage.py`

**Core Implementation**:

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List
import polars as pl

from src.models.config import StagingConfig
from src.models.manifest import ManifestRow
from src.core.staging_utils import (
    read_and_normalize,
    compute_run_id,
    ensure_start_time_utc,
    derive_local_date,
)


def stage_run(csv_path: Path, cfg: StagingConfig) -> ManifestRow:
    """
    Stage a single CSV file to Parquet with manifest row.

    Idempotent: re-running with same file produces same run_id and overwrites.
    Atomic: writes to temp file, then renames.

    Parameters
    ----------
    csv_path : Path
        Absolute path to CSV file
    cfg : StagingConfig
        Staging configuration

    Returns
    -------
    ManifestRow
        Validated manifest row (ready for append)

    Raises
    ------
    Exception
        If parsing, validation, or writing fails
    """
    # 1. Read and normalize CSV
    df, meta = read_and_normalize(csv_path, cfg.raw_root)

    # 2. Compute partition info
    start_utc = ensure_start_time_utc(meta, csv_path, cfg.local_tz)
    date_local_str = derive_local_date(start_utc, cfg.local_tz)
    run_id = compute_run_id(csv_path, start_utc, cfg.raw_root)

    # 3. Write Parquet atomically
    proc = meta.get("proc", "OTHER")
    out_dir = (
        cfg.stage_root
        / f"proc={proc}"
        / f"date={date_local_str}"
        / f"run_id={run_id}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = out_dir / "part-000.parquet"
    tmp_path = out_dir / "part-000.parquet.tmp"

    # Write to temp, then rename (atomic on POSIX)
    df.write_parquet(tmp_path, compression="snappy")
    tmp_path.rename(parquet_path)

    # 4. Build manifest row
    row = ManifestRow(
        run_id=run_id,
        source_file=csv_path.relative_to(cfg.raw_root),
        proc=proc,
        date_local=date_local_str,
        start_time_utc=start_utc,
        file_idx=meta.get("file_idx"),
        chip_group=meta.get("chip_group"),
        chip_number=meta.get("chip_number"),
        chip_name=meta.get("chip_name"),
        has_light=meta.get("has_light"),
        laser_voltage_v=meta.get("Laser voltage"),
        laser_wavelength_nm=meta.get("Laser wavelength"),
        laser_period_s=meta.get("Laser ON+OFF period"),
        vg_start_v=meta.get("vg_start_v"),
        vg_end_v=meta.get("vg_end_v"),
        vg_fixed_v=meta.get("VG"),
        vds_v=meta.get("VDS") or meta.get("VSD"),
        duration_s=meta.get("duration_s"),
        summary=meta.get("summary"),
        schema_version=1,
        extraction_version=cfg.extraction_version,
        ingested_at_utc=datetime.now(timezone.utc),
    )

    # 5. Optional: write event log
    if cfg.events_dir:
        event = {
            "run_id": run_id,
            "source_file": str(csv_path),
            "ingested_at": row.ingested_at_utc.isoformat(),
            "status": "success",
        }
        cfg.events_dir.mkdir(parents=True, exist_ok=True)
        event_path = cfg.events_dir / f"{run_id}.json"
        event_path.write_text(json.dumps(event, indent=2))

    return row


def append_manifest(rows: List[ManifestRow], manifest_path: Path) -> None:
    """
    Append manifest rows to Parquet file.

    Uses batch Pydantic validation for performance.
    Reads existing manifest, concatenates, writes atomically.

    Parameters
    ----------
    rows : list[ManifestRow]
        Validated manifest rows
    manifest_path : Path
        Path to manifest.parquet
    """
    from pydantic import TypeAdapter

    # Batch validate
    ta = TypeAdapter(list[ManifestRow])
    validated = ta.validate_python(rows)

    # Convert to DataFrame
    new_df = pl.DataFrame([r.model_dump() for r in validated])

    # Append to existing manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    if manifest_path.exists():
        existing_df = pl.read_parquet(manifest_path)
        combined_df = pl.concat([existing_df, new_df], how="vertical")
    else:
        combined_df = new_df

    # Atomic write
    tmp_path = manifest_path.with_suffix(".parquet.tmp")
    combined_df.write_parquet(tmp_path, compression="snappy")
    tmp_path.rename(manifest_path)


def stage_all(csvs: Iterable[Path], cfg: StagingConfig, batch_size: int = 100) -> None:
    """
    Stage multiple CSV files with batch manifest append.

    Errors are logged to rejects directory; processing continues.

    Parameters
    ----------
    csvs : Iterable[Path]
        CSV files to stage
    cfg : StagingConfig
        Staging configuration
    batch_size : int
        Number of rows to batch before manifest append
    """
    rows = []
    total = 0
    failed = 0

    for csv_path in csvs:
        try:
            row = stage_run(csv_path, cfg)
            rows.append(row)
            total += 1

            # Batch append
            if len(rows) >= batch_size:
                append_manifest(rows, cfg.manifest_path)
                rows = []

        except Exception as e:
            failed += 1
            _log_reject(csv_path, e, cfg)

    # Final batch
    if rows:
        append_manifest(rows, cfg.manifest_path)

    print(f"✓ Staged {total} files ({failed} rejected)")


def _log_reject(csv_path: Path, error: Exception, cfg: StagingConfig) -> None:
    """Log failed staging attempt to rejects directory."""
    if not cfg.rejects_dir:
        return

    reject = {
        "source_file": str(csv_path),
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    cfg.rejects_dir.mkdir(parents=True, exist_ok=True)
    reject_path = cfg.rejects_dir / f"{csv_path.stem}.json"
    reject_path.write_text(json.dumps(reject, indent=2))
```

**Deliverables**:
- ✅ `src/stage.py` created
- ✅ Unit tests for `stage_run()` idempotency
- ✅ Test atomic writes (simulate crash mid-write)
- ✅ Test batch append performance

---

### Phase 4: Manifest-Based Histories

**Goal**: Update `timeline.py` to read from manifest instead of day-level CSVs.

#### 4.1 Create New Functions in `src/core/timeline.py`

**Add these functions** (keep existing ones for backward compatibility):

```python
def build_chip_history_from_manifest(
    manifest_path: Path,
    chip_number: int,
    proc: str | None = None,
    chip_group: str | None = None,
) -> pl.DataFrame:
    """
    Build chip history from manifest.parquet (FAST).

    Replaces scanning multiple day-level metadata CSVs.

    Parameters
    ----------
    manifest_path : Path
        Path to manifest.parquet
    chip_number : int
        Chip number to filter
    proc : str | None
        Optional: filter by procedure ("IVg", "ITS", "IV")
    chip_group : str | None
        Optional: filter by chip group ("Alisson")

    Returns
    -------
    pl.DataFrame
        Chip history with columns:
        - seq: Sequential experiment number (per chip)
        - date_local: Date string
        - proc: Procedure type
        - has_light: Light indicator (💡/🌙/❗)
        - summary: Human-readable description
        - run_id: Run identifier
        - source_file: Original CSV path
        - file_idx: File number (#N in output)
    """
    # Lazy scan for performance
    lf = pl.scan_parquet(manifest_path)

    # Filter by chip
    q = lf.filter(pl.col("chip_number") == chip_number)

    # Optional filters
    if chip_group:
        q = q.filter(pl.col("chip_group") == chip_group)
    if proc:
        q = q.filter(pl.col("proc") == proc)

    # Assign seq numbers (per-chip sequential)
    df = (
        q.sort(["start_time_utc", "file_idx"])
         .with_columns(
             pl.int_range(1, pl.len() + 1).alias("seq")
         )
         .select([
             "seq",
             "date_local",
             "proc",
             "has_light",
             "summary",
             "chip_group",
             "chip_number",
             "chip_name",
             "run_id",
             "source_file",
             "file_idx",
             "start_time_utc",
         ])
    ).collect()

    return df


def export_chip_history_csv(
    manifest_path: Path,
    chip_number: int,
    out_csv: Path,
    proc: str | None = None,
    chip_group: str | None = None,
) -> None:
    """
    Export chip history from manifest to CSV (for TUI/plotting).

    This CSV is a VIEW, not authoritative (manifest is authoritative).

    Parameters
    ----------
    manifest_path : Path
        Path to manifest.parquet
    chip_number : int
        Chip number
    out_csv : Path
        Output CSV path (e.g., histories/Alisson67_history.csv)
    proc : str | None
        Optional: filter by procedure
    chip_group : str | None
        Optional: filter by chip group
    """
    df = build_chip_history_from_manifest(
        manifest_path, chip_number, proc, chip_group
    )

    # Format for TUI display
    df_export = df.with_columns(
        pl.col("has_light").map_elements(
            lambda x: "💡" if x is True else ("🌙" if x is False else "❗"),
            return_dtype=pl.Utf8
        ).alias("light_indicator")
    ).select([
        "seq",
        "date_local",
        "proc",
        "light_indicator",
        "summary",
        "file_idx",
    ])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_export.write_csv(out_csv)

    print(f"✓ Exported {len(df_export)} experiments to {out_csv}")


def export_all_chip_histories(
    manifest_path: Path,
    histories_dir: Path,
    min_experiments: int = 5,
    chip_group: str = "Alisson",
) -> dict[int, pl.DataFrame]:
    """
    Export histories for all chips found in manifest.

    Parameters
    ----------
    manifest_path : Path
        Path to manifest.parquet
    histories_dir : Path
        Output directory (e.g., histories/)
    min_experiments : int
        Minimum experiments to include chip
    chip_group : str
        Chip group prefix

    Returns
    -------
    dict[int, pl.DataFrame]
        Mapping of chip_number → history DataFrame
    """
    # Discover chips
    lf = pl.scan_parquet(manifest_path)
    chips_df = (
        lf.filter(pl.col("chip_group") == chip_group)
          .group_by("chip_number")
          .agg(pl.count().alias("count"))
          .filter(pl.col("count") >= min_experiments)
          .collect()
    )

    chip_numbers = chips_df["chip_number"].to_list()

    # Export each chip
    histories = {}
    for chip in chip_numbers:
        out_csv = histories_dir / f"{chip_group}{chip}_history.csv"
        export_chip_history_csv(manifest_path, chip, out_csv, chip_group=chip_group)
        histories[chip] = build_chip_history_from_manifest(
            manifest_path, chip, chip_group=chip_group
        )

    print(f"✓ Exported {len(chip_numbers)} chip histories")
    return histories
```

**Deliverables**:
- ✅ New functions added to `src/core/timeline.py`
- ✅ Keep old functions (`print_chip_history`, etc.) for backward compatibility
- ✅ Unit tests comparing manifest-based vs CSV-based histories
- ✅ Performance benchmark (manifest vs scanning CSVs)

---

### Phase 5: CLI Integration

**Goal**: Add CLI commands for staging and history generation.

#### 5.1 Create `src/cli/commands/staging.py`

```python
import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.models.config import StagingConfig
from src.stage import stage_all
from src.core.timeline import export_chip_history_csv, export_all_chip_histories

app = typer.Typer(name="staging", help="Staging and manifest commands")
console = Console()


@app.command("stage-all")
def stage_all_cmd(
    raw_root: Path = typer.Option("data/01_raw", help="Raw CSV root"),
    stage_root: Path = typer.Option("data/02_stage/raw_measurements", help="Staging root"),
    local_tz: str = typer.Option("America/Santiago", help="Acquisition timezone"),
    workers: int = typer.Option(6, help="Parallel workers"),
    polars_threads: int = typer.Option(1, help="Polars threads per worker"),
    extraction_version: str = typer.Option(None, help="Parser version (e.g., v0.4.2+g1a2b3c)"),
):
    """Stage all raw CSVs to Parquet + manifest."""
    console.print("[bold blue]Staging raw data...[/bold blue]")

    cfg = StagingConfig(
        raw_root=raw_root,
        stage_root=stage_root,
        local_tz=local_tz,
        workers=workers,
        polars_threads=polars_threads,
        extraction_version=extraction_version,
    )

    csvs = list(raw_root.rglob("*.csv"))
    console.print(f"Found {len(csvs)} CSV files")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Staging...", total=None)
        stage_all(csvs, cfg)
        progress.update(task, completed=True)

    console.print("[bold green]✓ Staging complete[/bold green]")


@app.command("build-history")
def build_history_cmd(
    manifest_path: Path = typer.Option("data/02_stage/_manifest/manifest.parquet", help="Manifest path"),
    chip: int = typer.Option(..., help="Chip number"),
    out_csv: Path = typer.Option(..., help="Output CSV path"),
    proc: str = typer.Option(None, help="Filter by procedure (IVg, ITS, IV)"),
    chip_group: str = typer.Option("Alisson", help="Chip group"),
):
    """Build chip history from manifest and export to CSV."""
    export_chip_history_csv(manifest_path, chip, out_csv, proc, chip_group)


@app.command("build-all-histories")
def build_all_histories_cmd(
    manifest_path: Path = typer.Option("data/02_stage/_manifest/manifest.parquet", help="Manifest path"),
    histories_dir: Path = typer.Option("histories", help="Output directory"),
    min_experiments: int = typer.Option(5, help="Minimum experiments per chip"),
    chip_group: str = typer.Option("Alisson", help="Chip group"),
):
    """Build and export histories for all chips."""
    export_all_chip_histories(manifest_path, histories_dir, min_experiments, chip_group)


@app.command("validate-manifest")
def validate_manifest_cmd(
    manifest_path: Path = typer.Option("data/02_stage/_manifest/manifest.parquet", help="Manifest path"),
):
    """Validate manifest schema and check for issues."""
    import polars as pl
    from pydantic import TypeAdapter
    from src.models.manifest import ManifestRow

    console.print("[bold blue]Validating manifest...[/bold blue]")

    # Load manifest
    df = pl.read_parquet(manifest_path)
    console.print(f"Total rows: {len(df)}")

    # Check for duplicates
    duplicates = df.group_by("run_id").agg(pl.count().alias("count")).filter(pl.col("count") > 1)
    if len(duplicates) > 0:
        console.print(f"[bold red]✗ Found {len(duplicates)} duplicate run_ids[/bold red]")
    else:
        console.print("[bold green]✓ No duplicate run_ids[/bold green]")

    # Schema validation
    try:
        ta = TypeAdapter(list[ManifestRow])
        rows = df.to_dicts()
        ta.validate_python(rows)
        console.print("[bold green]✓ Schema validation passed[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Schema validation failed: {e}[/bold red]")

    # Completeness checks
    required_fields = ["run_id", "source_file", "proc", "chip_number"]
    for field in required_fields:
        null_count = df[field].null_count()
        if null_count > 0:
            console.print(f"[yellow]⚠ {field}: {null_count} null values[/yellow]")
        else:
            console.print(f"[green]✓ {field}: complete[/green]")


if __name__ == "__main__":
    app()
```

#### 5.2 Update `src/cli/main.py`

Add staging commands to main CLI:

```python
import typer
from src.cli.commands import staging

app = typer.Typer()

# Register staging commands
app.add_typer(staging.app, name="staging")

# ... existing commands ...

if __name__ == "__main__":
    app()
```

**Deliverables**:
- ✅ `src/cli/commands/staging.py` created
- ✅ Commands registered in main CLI
- ✅ Rich progress bars for long operations
- ✅ Validation command with completeness checks

---

### Phase 6: Validation & Testing

**Goal**: Ensure parity between old and new systems before cutover.

#### 6.1 Unit Tests

Create `tests/test_staging/`:

```
tests/
├── test_staging/
│   ├── __init__.py
│   ├── test_manifest_validation.py      # Pydantic schema tests
│   ├── test_staging_writer.py           # Idempotency, atomic writes
│   ├── test_history_from_manifest.py    # Seq assignment, sorting
│   ├── test_timezone_handling.py        # UTC conversion
│   └── fixtures/
│       ├── sample_ivg.csv
│       ├── sample_its.csv
│       └── sample_manifest.parquet
```

**Key Test Cases**:

```python
# test_manifest_validation.py
def test_extra_field_forbidden():
    """ManifestRow rejects unknown fields."""
    with pytest.raises(ValidationError):
        ManifestRow(
            run_id="abc123",
            source_file="test.csv",
            proc="IVg",
            date_local=date.today(),
            start_time_utc=datetime.now(timezone.utc),
            ingested_at_utc=datetime.now(timezone.utc),
            unknown_field="should fail"  # ← Should raise error
        )

def test_run_id_lowercase():
    """run_id is normalized to lowercase."""
    row = ManifestRow(
        run_id="ABC123DEF",
        ...
    )
    assert row.run_id == "abc123def"

# test_staging_writer.py
def test_idempotency():
    """Re-staging same file produces same run_id."""
    csv_path = Path("fixtures/sample_ivg.csv")
    cfg = StagingConfig(raw_root=Path("."), stage_root=Path("tmp/stage"))

    row1 = stage_run(csv_path, cfg)
    row2 = stage_run(csv_path, cfg)

    assert row1.run_id == row2.run_id
    assert row1.start_time_utc == row2.start_time_utc

# test_history_from_manifest.py
def test_seq_assignment():
    """Seq numbers are stable and sequential."""
    manifest_path = Path("fixtures/manifest.parquet")
    df = build_chip_history_from_manifest(manifest_path, chip_number=67)

    assert df["seq"].to_list() == list(range(1, len(df) + 1))
    assert df["seq"].is_sorted()

# test_timezone_handling.py
def test_utc_conversion():
    """Local time is correctly converted to UTC."""
    meta = {"start_time": 1729267800.0}  # 2024-10-18 14:30:00 Santiago
    csv_path = Path("test.csv")

    dt_utc = ensure_start_time_utc(meta, csv_path, "America/Santiago")

    assert dt_utc.tzinfo == timezone.utc
    assert dt_utc.hour == 17  # 14:30 Santiago = 17:30 UTC (DST)
```

#### 6.2 Parity Checks

**Script**: `scripts/validate_parity.py`

```python
"""
Compare old (CSV-based) vs new (manifest-based) chip histories.

Usage:
    python scripts/validate_parity.py --chip 67
"""

import typer
from pathlib import Path
import polars as pl

from src.core.timeline import (
    print_chip_history,               # Old: CSV-based
    build_chip_history_from_manifest  # New: manifest-based
)

def compare_histories(chip: int):
    """Compare old vs new history for a chip."""

    # Old method: scan day CSVs
    old_df = print_chip_history(
        metadata_dir=Path("metadata"),
        raw_data_dir=Path("data/01_raw"),
        chip_number=chip,
        chip_group_name="Alisson",
        proc_filter=None,
    )

    # New method: read manifest
    new_df = build_chip_history_from_manifest(
        manifest_path=Path("data/02_stage/_manifest/manifest.parquet"),
        chip_number=chip,
        chip_group="Alisson",
    )

    # Compare counts
    print(f"Old: {len(old_df)} experiments")
    print(f"New: {len(new_df)} experiments")

    if len(old_df) != len(new_df):
        print("✗ Row count mismatch!")
        return False

    # Compare seq numbers
    if not old_df["seq"].equals(new_df["seq"]):
        print("✗ Seq numbers differ!")
        return False

    # Compare procs
    if not old_df["proc"].equals(new_df["proc"]):
        print("✗ Proc values differ!")
        return False

    print("✓ Parity check passed!")
    return True

if __name__ == "__main__":
    typer.run(compare_histories)
```

**Deliverables**:
- ✅ Unit tests passing (>90% coverage on new code)
- ✅ Parity validation script
- ✅ Performance benchmarks documented

---

### Phase 7: Data Migration

**Goal**: Backfill historical data and reorganize directory structure.

#### 7.1 Migration Steps

**Week 1: Backfill**

```bash
# 1. Move raw data to new location
mkdir -p data/01_raw
mv raw_data/* data/01_raw/

# 2. Create symlink for backward compatibility
ln -s data/01_raw raw_data

# 3. Run staging on all historical data
python process_and_analyze.py staging stage-all \
    --raw-root data/01_raw \
    --stage-root data/02_stage/raw_measurements \
    --workers 8 \
    --polars-threads 2 \
    --extraction-version "v0.4.2+g1a2b3c"

# 4. Validate manifest
python process_and_analyze.py staging validate-manifest

# 5. Build all chip histories
python process_and_analyze.py staging build-all-histories \
    --histories-dir histories \
    --chip-group Alisson
```

**Week 2: Validation**

```bash
# Compare old vs new histories for all chips
for chip in 67 68 75; do
    python scripts/validate_parity.py --chip $chip
done

# Spot-check Parquet files
python -c "
import polars as pl
df = pl.read_parquet('data/02_stage/raw_measurements/proc=IVg/date=2025-10-18/run_id=*/part-000.parquet')
print(df.head())
"

# Check manifest completeness
python process_and_analyze.py staging validate-manifest
```

**Week 3: Cutover**

```bash
# 1. Update default paths in code
# 2. Switch TUI to read histories/ instead of metadata/
# 3. Export day CSVs from manifest (optional, for humans)
python process_and_analyze.py staging export-metadata --date 2025-10-18

# 4. Remove old metadata/ directory (BACKUP FIRST!)
mv metadata metadata.old_backup
```

#### 7.2 Rollback Plan

**If issues arise**:

1. Keep `metadata.old_backup/` for 2 weeks
2. Add `--legacy` flag to CLI to use old CSV-based methods
3. Manifest is append-only, can rebuild from scratch if needed

```bash
# Rollback command
mv metadata.old_backup metadata
rm -rf data/02_stage/_manifest/manifest.parquet

# Re-run backfill with fixes
python process_and_analyze.py staging stage-all ...
```

**Deliverables**:
- ✅ All historical data staged to Parquet
- ✅ Manifest validated (no duplicates, schema correct)
- ✅ Chip histories exported to `histories/`
- ✅ Parity checks passed
- ✅ Backup of old metadata preserved

---

### Phase 8: Cutover & Documentation

**Goal**: Finalize migration and update all documentation.

#### 8.1 Code Updates

**Changes to existing code**:

1. **`src/core/timeline.py`**: Update default to use manifest
2. **`src/tui/screens/chip_selector.py`**: Read from `histories/` instead of `metadata/`
3. **`src/cli/main.py`**: Default to manifest-based commands
4. **`process_and_analyze.py`**: Update full-pipeline to use staging

#### 8.2 Documentation Updates

**Files to update**:

1. **`README.md`**: Update directory structure, add staging section
2. **`CLAUDE.md`**: Document new architecture, update workflow diagrams
3. **`TUI_GUIDE.md`**: No changes needed (TUI interface unchanged)
4. **`CLI_GUIDE.md`**: Add staging commands documentation
5. **Create `STAGING_GUIDE.md`**: User-facing staging documentation

**New Documentation** (`STAGING_GUIDE.md`):

```markdown
# Staging Guide

## Overview

The staging layer converts raw CSVs to Parquet format with a centralized manifest.

## Commands

### Stage New Data

```bash
# Stage all CSVs
python process_and_analyze.py staging stage-all

# Build chip histories
python process_and_analyze.py staging build-all-histories
```

### Validate

```bash
# Check manifest integrity
python process_and_analyze.py staging validate-manifest
```

## Directory Structure

- `data/01_raw/` - Raw CSVs (unchanged)
- `data/02_stage/raw_measurements/` - Parquet data (partitioned)
- `data/02_stage/_manifest/manifest.parquet` - Metadata (authoritative)
- `histories/` - Exported chip history CSVs (TUI reads these)

## Troubleshooting

See `STAGING_IMPLEMENTATION_PLAN.md` for detailed architecture.
```

**Deliverables**:
- ✅ All code updated to use manifest by default
- ✅ Documentation updated
- ✅ Migration guide created
- ✅ Git tag created (e.g., `v0.5.0-staging-migration`)

---

## 📐 Technical Specifications

### Run ID Generation

**Algorithm**:
```python
payload = f"{normalized_relative_path}|{timestamp_utc_iso}"
# e.g., "alisson_15_sept/alisson67_001.csv|2025-10-18T14:30:00Z"

run_id = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
# → "a1b2c3d4e5f67890"
```

**Properties**:
- ✅ Deterministic: Same file + timestamp → same run_id
- ✅ Collision-resistant: SHA-1 truncated to 16 chars (64-bit space)
- ✅ Lowercase: Normalized for case-insensitive filesystems
- ✅ Idempotent: Re-staging overwrites in place

### Timezone Handling

**Flow**:
```
Header timestamp (Unix) → UTC datetime (authoritative)
                       ↓
                  localize to America/Santiago
                       ↓
              extract local calendar date → partition key
```

**Fallback Priority**:
1. CSV header `Start time` field (Unix timestamp)
2. Filename pattern (future: if timestamp embedded)
3. File mtime (last resort)

**Storage**:
- `start_time_utc`: `datetime` (timezone-aware, UTC)
- `date_local`: `str` (ISO format, e.g., "2025-10-18")

### Partitioning Strategy

**Hive-style partitioning**:
```
proc={PROC}/date={YYYY-MM-DD}/run_id={SHA1}/part-000.parquet
```

**Benefits**:
- Polars partition pruning (fast filtering)
- Chronological organization (easy cleanup)
- Idempotent writes (same run_id → overwrite)

**Trade-offs**:
- More directories (manageable with modern filesystems)
- Slightly longer paths (no practical limit)

### Manifest Schema

**Key Fields**:
- Identity: `run_id`, `source_file`, `proc`
- Timestamps: `start_time_utc`, `date_local`, `ingested_at_utc`
- Chip: `chip_group`, `chip_number`, `chip_name`
- Experiment: `has_light`, laser fields, voltage ranges, `duration_s`
- Governance: `schema_version`, `extraction_version`, `summary`

**Schema Evolution**:
- Version 1: Initial schema
- Future versions: Bump `schema_version`, keep readers backward-compatible
- Nullable fields allow incremental schema expansion

### File Naming Pattern

**Preferred**:
```
{chip_group}{chip_number}_{file_idx}.csv
Examples:
  - Alisson67_015.csv
  - alisson67_1.csv (normalized to Alisson67)
```

**Fallbacks**:
- `Alisson67.csv` (no file_idx)
- `Alisson-67-15.csv` (delimiter variation)
- `alisson67_timestamp.csv` (lowercase + extra tokens)

**Extraction**:
```python
import re

match = re.match(r"^([A-Za-z]+)(\d+)(?:_(\d+))?", basename)
if match:
    group = match.group(1).title()    # "Alisson"
    number = int(match.group(2))      # 67
    file_idx = int(match.group(3)) if match.group(3) else None  # 15
```

---

## 🛡️ Risk Mitigation

### Risk 1: Data Loss During Migration

**Mitigation**:
- ✅ Never delete `raw_data/` (source of truth)
- ✅ Backup `metadata/` before cutover
- ✅ Test backfill on subset first (e.g., one day)
- ✅ Verify Parquet files readable before deleting CSVs
- ✅ Keep symlinks during transition period

### Risk 2: Schema Drift

**Mitigation**:
- ✅ Pydantic `extra="forbid"` (fail on unknown fields)
- ✅ Unit tests for schema validation
- ✅ `schema_version` field for breaking changes
- ✅ Manifest validation command (`validate-manifest`)

### Risk 3: Performance Regression

**Mitigation**:
- ✅ Benchmark old vs new (chip history build time)
- ✅ Polars lazy scan (only read needed columns)
- ✅ Partitioned Parquet (skip irrelevant files)
- ✅ Batch manifest appends (reduce I/O)

### Risk 4: Timezone Bugs

**Mitigation**:
- ✅ Always store UTC in manifest
- ✅ Explicit timezone validation in Pydantic
- ✅ Unit tests for DST transitions
- ✅ Fallback to file mtime (deterministic)

### Risk 5: Duplicate Run IDs

**Mitigation**:
- ✅ SHA-1 collision resistance (2^64 space)
- ✅ Validate manifest for duplicates (`validate-manifest`)
- ✅ Idempotent writes (overwrite, don't duplicate)
- ✅ Event logs track staging timestamps

---

## ✅ Success Criteria

### Phase 1-2 (Models & Utils)
- [ ] Pydantic models pass 100% validation tests
- [ ] Run ID generation is deterministic
- [ ] Timezone conversion handles DST correctly
- [ ] Chip name extraction covers 95%+ of filenames

### Phase 3 (Staging)
- [ ] Staging is idempotent (re-running doesn't duplicate)
- [ ] Parquet writes are atomic (no corrupt files)
- [ ] Rejects are logged with error details
- [ ] Batch append is 10x+ faster than individual appends

### Phase 4 (Histories)
- [ ] Manifest-based history matches CSV-based history (100% parity)
- [ ] Seq numbers are stable and sequential
- [ ] History build is 5x+ faster than CSV scanning

### Phase 5 (CLI)
- [ ] All commands have rich progress bars
- [ ] `validate-manifest` catches schema issues
- [ ] Full pipeline command works end-to-end

### Phase 6 (Testing)
- [ ] Unit test coverage >90% on new code
- [ ] Parity checks pass for all chips
- [ ] Performance benchmarks documented

### Phase 7-8 (Migration & Docs)
- [ ] All historical data staged successfully
- [ ] Manifest validated (no duplicates, complete)
- [ ] TUI works unchanged (reads new histories/)
- [ ] Documentation updated (README, CLAUDE, CLI guides)

---

## 📅 Timeline

### Week 1: Foundation
- Day 1-2: Phase 0 (setup) + Phase 1 (Pydantic models)
- Day 3-4: Phase 2 (utilities)
- Day 5: Testing & adjustments

### Week 2: Implementation
- Day 1-2: Phase 3 (staging writer)
- Day 3-4: Phase 4 (manifest-based histories)
- Day 5: Phase 5 (CLI integration)

### Week 3: Validation
- Day 1-2: Phase 6 (testing & parity checks)
- Day 3-4: Backfill historical data
- Day 5: Spot-check & performance benchmarks

### Week 4: Cutover
- Day 1-2: Phase 7 (final migration)
- Day 3-4: Phase 8 (documentation & cleanup)
- Day 5: Release & monitoring

---

## 🚦 Next Steps

### Immediate (This Week)
1. ✅ Review and approve this plan
2. ✅ Share draft Pydantic models for review
3. ✅ Clarify any open questions
4. ✅ Create project board / task tracker

### Phase 1 Start (Next)
1. Create `src/models/` directory
2. Implement `ManifestRow` schema
3. Implement `StagingConfig` schema
4. Write schema validation tests
5. Test against sample CSV data

---

## 📞 Contact & Questions

**For discussion**:
- Schema fields: Are there missing fields in `ManifestRow`?
- Chip params YAML: What parameters should be in `chip_params.yaml`?
- Timeline: Is 4 weeks realistic? Can we parallelize?
- Rollback: What's the acceptable downtime during cutover?

**Decision Points**:
- Extraction version format: Git describe output OK?
- Parallelization: Multiprocessing or threading for staging?
- Incremental staging: Add command to stage only new files?
- Manifest compaction: Periodic deduplication needed?

---

## 📚 References

- **MIGRATION_TO_STAGING.md** - Original migration guide
- **CLAUDE.md** - Current system architecture
- **src/core/README.md** - Core module documentation
- **ITS_BASELINE_GUIDE.md** - Baseline system (unchanged by staging)

---

**Last Updated**: 2025-10-26
**Status**: Planning Phase
**Next Review**: After Phase 1 completion
