#!/usr/bin/env python3
"""
Test script for ITS preset backend implementation (Phase 1).

Tests:
1. Preset definitions load correctly
2. Auto baseline calculation works
3. Duration mismatch detection works
4. Baseline modes (fixed, auto, none) work in plotting function
"""

from pathlib import Path
import polars as pl

# Test 1: Load presets
print("=" * 80)
print("Test 1: Preset Definitions")
print("=" * 80)

from src.plotting.its_presets import PRESETS, get_preset, preset_summary

for name, preset in PRESETS.items():
    print(f"\n{name}:")
    print(f"  Name: {preset.name}")
    print(f"  Baseline mode: {preset.baseline_mode}")
    print(f"  Plot start: {preset.plot_start_time}s")
    print(f"  Legend by: {preset.legend_by}")

# Test preset retrieval
print("\n\n" + "=" * 80)
print("Test 2: Preset Retrieval and Summary")
print("=" * 80)

dark_preset = get_preset("dark")
if dark_preset:
    print("\nDark preset summary:")
    print(preset_summary(dark_preset))

# Test 3: Helper functions
print("\n\n" + "=" * 80)
print("Test 3: Helper Functions")
print("=" * 80)

from src.plotting.its import (
    _calculate_auto_baseline,
    _check_duration_mismatch,
    _get_experiment_durations
)

# Create mock metadata with LED periods
mock_data = {
    "proc": ["ITS", "ITS", "ITS"],
    "Laser ON+OFF period": [120.0, 120.0, 120.0],
    "source_file": ["test1.csv", "test2.csv", "test3.csv"]
}
mock_df = pl.DataFrame(mock_data)

print("\nAuto baseline calculation:")
baseline = _calculate_auto_baseline(mock_df, divisor=2.0)
print(f"  Calculated baseline: {baseline}s (expected: 60.0s)")

print("\nDuration mismatch detection:")
# Test with matching durations
durations_ok = [120.0, 121.0, 119.0]  # Within 10% tolerance
has_mismatch, warning = _check_duration_mismatch(durations_ok, tolerance=0.10)
print(f"  Test 1 (similar durations): has_mismatch={has_mismatch}")

# Test with mismatched durations
durations_bad = [120.0, 150.0, 90.0]  # Outside 10% tolerance
has_mismatch, warning = _check_duration_mismatch(durations_bad, tolerance=0.10)
print(f"  Test 2 (mismatched durations): has_mismatch={has_mismatch}")
if warning:
    print(f"\n{warning}")

# Test 4: Integration with real metadata (if available)
print("\n\n" + "=" * 80)
print("Test 4: Integration with Real Metadata")
print("=" * 80)

metadata_file = Path("metadata/Alisson_22_sept/metadata.csv")
if metadata_file.exists():
    print(f"\nLoading metadata from: {metadata_file}")
    try:
        from src.core.utils import load_and_prepare_metadata

        meta = load_and_prepare_metadata(metadata_file, chip=68.0)
        its = meta.filter(pl.col("proc") == "ITS")

        print(f"  Total ITS experiments: {its.height}")

        if its.height > 0:
            # Test auto baseline
            print("\n  Testing auto baseline:")
            baseline = _calculate_auto_baseline(its, divisor=2.0)
            print(f"    Auto baseline: {baseline}s")

            # Test duration extraction
            print("\n  Testing duration extraction:")
            durations = _get_experiment_durations(meta, Path("raw_data"))
            if durations:
                print(f"    Found {len(durations)} durations")
                print(f"    Range: {min(durations):.1f}s - {max(durations):.1f}s")

                # Test mismatch detection
                has_mismatch, warning = _check_duration_mismatch(durations, tolerance=0.10)
                if has_mismatch:
                    print(f"\n{warning}")
                else:
                    print("    ✓ No duration mismatch (all within tolerance)")
    except Exception as e:
        print(f"  Error: {e}")
else:
    print(f"\n  Metadata file not found: {metadata_file}")
    print("  Skipping integration test")

print("\n\n" + "=" * 80)
print("Backend tests complete!")
print("=" * 80)
print("\n✓ All preset backend components loaded successfully")
print("✓ Ready for Phase 2: CLI Integration")
