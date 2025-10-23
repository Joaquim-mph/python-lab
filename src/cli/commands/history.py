"""History display commands: show-history."""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
import polars as pl

console = Console()


def show_history_command(
    chip_number: int = typer.Argument(
        ...,
        help="Chip number to display (e.g., 67 for Alisson67)"
    ),
    chip_group: str = typer.Option(
        "Alisson",
        "--group",
        "-g",
        help="Chip group name prefix"
    ),
    history_dir: Path = typer.Option(
        Path("chip_histories"),
        "--history-dir",
        "-d",
        help="Directory containing chip history CSV files"
    ),
    proc_filter: Optional[str] = typer.Option(
        None,
        "--proc",
        "-p",
        help="Filter by procedure type (IVg, ITS, IV, etc.)"
    ),
    light_filter: Optional[str] = typer.Option(
        None,
        "--light",
        "-l",
        help="Filter by light status: 'light', 'dark', or 'unknown'"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Show only last N experiments"
    ),
):
    """
    Display the complete experiment history for a specific chip.

    Shows a beautiful, paginated view of all experiments with details
    including date, time, procedure type, and parameters.

    Example:
        python process_and_analyze.py show-history 67
        python process_and_analyze.py show-history 72 --proc ITS --limit 20
    """
    chip_name = f"{chip_group}{chip_number}"
    history_file = history_dir / f"{chip_name}_history.csv"

    # Check if file exists
    if not history_file.exists():
        console.print(f"[red]Error:[/red] History file not found: {history_file}")
        console.print(f"\n[yellow]Hint:[/yellow] Run [cyan]chip-histories[/cyan] command first to generate history files.")
        console.print(f"Available files in {history_dir}:")
        if history_dir.exists():
            for f in sorted(history_dir.glob("*_history.csv")):
                console.print(f"  • {f.name}")
        else:
            console.print(f"  [dim](directory does not exist)[/dim]")
        raise typer.Exit(1)

    # Load history
    try:
        history = pl.read_csv(history_file)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read history file: {e}")
        raise typer.Exit(1)

    # Apply filters
    if proc_filter:
        history = history.filter(pl.col("proc") == proc_filter)
        if history.height == 0:
            console.print(f"[yellow]No experiments found with procedure '{proc_filter}'[/yellow]")
            raise typer.Exit(0)

    # Apply light filter
    if light_filter:
        lf = light_filter.lower()
        if lf in ("light", "l", "💡"):
            history = history.filter(pl.col("has_light") == True)
            filter_desc = "light experiments"
        elif lf in ("dark", "d", "🌙"):
            history = history.filter(pl.col("has_light") == False)
            filter_desc = "dark experiments"
        elif lf in ("unknown", "u", "?", "❗"):
            history = history.filter(pl.col("has_light").is_null())
            filter_desc = "unknown light status"
        else:
            console.print(f"[red]Error:[/red] Invalid light filter '{light_filter}'. Use: light, dark, or unknown")
            raise typer.Exit(1)

        if history.height == 0:
            console.print(f"[yellow]No {filter_desc} found[/yellow]")
            raise typer.Exit(0)

    if limit:
        history = history.tail(limit)

    # Display header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]{chip_name} Experiment History[/bold cyan]\n"
        f"Total experiments: [yellow]{history.height}[/yellow]",
        border_style="cyan"
    ))
    console.print()

    # Summary statistics
    dates = [d for d in history["date"].to_list() if d != "unknown"]
    if dates:
        date_range = f"{min(dates)} to {max(dates)}"
        num_days = len(set(dates))
    else:
        date_range = "unknown"
        num_days = 0

    # Count by procedure
    proc_counts = history.group_by("proc").agg([
        pl.len().alias("count")
    ]).sort("proc")

    # Summary cards
    summary_items = []

    # Date range card
    date_card = Table.grid(padding=(0, 2))
    date_card.add_column(style="cyan", justify="right")
    date_card.add_column(style="yellow")
    date_card.add_row("Date Range:", date_range)
    date_card.add_row("Days:", str(num_days))
    summary_items.append(Panel(date_card, title="[cyan]Timeline[/cyan]", border_style="cyan"))

    # Procedure breakdown card
    proc_table = Table.grid(padding=(0, 2))
    proc_table.add_column(style="magenta", justify="right")
    proc_table.add_column(style="yellow")
    for row in proc_counts.iter_rows(named=True):
        proc_table.add_row(f"{row['proc']}:", str(row['count']))
    summary_items.append(Panel(proc_table, title="[magenta]Procedures[/magenta]", border_style="magenta"))

    # Light status breakdown card (if has_light column exists)
    if "has_light" in history.columns:
        light_table = Table.grid(padding=(0, 2))
        light_table.add_column(style="green", justify="right")
        light_table.add_column(style="yellow")

        light_count = history.filter(pl.col("has_light") == True).height
        dark_count = history.filter(pl.col("has_light") == False).height
        unknown_count = history.filter(pl.col("has_light").is_null()).height

        if light_count > 0:
            light_table.add_row("💡 Light:", str(light_count))
        if dark_count > 0:
            light_table.add_row("🌙 Dark:", str(dark_count))
        if unknown_count > 0:
            light_table.add_row("❗ Unknown:", str(unknown_count))

        summary_items.append(Panel(light_table, title="[green]Light Status[/green]", border_style="green"))

    console.print(Columns(summary_items, equal=True, expand=True))
    console.print()

    # Experiment table
    table = Table(
        title=f"Experiments" + (f" (showing last {limit})" if limit else ""),
        box=box.ROUNDED,
        show_lines=False,
        expand=False
    )

    # Add light indicator column if has_light exists
    has_light_col = "has_light" in history.columns

    if has_light_col:
        table.add_column("💡", style="bold", width=3, justify="center")

    table.add_column("Seq", style="dim", width=5, justify="right")
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Time", style="green", width=10)
    table.add_column("Proc", style="yellow", width=6)
    table.add_column("Description", style="white")

    # Group by date for visual separation
    current_date = None
    for row in history.iter_rows(named=True):
        date = row.get("date", "unknown")

        # Add separator when date changes
        if date != current_date and current_date is not None:
            table.add_row("", "", "", "", "", end_section=True)

        current_date = date

        # Build description from summary
        summary = row.get("summary", "")
        # Remove chip name and sequence number from summary for cleaner display
        desc = summary
        for prefix in [chip_name, f"{chip_group}{chip_number}"]:
            desc = desc.replace(prefix, "").strip()
        # Remove leading procedure name (already in Proc column)
        proc = row.get("proc", "")
        if desc.startswith(proc):
            desc = desc[len(proc):].strip()

        # Truncate if too long
        if len(desc) > 80:
            desc = desc[:77] + "..."

        # Get light indicator if column exists
        if has_light_col:
            has_light = row.get("has_light")
            if has_light is True:
                light_icon = "💡"
            elif has_light is False:
                light_icon = "🌙"
            else:
                light_icon = "[red]❗[/red]"  # Red for unknown/warning

            table.add_row(
                light_icon,
                str(row.get("seq", "?")),
                date,
                row.get("time_hms", "?"),
                proc,
                desc
            )
        else:
            table.add_row(
                str(row.get("seq", "?")),
                date,
                row.get("time_hms", "?"),
                proc,
                desc
            )

    console.print(table)
    console.print()

    # Footer with file info
    console.print(f"[dim]Data source: {history_file}[/dim]")

    # Show active filters
    active_filters = []
    if proc_filter:
        active_filters.append(f"proc={proc_filter}")
    if light_filter:
        active_filters.append(f"light={light_filter}")

    if active_filters:
        console.print(f"[dim]Filters: {', '.join(active_filters)}[/dim]")

    if limit:
        console.print(f"[yellow]Note:[/yellow] Showing only last {limit} experiments. Remove --limit to see all.")
