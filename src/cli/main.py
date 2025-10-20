#!/usr/bin/env python3
"""
Main CLI application entry point.

Aggregates all commands from the different command modules and
provides a single unified Typer app for the data processing pipeline.
"""

import typer

# Import command functions from command modules
from src.cli.commands.data_pipeline import (
    parse_all_command,
    chip_histories_command,
    full_pipeline_command,
    quick_stats_command
)
from src.cli.commands.history import show_history_command
from src.cli.commands.plot_its import plot_its_command
from src.cli.commands.plot_ivg import plot_ivg_command
from src.cli.commands.plot_transconductance import plot_transconductance_command

# Create the main Typer app
app = typer.Typer(
    name="process_and_analyze",
    help="Complete data processing and analysis pipeline for semiconductor device characterization",
    add_completion=False
)

# Register data pipeline commands
app.command(name="parse-all")(parse_all_command)
app.command(name="chip-histories")(chip_histories_command)
app.command(name="full-pipeline")(full_pipeline_command)
app.command(name="quick-stats")(quick_stats_command)

# Register history command
app.command(name="show-history")(show_history_command)

# Register plotting commands
app.command(name="plot-its")(plot_its_command)
app.command(name="plot-ivg")(plot_ivg_command)
app.command(name="plot-transconductance")(plot_transconductance_command)


def main():
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
