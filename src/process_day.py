#!/usr/bin/env python3
"""
process_day.py

Automated processing script for a full day's experimental data.
Generates all requested plots based on the timeline and available measurements.
"""

from pathlib import Path
import numpy as np
import polars as pl
from plots import (
    load_and_prepare_metadata, plot_ivg_sequence, plot_its_by_vg,
    plot_its_by_vg_delta, plot_its_wavelength_overlay_delta_for_chip,
    ivg_sequence_gif
)
from timeline import print_day_timeline
from styles import set_plot_style
import scienceplots
set_plot_style('prism_rain')

def process_day_experiments(
    metadata_csv: str,
    base_dir: Path = Path("."),
    chips_to_process: list = None,
    generate_gifs: bool = True,
    generate_wavelength_overlays: bool = True
):
    """
    Process a full day's experiments and generate all requested plots.
    
    Parameters:
    -----------
    metadata_csv : str
        Path to the metadata CSV file
    base_dir : Path
        Base directory where the raw CSV files are located
    chips_to_process : list, optional
        List of chip numbers to process. If None, processes all chips found.
    generate_gifs : bool
        Whether to generate animated GIFs of IVg sequences
    generate_wavelength_overlays : bool
        Whether to generate wavelength overlay plots
    """
    
    print(f"Processing day experiments from: {metadata_csv}")
    print(f"Base directory: {base_dir}")
    
    # Print the day timeline first
    print("\n" + "="*50)
    print("GENERATING DAY TIMELINE")
    print("="*50)
    timeline = print_day_timeline(metadata_csv, base_dir)
    
    # Load full metadata to determine available chips
    full_meta = pl.read_csv(metadata_csv, infer_schema_length=1000)
    available_chips = sorted([float(x) for x in full_meta.get_column("Chip number").unique().to_list() 
                             if x is not None])
    
    if chips_to_process is None:
        chips_to_process = available_chips
    
    print(f"\nAvailable chips: {available_chips}")
    print(f"Processing chips: {chips_to_process}")
    
    tag = Path(metadata_csv).stem
    
    # Process each chip
    for chip_num in chips_to_process:
        if chip_num not in available_chips:
            print(f"\nWarning: Chip {chip_num} not found in data, skipping...")
            continue
            
        print(f"\n" + "="*50)
        print(f"PROCESSING CHIP {chip_num}")
        print("="*50)
        
        # Load and prepare metadata for this chip
        meta = load_and_prepare_metadata(metadata_csv, chip_num)
        
        if meta.height == 0:
            print(f"No data found for chip {chip_num}, skipping...")
            continue
            
        # Check what types of measurements we have
        procs = set(meta.get_column("proc").to_list())
        print(f"Available procedures for chip {chip_num}: {procs}")
        
        # 1. Process IVg measurements
        if "IVg" in procs:
            print(f"\nGenerating IVg plots for chip {chip_num}...")
            
            # Plot all IVg in sequence
            plot_ivg_sequence(meta, base_dir, tag)
            
            # Generate IVg sequence groups (consecutive IVgs as requested)
            ivg_data = meta.filter(pl.col("proc") == "IVg").sort("file_idx")
            if ivg_data.height > 1:
                file_indices = ivg_data.get_column("file_idx").to_list()
                
                # Generate plots for consecutive IVg groups
                consecutive_groups = find_consecutive_groups(file_indices)
                
                for group in consecutive_groups:
                    if len(group) >= 2:  # Only plot if we have at least 2 consecutive IVgs
                        print(f"Plotting IVg group: {group}")
                        meta_subset = meta.filter(
                            (pl.col("proc") == "IVg") & pl.col("file_idx").is_in(group)
                        )
                        plot_ivg_sequence(meta_subset, base_dir, f"{tag}_group_{group[0]}_{group[-1]}")
            
            # Generate GIF if requested
            if generate_gifs:
                print(f"Generating IVg sequence GIF for chip {chip_num}...")
                ivg_sequence_gif(meta, base_dir, tag, fps=2, cumulative=True)
        
        # 2. Process ITS measurements  
        if "ITS" in procs:
            print(f"\nGenerating ITS plots for chip {chip_num}...")
            
            # Get unique VG values and wavelengths from the data
            its_data = meta.filter(pl.col("proc") == "ITS")
            
            if "VG_meta" in its_data.columns:
                unique_vgs = sorted([float(x) for x in its_data.get_column("VG_meta").drop_nulls().unique().to_list()])
            else:
                unique_vgs = []
                
            unique_wavelengths = []
            if "Laser wavelength" in its_data.columns:
                unique_wavelengths = sorted([float(x) for x in its_data.get_column("Laser wavelength").drop_nulls().unique().to_list()])
            
            print(f"Found VG values: {unique_vgs}")
            print(f"Found wavelengths: {unique_wavelengths}")
            
            # Generate ITS plots by VG and wavelength (regular current)
            for vg in unique_vgs:
                for wl in unique_wavelengths:
                    print(f"Plotting ITS for Vg={vg}V, Î»={wl}nm...")
                    plot_its_by_vg(meta, base_dir, tag, vgs=[vg], wavelengths=[wl])
            
            # Generate ITS delta plots (baseline subtracted)
            for vg in unique_vgs:
                for wl in unique_wavelengths:
                    print(f"Plotting ITS delta for Vg={vg}V, Î»={wl}nm...")
                    plot_its_by_vg_delta(
                        meta, base_dir, tag,
                        vgs=[vg], wavelengths=[wl],
                        baseline_t=60.0, clip_t_min=20.0
                    )
            
            # Generate wavelength overlay plots if requested
            if generate_wavelength_overlays and unique_vgs:
                print(f"Generating wavelength overlay plots for chip {chip_num}...")
                
                for vg in unique_vgs:
                    # All wavelengths overlay
                    plot_its_wavelength_overlay_delta_for_chip(
                        meta, base_dir, tag,
                        chip=chip_num,
                        vg_center=vg, vg_window=1.5,
                        wavelengths=None,  # All wavelengths
                        baseline_t=60.0, clip_t_min=40.0
                    )
                    
                    # Split wavelengths into groups for better visualization
                    if len(unique_wavelengths) > 4:
                        # Group 1: UV-Blue range
                        uv_blue = [wl for wl in unique_wavelengths if wl <= 455.0]
                        if uv_blue:
                            plot_its_wavelength_overlay_delta_for_chip(
                                meta, base_dir, f"{tag}_UV_blue",
                                chip=chip_num,
                                vg_center=vg, vg_window=1.5,
                                wavelengths=uv_blue,
                                baseline_t=60.0, clip_t_min=40.0
                            )
                        
                        # Group 2: Green-Red range  
                        green_red = [wl for wl in unique_wavelengths if wl > 455.0]
                        if green_red:
                            plot_its_wavelength_overlay_delta_for_chip(
                                meta, base_dir, f"{tag}_green_red",
                                chip=chip_num,
                                vg_center=vg, vg_window=1.5,
                                wavelengths=green_red,
                                baseline_t=60.0, clip_t_min=40.0
                            )
    
    print(f"\n" + "="*50)
    print("PROCESSING COMPLETE")
    print("="*50)
    print(f"All plots saved to: {Path('figs').absolute()}")


