"""ITS plotting command: plot-its."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel

from src.plotting import its, plot_utils
from src.cli.helpers import (
    parse_seq_list,
    generate_plot_tag,
    setup_output_dir,
    auto_select_experiments,
    validate_experiments_exist,
    apply_metadata_filters,
    display_experiment_list,
    display_plot_settings,
    display_plot_success
)
import polars as pl

console = Console()


def _all_its_are_dark(meta: pl.DataFrame) -> bool:
    """
    Check if all ITS experiments in metadata are dark (no laser).

    Returns True if ALL experiments have laser toggle = False or laser voltage = 0.
    """
    its = meta.filter(pl.col("proc") == "ITS")
    if its.height == 0:
        return False

    # Check laser toggle column if available
    if "Laser toggle" in its.columns:
        try:
            # Convert to boolean and check if ALL are False
            laser_toggle_col = its["Laser toggle"]
            # Handle various formats: bool, string "true"/"false", etc.
            toggles = []
            for val in laser_toggle_col.to_list():
                if isinstance(val, bool):
                    toggles.append(val)
                elif isinstance(val, str):
                    toggles.append(val.lower() == "true")
                else:
                    # If unclear, assume it might have light
                    toggles.append(True)

            if all(not t for t in toggles):
                return True
        except Exception:
            pass

    # Check laser voltage column if available
    if "Laser voltage" in its.columns or "VL_meta" in its.columns:
        try:
            col_name = "Laser voltage" if "Laser voltage" in its.columns else "VL_meta"
            voltages = its[col_name].cast(pl.Float64).to_list()
            # If ALL voltages are 0 or NaN/None, it's dark
            if all(v is None or v == 0 or v != v for v in voltages):  # v != v checks for NaN
                return True
        except Exception:
            pass

    return False


def plot_its_command(
    chip_number: int = typer.Argument(
        ...,
        help="Chip number (e.g., 67 for Alisson67)"
    ),
    seq: Optional[str] = typer.Option(
        None,
        "--seq",
        "-s",
        help="Comma-separated seq numbers (e.g., '52,57,58'). Required unless --auto is used."
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Automatically select all ITS experiments"
    ),
    legend_by: str = typer.Option(
        "led_voltage",
        "--legend",
        "-l",
        help="Legend grouping: 'led_voltage', 'wavelength', or 'vg'"
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Custom tag for output filename (default: auto-generated from seq numbers)"
    ),
    output_dir: Path = typer.Option(
        Path("figs"),
        "--output",
        "-o",
        help="Output directory for plots"
    ),
    chip_group: str = typer.Option(
        "Alisson",
        "--group",
        "-g",
        help="Chip group name"
    ),
    padding: float = typer.Option(
        0.05,
        "--padding",
        help="Y-axis padding (fraction of data range, e.g., 0.05 = 5%)"
    ),
    baseline_t: float = typer.Option(
        60.0,
        "--baseline",
        help="Baseline time in seconds for current correction"
    ),
    vg: Optional[float] = typer.Option(
        None,
        "--vg",
        help="Filter by gate voltage (V)"
    ),
    wavelength: Optional[float] = typer.Option(
        None,
        "--wavelength",
        help="Filter by wavelength (nm)"
    ),
    date: Optional[str] = typer.Option(
        None,
        "--date",
        help="Filter by date (YYYY-MM-DD)"
    ),
    metadata_dir: Path = typer.Option(
        Path("metadata"),
        "--metadata",
        help="Metadata directory"
    ),
    raw_dir: Path = typer.Option(
        Path("."),
        "--raw-dir",
        help="Raw data directory"
    ),
    history_dir: Path = typer.Option(
        Path("chip_histories"),
        "--history-dir",
        help="Chip history directory"
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        help="Preview mode: show what will be plotted without generating files"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Dry run mode: validate experiments and show output filename only (fastest)"
    ),
):
    """
    Generate ITS overlay plots from terminal.

    Plot ITS (current vs time) experiments with baseline correction and
    customizable legend grouping. Prevents overwriting by using unique
    filenames based on the experiments selected.

    Examples:
        # Plot specific experiments
        python process_and_analyze.py plot-its 67 --seq 52,57,58

        # Auto-select all ITS with custom legend
        python process_and_analyze.py plot-its 67 --auto --legend wavelength

        # Filter by gate voltage
        python process_and_analyze.py plot-its 67 --auto --vg -0.4

        # Custom output location
        python process_and_analyze.py plot-its 67 --seq 52,57,58 --output results/
    """
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]ITS Overlay Plot: {chip_group}{chip_number}[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    # Step 1: Get seq numbers (manual or auto)
    if seq and auto:
        console.print("[red]Error:[/red] Cannot use both --seq and --auto. Choose one.")
        raise typer.Exit(1)

    if not seq and not auto:
        console.print("[red]Error:[/red] Must specify either --seq or --auto")
        console.print("[yellow]Hint:[/yellow] Use --seq 52,57,58 or --auto")
        raise typer.Exit(1)

    try:
        if auto:
            console.print("[cyan]Auto-selecting ITS experiments...[/cyan]")
            filters = {}
            if vg is not None:
                filters["vg"] = vg
            if wavelength is not None:
                filters["wavelength"] = wavelength
            if date is not None:
                filters["date"] = date

            seq_numbers = auto_select_experiments(
                chip_number,
                "ITS",
                history_dir,
                chip_group,
                filters
            )
            console.print(f"[green]✓[/green] Auto-selected {len(seq_numbers)} ITS experiment(s)")
        else:
            seq_numbers = parse_seq_list(seq)
            console.print(f"[cyan]Using specified seq numbers:[/cyan] {seq_numbers}")

    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Step 2: Validate seq numbers exist
    console.print("\n[cyan]Validating experiments...[/cyan]")
    valid, errors = validate_experiments_exist(
        seq_numbers,
        chip_number,
        history_dir,
        chip_group
    )

    if not valid:
        console.print("[red]Validation failed:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] All seq numbers valid")

    # Dry-run mode: exit after validation, before loading metadata
    if dry_run:
        # Calculate output filename
        output_dir_calc = setup_output_dir(output_dir, chip_number, chip_group)
        plot_tag = generate_plot_tag(seq_numbers, custom_tag=tag)
        chip_label = f"chip{chip_number}"
        output_file = output_dir_calc / f"{chip_label}_ITS_overlay_{plot_tag}.png"

        # Check if file already exists
        file_exists = output_file.exists()
        file_status = "[yellow](file exists - will overwrite)[/yellow]" if file_exists else "[green](new file)[/green]"

        console.print()
        console.print(Panel(
            f"[cyan]Output file:[/cyan]\n{output_file}\n{file_status}",
            title="[bold]Output File[/bold]",
            border_style="cyan"
        ))
        console.print()
        console.print("[bold green]✓ Dry run complete - no files generated[/bold green]")
        console.print("[dim]  Run without --dry-run to generate plot[/dim]")
        console.print("[dim]  Use --preview to see full experiment details[/dim]")
        raise typer.Exit(0)

    # Step 3: Load metadata using combine_metadata_by_seq
    console.print("\n[cyan]Loading experiment metadata...[/cyan]")
    try:
        meta = plot_utils.combine_metadata_by_seq(
            metadata_dir,
            raw_dir,
            float(chip_number),
            seq_numbers,
            chip_group
        )
    except Exception as e:
        console.print(f"[red]Error loading metadata:[/red] {e}")
        raise typer.Exit(1)

    if meta.height == 0:
        console.print("[red]Error:[/red] No metadata loaded")
        raise typer.Exit(1)

    # Step 4: Apply additional filters (if any)
    if vg is not None or wavelength is not None or date is not None:
        console.print("\n[cyan]Applying filters...[/cyan]")
        original_count = meta.height
        meta = apply_metadata_filters(meta, vg=vg, wavelength=wavelength, date=date)

        if meta.height == 0:
            console.print("[red]Error:[/red] No experiments remain after filtering")
            raise typer.Exit(1)

        console.print(f"[green]✓[/green] Filtered: {original_count} → {meta.height} experiment(s)")

    # Step 5: Display selected experiments
    console.print()
    display_experiment_list(meta, title="ITS Experiments to Plot")

    # Step 6: Display plot settings
    console.print()
    display_plot_settings({
        "Legend by": legend_by,
        "Baseline time": f"{baseline_t} s",
        "Padding": f"{padding:.2%}",
        "Output directory": str(output_dir)
    })

    # Step 7: Setup output directory and generate plot tag
    output_dir = setup_output_dir(output_dir, chip_number, chip_group)

    # Generate unique tag based on seq numbers
    plot_tag = generate_plot_tag(seq_numbers, custom_tag=tag)

    # Preview output filename
    chip_label = f"chip{chip_number}"
    output_file = output_dir / f"{chip_label}_ITS_overlay_{plot_tag}.png"

    console.print()
    console.print(Panel(
        f"[cyan]Output file:[/cyan]\n{output_file}",
        title="[bold]Output File[/bold]",
        border_style="cyan"
    ))

    # Exit in preview mode
    if preview:
        console.print()
        console.print("[bold green]✓ Preview complete - no files generated[/bold green]")
        console.print("[dim]  Run without --preview to generate plot[/dim]")
        raise typer.Exit(0)

    # Step 8: Detect if all ITS are dark and choose appropriate plotting function
    all_dark = _all_its_are_dark(meta)

    if all_dark:
        console.print("\n[dim]Detected: All ITS experiments are dark (no laser)[/dim]")
        console.print("[dim]Using simplified dark plot (no light window shading)[/dim]")
        # Update output filename for dark plots
        output_file = output_dir / f"{chip_label}_ITS_dark_{plot_tag}.png"
        # Adjust legend default for dark plots (vg is more useful than led_voltage)
        if legend_by == "led_voltage":
            console.print("[dim]Tip: For dark measurements, --legend vg might be more useful[/dim]")

    # Step 9: Set FIG_DIR and call plotting function
    console.print("\n[cyan]Generating plot...[/cyan]")
    its.FIG_DIR = output_dir

    try:
        if all_dark:
            its.plot_its_dark(
                meta,
                raw_dir,
                plot_tag,
                baseline_t=baseline_t,
                legend_by=legend_by,
                padding=padding
            )
        else:
            its.plot_its_overlay(
                meta,
                raw_dir,
                plot_tag,
                baseline_t=baseline_t,
                legend_by=legend_by,
                padding=padding
            )
    except Exception as e:
        console.print(f"[red]Error generating plot:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)

    # Step 10: Display success with output file path
    console.print()
    display_plot_success(output_file)
    console.print()
