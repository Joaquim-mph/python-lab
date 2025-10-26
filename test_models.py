#!/usr/bin/env python3
"""
Quick validation test for Phase 1 Pydantic models.

Run this to verify ManifestRow and StagingConfig work correctly.

Usage:
    python test_models.py
"""

from datetime import datetime, date, timezone
from pathlib import Path

def test_staging_config():
    """Test StagingConfig model."""
    from src.models import StagingConfig

    print("Testing StagingConfig...")

    # Create config with minimal required fields
    cfg = StagingConfig(
        raw_root=Path("raw_data"),
        stage_root=Path("data/02_stage/raw_measurements"),
        procedures_yaml=Path("config/procedures.yml")
    )

    # Check auto-filled paths
    assert cfg.manifest_path == Path("data/02_stage/_manifest/manifest.parquet")
    assert cfg.rejects_dir == Path("data/02_stage/_rejects")
    assert cfg.events_dir == Path("data/02_stage/_manifest/events")

    # Check extraction version auto-detection
    assert cfg.extraction_version is not None
    assert isinstance(cfg.extraction_version, str)

    # Check defaults
    assert cfg.workers == 6
    assert cfg.polars_threads == 1
    assert cfg.local_tz == "America/Santiago"
    assert cfg.force is False
    assert cfg.only_yaml_data is False

    print("  ✓ Auto-fill paths working")
    print(f"  ✓ Extraction version: {cfg.extraction_version}")
    print(f"  ✓ Manifest path: {cfg.manifest_path}")

    # Test helper methods
    partition_path = cfg.get_partition_path("It", "2025-10-18", "a1b2c3d4e5f67890")
    expected = Path("data/02_stage/raw_measurements/proc=It/date=2025-10-18/run_id=a1b2c3d4e5f67890")
    assert partition_path == expected
    print(f"  ✓ Partition path: {partition_path}")

    # Test timezone validation
    cfg.validate_timezone()
    print("  ✓ Timezone validation working")

    print("✅ StagingConfig: All tests passed!\n")


def test_manifest_row():
    """Test ManifestRow model."""
    from src.models import ManifestRow

    print("Testing ManifestRow...")

    # Create manifest row with all required fields
    row = ManifestRow(
        run_id="ABC123DEF456",  # Will normalize to lowercase
        source_file=Path("Alisson_15_sept/Alisson67_015.csv"),
        proc="It",
        date_local=date(2025, 10, 18),
        start_time_utc=datetime(2025, 10, 18, 17, 30, 0, tzinfo=timezone.utc),
        chip_group="alisson",  # Will normalize to title case
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

    # Check normalizations
    assert row.run_id == "abc123def456", f"Expected lowercase run_id, got {row.run_id}"
    assert row.chip_group == "Alisson", f"Expected title case chip_group, got {row.chip_group}"

    print(f"  ✓ run_id normalized: {row.run_id}")
    print(f"  ✓ chip_group normalized: {row.chip_group}")
    print(f"  ✓ Chip: {row.chip_name}")
    print(f"  ✓ Proc: {row.proc}")
    print(f"  ✓ Summary: {row.summary}")

    # Check Pydantic serialization
    row_dict = row.model_dump()
    assert "run_id" in row_dict
    assert "source_file" in row_dict
    print(f"  ✓ Serialization to dict: {len(row_dict)} fields")

    # Test model_dump_json (Pydantic v2)
    json_str = row.model_dump_json()
    assert isinstance(json_str, str)
    print(f"  ✓ JSON serialization: {len(json_str)} chars")

    print("✅ ManifestRow: All tests passed!\n")


def test_proc_enum():
    """Test Proc enum and helper functions."""
    from src.models import Proc, proc_display_name, proc_short_name

    print("Testing Proc enum...")

    # Test all procedure types
    procs = ["IVg", "IV", "IVgT", "It", "ITt", "LaserCalibration", "Tt"]

    for proc in procs:
        display = proc_display_name(proc)
        short = proc_short_name(proc)
        print(f"  ✓ {proc:20s} → {short:4s} → {display}")

    # Test specific mappings
    assert proc_short_name("It") == "ITS"
    assert proc_short_name("ITt") == "ITS"
    assert proc_display_name("It") == "Current vs Time"
    assert proc_display_name("IVg") == "Gate Voltage Sweep"

    print("✅ Proc enum: All tests passed!\n")


def test_extra_forbid():
    """Test that extra fields are rejected."""
    from src.models import ManifestRow
    from pydantic import ValidationError

    print("Testing extra='forbid' validation...")

    try:
        # This should fail with unknown field
        row = ManifestRow(
            run_id="abc123",
            source_file=Path("test.csv"),
            proc="It",
            date_local=date.today(),
            start_time_utc=datetime.now(timezone.utc),
            ingested_at_utc=datetime.now(timezone.utc),
            unknown_field="should_fail"  # ← This should raise error
        )
        print("  ✗ FAILED: Should have raised ValidationError")
        return False
    except ValidationError as e:
        print(f"  ✓ Correctly rejected unknown field")
        print(f"    Error: {e.error_count()} validation error(s)")
        return True


def test_timezone_validation():
    """Test timezone-aware datetime enforcement."""
    from src.models import ManifestRow
    from pydantic import ValidationError

    print("Testing timezone validation...")

    try:
        # This should fail with timezone-naive datetime
        row = ManifestRow(
            run_id="abc123",
            source_file=Path("test.csv"),
            proc="It",
            date_local=date.today(),
            start_time_utc=datetime.now(),  # ← Missing tzinfo!
            ingested_at_utc=datetime.now(timezone.utc)
        )
        print("  ✗ FAILED: Should have raised ValidationError")
        return False
    except ValidationError as e:
        print(f"  ✓ Correctly rejected timezone-naive datetime")
        print(f"    Error: {e.error_count()} validation error(s)")
        return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Phase 1 Model Validation Tests")
    print("=" * 70)
    print()

    try:
        test_staging_config()
        test_manifest_row()
        test_proc_enum()

        print("=" * 70)
        print("Validation Tests (Should Fail)")
        print("=" * 70)
        print()

        test_extra_forbid()
        print()
        test_timezone_validation()

        print()
        print("=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
        print()
        print("Phase 1 models are working correctly.")
        print("Ready to proceed to Phase 2: Staging Utilities")

    except Exception as e:
        print()
        print("=" * 70)
        print(f"✗ Test failed with error:")
        print("=" * 70)
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