def find_consecutive_groups(numbers: list) -> list:
    """
    Find groups of consecutive numbers in a list.
    
    Returns:
    --------
    list of lists: Each sublist contains consecutive numbers
    """
    if not numbers:
        return []
    
    numbers = sorted(set(numbers))  # Remove duplicates and sort
    groups = []
    current_group = [numbers[0]]
    
    for i in range(1, len(numbers)):
        if numbers[i] == numbers[i-1] + 1:  # Consecutive
            current_group.append(numbers[i])
        else:  # Gap found, start new group
            if len(current_group) > 1:  # Only keep groups with multiple elements
                groups.append(current_group)
            current_group = [numbers[i]]
    
    # Don't forget the last group
    if len(current_group) > 1:
        groups.append(current_group)
    
    return groups


def process_specific_chip_day(metadata_csv: str, chip_number: float, base_dir: Path = Path(".")):
    """
    Process a specific chip following the exact pattern from your examples.
    This replicates the manual workflow you showed.
    """
    
    tag = Path(metadata_csv).stem
    meta = load_and_prepare_metadata(metadata_csv, chip_number)
    
    if meta.height == 0:
        print(f"No data found for chip {chip_number}")
        return
    
    print(f"Processing chip {chip_number} with {meta.height} measurements")
    
    # Print timeline for this chip
    timeline = print_day_timeline(metadata_csv, base_dir)
    chip_timeline = timeline.filter(pl.col("chip") == chip_number)
    print(f"Timeline for chip {chip_number}:")
    for row in chip_timeline.iter_rows(named=True):
        print(f"  {row['seq']:>3d}  {row['time_hms']:>8}  {row['summary']}")
    
    # Main sequence plot
    plot_ivg_sequence(meta, base_dir, tag)
    
    # Get the IVg file indices for manual grouping
    ivg_data = meta.filter(pl.col("proc") == "IVg").sort("file_idx")
    ivg_indices = ivg_data.get_column("file_idx").to_list()
    print(f"Available IVg indices: {ivg_indices}")
    
    # Generate consecutive IVg plots (as in your examples)
    consecutive_groups = find_consecutive_groups(ivg_indices)
    for group in consecutive_groups:
        print(f"Plotting consecutive IVg group: {group}")
        meta_subset = meta.filter(
            (pl.col("proc") == "IVg") & pl.col("file_idx").is_in(group)
        )
        plot_ivg_sequence(meta_subset, base_dir, f"{tag}_consecutive_{group[0]}_{group[-1]}")
    
    # Process ITS measurements by VG and wavelength
    its_data = meta.filter(pl.col("proc") == "ITS")
    if its_data.height > 0:
        vgs = sorted(set(its_data.get_column("VG_meta").drop_nulls().to_list()))
        wavelengths = []
        if "Laser wavelength" in its_data.columns:
            wavelengths = sorted(set(its_data.get_column("Laser wavelength").drop_nulls().to_list()))
        
        # Regular ITS plots
        for vg in vgs:
            for wl in wavelengths:
                plot_its_by_vg(meta, base_dir, tag, vgs=[vg], wavelengths=[wl])
        
        # Delta ITS plots  
        for vg in vgs:
            for wl in wavelengths:
                plot_its_by_vg_delta(
                    meta, base_dir, tag,
                    vgs=[vg], wavelengths=[wl],
                    baseline_t=60.0, clip_t_min=20.0
                )
    
    print(f"Completed processing chip {chip_number}")


if __name__ == "__main__":
    # Example usage - modify these parameters for your specific day
    
    # For the Sept 12 example from your timeline:
    METADATA_CSV = "Alisson_12_sept_metadata.csv"
    BASE_DIR = Path("raw_data")
    CHIPS_TO_PROCESS = [75.0]  # Based on your timeline showing chip 75
    
    # Process the full day
    process_day_experiments(
        METADATA_CSV,
        BASE_DIR,
        chips_to_process=CHIPS_TO_PROCESS,
        generate_gifs=True,
        generate_wavelength_overlays=True
    )
    
    # Or process a specific chip with the exact workflow pattern:
    process_specific_chip_day(METADATA_CSV, 75.0, BASE_DIR)
    
    # For other days, just change the parameters:
    METADATA_CSV = "Alisson_15_sept_metadata.csv"  
    CHIPS_TO_PROCESS = [68.0]
    process_day_experiments(METADATA_CSV, BASE_DIR, CHIPS_TO_PROCESS)