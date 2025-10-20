"""Transconductance plotting command: plot-transconductance."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
import polars as pl

from src.plotting import plots
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

console = Console()


def plot_transconductance_command(
    chip_number: int = typer.Argument(
        ...,
        help="Chip number (e.g., 67 for Alisson67)"
    ),
    seq: Optional[str] = typer.Option(
        None,
        "--seq",
        "-s",
        help="Comma-separated seq numbers of IVg experiments (e.g., '2,8,14'). Required unless --auto is used."
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Automatically select all IVg experiments"
    ),
    method: str = typer.Option(
        "gradient",
        "--method",
        "-m",
        help="Derivative method: 'gradient' (numpy.gradient) or 'savgol' (Savitzky-Golay filter)"
    ),
    window_length: int = typer.Option(
        9,
        "--window",
        help="Savitzky-Golay window length (odd number, only used with --method savgol)"
    ),
    polyorder: int = typer.Option(
        3,
        "--polyorder",
        help="Savitzky-Golay polynomial order (only used with --method savgol)"
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
    vds: Optional[float] = typer.Option(
        None,
        "--vds",
        help="Filter by VDS voltage (V)"
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
    Generate transconductance (gm = dI/dVg) plots from IVg experiments.

    Computes and plots the transconductance for IVg measurements. Two methods available:
    - 'gradient': Uses numpy.gradient (default, matches PyQtGraph behavior)
    - 'savgol': Uses Savitzky-Golay filter for smoother curves

    IMPORTANT: Only IVg experiments can be used for transconductance plots.
    Use 'show-history --proc IVg' to find valid IVg seq numbers.

    Examples:
        # Plot transconductance with default gradient method
        python process_and_analyze.py plot-transconductance 67 --seq 2,8,14

        # Use Savitzky-Golay filter for smoother curves
        python process_and_analyze.py plot-transconductance 67 --seq 2,8,14 --method savgol

        # Auto-select all IVg with custom window
        python process_and_analyze.py plot-transconductance 67 --auto --method savgol --window 11

        # Filter by date
        python process_and_analyze.py plot-transconductance 67 --auto --date 2025-10-15
    """
    console.print()
    console.print(Panel.fit(
        f"[bold magenta]Transconductance Plot: {chip_group}{chip_number}[/bold magenta]",
        border_style="magenta"
    ))
    console.print()

    # Validate method
    method = method.lower()
    if method not in ["gradient", "savgol"]:
        console.print(f"[red]Error:[/red] Invalid method '{method}'. Must be 'gradient' or 'savgol'")
        raise typer.Exit(1)

    # Step 1: Get seq numbers (manual or auto)
    if seq and auto:
        console.print("[red]Error:[/red] Cannot use both --seq and --auto. Choose one.")
        raise typer.Exit(1)

    if not seq and not auto:
        console.print("[red]Error:[/red] Must specify either --seq or --auto")
        console.print("[yellow]Hint:[/yellow] Use --seq 2,8,14 or --auto")
        console.print("[yellow]Note:[/yellow] Only IVg experiments can be used for transconductance")
        console.print("[dim]      Run: python process_and_analyze.py show-history {chip_number} --proc IVg[/dim]")
        raise typer.Exit(1)

    try:
        if auto:
            console.print("[cyan]Auto-selecting IVg experiments...[/cyan]")
            filters = {}
            if vds is not None:
                filters["vds"] = vds
            if date is not None:
                filters["date"] = date

            seq_numbers = auto_select_experiments(
                chip_number,
                "IVg",  # Only select IVg experiments
                history_dir,
                chip_group,
                filters
            )
            console.print(f"[green]✓[/green] Auto-selected {len(seq_numbers)} IVg experiment(s)")
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
        # Calculate output filename (method-dependent)
        output_dir_calc = setup_output_dir(output_dir, chip_number, chip_group)
        plot_tag = generate_plot_tag(seq_numbers, custom_tag=tag)

        if method == "gradient":
            output_filename = f"gm_sequence_{plot_tag}.png"
        else:  # savgol
            output_filename = f"gm_savgol_{plot_tag}.png"

        output_file = output_dir_calc / output_filename

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
        meta = plots.combine_metadata_by_seq(
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
    if vds is not None or date is not None:
        console.print("\n[cyan]Applying filters...[/cyan]")
        original_count = meta.height
        meta = apply_metadata_filters(meta, vds=vds, date=date)

        if meta.height == 0:
            console.print("[red]Error:[/red] No experiments remain after filtering")
            raise typer.Exit(1)

        console.print(f"[green]✓[/green] Filtered: {original_count} → {meta.height} experiment(s)")

    # Step 5: CRITICAL - Verify ALL experiments are IVg type
    console.print("\n[cyan]Validating experiment types...[/cyan]")
    if "proc" in meta.columns:
        non_ivg = meta.filter(pl.col("proc") != "IVg")
        if non_ivg.height > 0:
            console.print(f"[red]Error:[/red] Found {non_ivg.height} non-IVg experiment(s)")
            console.print("[red]Transconductance can only be computed from IVg experiments![/red]")
            console.print("\n[yellow]Non-IVg experiments found:[/yellow]")
            for row in non_ivg.iter_rows(named=True):
                seq_num = row.get("seq", "?")
                proc = row.get("proc", "?")
                console.print(f"  • Seq {seq_num}: {proc}")
            console.print(f"\n[yellow]Hint:[/yellow] Use [cyan]show-history {chip_number} --proc IVg[/cyan] to find valid IVg experiments")
            raise typer.Exit(1)
    else:
        console.print("[yellow]Warning:[/yellow] Could not verify experiment types (no 'proc' column)")
        console.print("[dim]Proceeding anyway, but results may fail if non-IVg data is present[/dim]")

    console.print(f"[green]✓[/green] All {meta.height} experiment(s) are IVg type")

    # Step 6: Display selected experiments
    console.print()
    display_experiment_list(meta, title="IVg Experiments for Transconductance")

    # Step 7: Display plot settings
    console.print()
    method_desc = {
        "gradient": "numpy.gradient (central differences)",
        "savgol": f"Savitzky-Golay (window={window_length}, poly={polyorder})"
    }
    display_plot_settings({
        "Plot type": "Transconductance (gm = dI/dVg)",
        "Method": method_desc[method],
        "Curves": f"{meta.height} IVg measurement(s)",
        "Output directory": str(output_dir)
    })

    # Step 8: Setup output directory and generate plot tag
    output_dir = setup_output_dir(output_dir, chip_number, chip_group)

    # Generate unique tag based on seq numbers and method
    plot_tag = generate_plot_tag(seq_numbers, custom_tag=tag)

    # Preview output filename (method-dependent)
    if method == "gradient":
        output_filename = f"gm_sequence_{plot_tag}.png"
    else:  # savgol
        output_filename = f"gm_savgol_{plot_tag}.png"

    chip_label = f"Chip{chip_number}"  # Will be updated by plot function if needed
    output_file = output_dir / output_filename

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

    # Step 9: Set FIG_DIR and call appropriate plotting function
    console.print("\n[cyan]Generating transconductance plot...[/cyan]")
    plots.FIG_DIR = output_dir

    try:
        if method == "gradient":
            plots.plot_ivg_transconductance(
                meta,
                raw_dir,
                plot_tag
            )
        else:  # savgol
            plots.plot_ivg_transconductance_savgol(
                meta,
                raw_dir,
                plot_tag,
                window_length=window_length,
                polyorder=polyorder
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
