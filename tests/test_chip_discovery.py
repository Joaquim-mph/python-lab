#!/usr/bin/env python3
"""Test script to verify chip discovery is working."""

from pathlib import Path
from src.tui.utils import discover_chips

# Test with the actual paths
metadata_dir = Path("metadata")
raw_dir = Path(".")
history_dir = Path("chip_histories")
chip_group = "Alisson"

print(f"Testing chip discovery...")
print(f"  metadata_dir: {metadata_dir} (exists: {metadata_dir.exists()})")
print(f"  raw_dir: {raw_dir} (exists: {raw_dir.exists()})")
print(f"  history_dir: {history_dir} (exists: {history_dir.exists()})")
print(f"  chip_group: {chip_group}")
print()

chips = discover_chips(metadata_dir, raw_dir, history_dir, chip_group)

print(f"Found {len(chips)} chips:")
for chip in chips:
    print(f"  - {chip.chip_group}{chip.chip_number}: {chip.total_experiments} experiments "
          f"({chip.ivg_count} IVg, {chip.its_count} ITS), Last: {chip.last_experiment_date}")
