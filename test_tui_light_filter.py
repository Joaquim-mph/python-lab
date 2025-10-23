#!/usr/bin/env python3
"""
Test script for TUI light filter integration.

Tests the interactive experiment selector with light filter buttons.
"""

from pathlib import Path
from src.interactive_selector import ExperimentSelectorApp
from src.core.timeline import build_chip_history

def test_tui_light_filter():
    """Test TUI with light filter for ITS experiments."""

    # Build chip history with has_light column
    metadata_dir = Path("metadata")
    raw_data_dir = Path("raw_data")
    chip_number = 68
    chip_group = "Alisson"

    print(f"Building chip history for {chip_group}{chip_number}...")
    history_df = build_chip_history(
        metadata_dir=metadata_dir,
        raw_data_dir=raw_data_dir,
        chip_number=chip_number,
        chip_group_name=chip_group,
        save_csv=False
    )

    print(f"Total experiments: {history_df.height}")
    print(f"Columns: {history_df.columns}")

    # Check if has_light column exists
    if "has_light" in history_df.columns:
        print("\n✅ has_light column found!")

        # Count light/dark experiments
        light_count = history_df.filter(history_df["has_light"] == True).height
        dark_count = history_df.filter(history_df["has_light"] == False).height
        unknown_count = history_df.filter(history_df["has_light"].is_null()).height

        print(f"  💡 Light: {light_count}")
        print(f"  🌙 Dark: {dark_count}")
        print(f"  ❗ Unknown: {unknown_count}")
    else:
        print("\n⚠️ has_light column NOT found - buttons won't appear")

    # Launch TUI with ITS filter
    print("\nLaunching TUI with ITS filter...")
    print("Expected features:")
    print("  - Light indicator column (💡/🌙/❗)")
    print("  - Toggle filter buttons: [All] [💡 Light Only] [🌙 Dark Only]")
    print("  - Active button shown with primary variant (blue)")
    print("\nPress Ctrl+Q to quit the TUI\n")

    app = ExperimentSelectorApp(
        chip_number=chip_number,
        chip_group=chip_group,
        history_df=history_df,
        proc_filter="ITS",  # Filter for ITS experiments
        title="Test ITS Light Filter"
    )

    # Run the app
    selected = app.run()

    if selected:
        print(f"\n✅ Selected {len(selected)} experiments: {selected}")
    else:
        print("\n❌ No experiments selected (or cancelled)")

if __name__ == "__main__":
    test_tui_light_filter()
