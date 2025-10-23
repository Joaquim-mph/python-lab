#!/usr/bin/env python3
"""
Test has_light detection function.

Quick validation of the detection algorithm with real data.
"""

from pathlib import Path
from src.core.parser import parse_iv_metadata

def test_detection():
    """Test has_light detection on sample files."""

    # Find some sample files
    test_files = [
        "raw_data/Alisson_12_sept/It2025-09-12_7.csv",
        "raw_data/Alisson_12_sept/It2025-09-12_11.csv",
        "raw_data/Alisson_15_sept/It2025-09-15_1.csv",
    ]

    print("Testing has_light detection:")
    print("=" * 80)

    for file_path_str in test_files:
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"\n❌ File not found: {file_path}")
            continue

        try:
            params = parse_iv_metadata(file_path)

            has_light = params.get("has_light")
            laser_voltage = params.get("Laser voltage", "N/A")

            # Format indicator
            if has_light is True:
                indicator = "💡 LIGHT"
            elif has_light is False:
                indicator = "🌙 DARK"
            else:
                indicator = "❗ UNKNOWN"

            print(f"\n{indicator}")
            print(f"  File: {file_path.name}")
            print(f"  Laser voltage: {laser_voltage}")
            print(f"  has_light: {has_light}")

        except Exception as e:
            print(f"\n❌ Error parsing {file_path.name}: {e}")

    print("\n" + "=" * 80)
    print("Detection test complete!")

if __name__ == "__main__":
    test_detection()
