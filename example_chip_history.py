#!/usr/bin/env python3
"""
Example script showing how to use the chip history timeline functions.

This demonstrates:
1. Generating a timeline for a specific chip
2. Automatically generating timelines for all chips
"""

from pathlib import Path
from src.timeline import print_chip_history, generate_all_chip_histories

# =============================================================================
# Configuration
# =============================================================================
METADATA_DIR = Path("metadata")
RAW_DATA_DIR = Path("raw_data")
CHIP_GROUP_NAME = "Alisson"  # Your chip group name

# =============================================================================
# Example 1: Generate history for a specific chip
# =============================================================================
def example_single_chip():
    """Show complete experiment history for one chip."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Chip History")
    print("="*80)

    # Generate history for Alisson72
    chip_num = 72

    history = print_chip_history(
        metadata_dir=METADATA_DIR,
        raw_data_dir=RAW_DATA_DIR,
        chip_number=chip_num,
        chip_group_name=CHIP_GROUP_NAME,
        save_csv=True,  # Saves to Alisson72_history.csv
    )

    # You can also filter by procedure type
    # print_chip_history(
    #     METADATA_DIR,
    #     RAW_DATA_DIR,
    #     chip_num,
    #     CHIP_GROUP_NAME,
    #     proc_filter="IVg"  # Only show IVg measurements
    # )

    return history


# =============================================================================
# Example 2: Generate histories for ALL chips automatically
# =============================================================================
def example_all_chips():
    """Automatically find all chips and generate their histories."""
    print("\n" + "="*80)
    print("EXAMPLE 2: All Chips - Automatic History Generation")
    print("="*80)

    histories = generate_all_chip_histories(
        metadata_dir=METADATA_DIR,
        raw_data_dir=RAW_DATA_DIR,
        chip_group_name=CHIP_GROUP_NAME,
        save_csv=True,  # Saves Alisson72_history.csv, Alisson68_history.csv, etc.
        min_experiments=5,  # Only include chips with 5+ experiments
    )

    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    for chip_num, history in sorted(histories.items()):
        print(f"{CHIP_GROUP_NAME}{chip_num}: {history.height} experiments")

    return histories


# =============================================================================
# Example 3: Programmatic access to history data
# =============================================================================
def example_data_analysis():
    """Show how to access and analyze the history data programmatically."""
    from src.timeline import build_chip_history

    print("\n" + "="*80)
    print("EXAMPLE 3: Programmatic Data Access")
    print("="*80)

    chip_num = 72
    history = build_chip_history(
        METADATA_DIR,
        RAW_DATA_DIR,
        chip_num,
        CHIP_GROUP_NAME
    )

    if history.height > 0:
        # Count experiments by procedure type
        proc_counts = history.group_by("proc").agg([
            ("proc", "count")
        ]).sort("proc")

        print(f"\n{CHIP_GROUP_NAME}{chip_num} Experiment Breakdown:")
        print("-" * 40)
        for row in proc_counts.iter_rows(named=True):
            print(f"  {row['proc']:15s}: {row['count']:3d} experiments")

        # Count experiments by date
        date_counts = history.group_by("date").agg([
            ("date", "count")
        ]).sort("date")

        print(f"\nExperiments by Date:")
        print("-" * 40)
        for row in date_counts.iter_rows(named=True):
            print(f"  {row['date']}: {row['count']:3d} experiments")

    return history


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    # Uncomment the example you want to run:

    # Example 1: Single chip history
    example_single_chip()

    # Example 2: All chips automatically
    # example_all_chips()

    # Example 3: Programmatic analysis
    # example_data_analysis()
