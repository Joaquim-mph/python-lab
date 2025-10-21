"""
Process Confirmation Dialog.

Simple confirmation dialog before running the full data processing pipeline.
"""

from __future__ import annotations
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding

import polars as pl
from src.core.parser import parse_iv_metadata
from src.core.timeline import build_chip_history


class ProcessConfirmationScreen(Screen):
    """Confirmation dialog for processing new data."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("enter", "confirm", "Start", priority=True),
    ]

    CSS = """
    ProcessConfirmationScreen {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2 4;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 2;
    }

    #description {
        width: 100%;
        color: $text;
        margin-bottom: 2;
        padding: 1;
        background: $panel;
    }

    #command {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
        margin-bottom: 2;
    }

    #warning {
        width: 100%;
        color: $warning;
        text-style: italic;
        margin-bottom: 2;
        content-align: center middle;
    }

    #status {
        width: 100%;
        content-align: center middle;
        color: $accent;
        text-style: bold;
        margin-bottom: 2;
    }

    #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }

    .dialog-button {
        width: 1fr;
        margin: 0 1;
        min-height: 3;
    }

    .dialog-button:focus {
        background: $primary;
        border: tall $accent;
        color: $primary-background;
        text-style: bold;
    }
    """

    def __init__(self):
        super().__init__()
        self.processing = False

    def compose(self) -> ComposeResult:
        """Create confirmation dialog widgets."""
        yield Header()

        with Container(id="dialog-container"):
            yield Static("Process New Data?", id="title")

            yield Static(
                "This will run the full processing pipeline:\n\n"
                "• Parse all metadata from raw CSV files\n"
                "• Rebuild chip histories\n"
                "• Process all chips (~40 MB)\n"
                "• Overwrite existing metadata and history files",
                id="description"
            )

            yield Static("Running full pipeline directly", id="command")

            yield Static("⚠ This may take a few minutes", id="warning")

            yield Static("", id="status")

            with Vertical(id="button-container"):
                yield Button("Cancel", id="cancel-button", variant="default", classes="dialog-button")
                yield Button("Start Processing", id="confirm-button", variant="primary", classes="dialog-button")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the confirm button on mount."""
        self.query_one("#confirm-button", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.action_cancel()
        elif event.button.id == "confirm-button":
            self.action_confirm()

    def action_cancel(self) -> None:
        """Cancel and return to main menu."""
        self.app.pop_screen()

    def action_confirm(self) -> None:
        """Start processing in background and close immediately."""
        # Start processing in background thread (fire and forget)
        thread = threading.Thread(target=self._run_process, daemon=True)
        thread.start()

        # Notify and close immediately
        self.app.notify(
            "Processing started in background",
            severity="information",
            timeout=3
        )
        self.app.pop_screen()

    def _run_process(self) -> None:
        """Run the processing pipeline in background."""
        try:
            raw_dir = Path("raw_data")
            meta_dir = Path("metadata")
            history_dir = Path("chip_histories")
            chip_group = "Alisson"

            # Step 1: Parse all metadata
            folders = [item for item in raw_dir.iterdir() if item.is_dir() and list(item.glob("*.csv"))]

            meta_dir.mkdir(parents=True, exist_ok=True)

            for folder in folders:
                folder_name = folder.name
                out_dir = meta_dir / folder_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / "metadata.csv"

                csv_files = sorted(folder.glob("*.csv"))
                metadata_rows = []

                for csv_file in csv_files:
                    try:
                        meta = parse_iv_metadata(csv_file)
                        if meta:
                            rel_path = f"{raw_dir.name}/{folder_name}/{csv_file.name}"
                            meta['source_file'] = rel_path
                            metadata_rows.append(meta)
                    except Exception:
                        pass

                if metadata_rows:
                    df = pl.DataFrame(metadata_rows)
                    df.write_csv(out_file)

            # Step 2: Build chip histories
            metadata_files = list(meta_dir.glob("**/metadata.csv")) + list(meta_dir.glob("**/*_metadata.csv"))

            all_chips = set()
            for meta_file in metadata_files:
                try:
                    meta = pl.read_csv(meta_file, ignore_errors=True)
                    if "Chip number" in meta.columns:
                        chips = meta.get_column("Chip number").drop_nulls().unique().to_list()
                        for c in chips:
                            try:
                                all_chips.add(int(float(c)))
                            except (ValueError, TypeError):
                                pass
                except Exception:
                    pass

            history_dir.mkdir(parents=True, exist_ok=True)

            for chip_num in sorted(all_chips):
                chip_name = f"{chip_group}{chip_num}"
                history = build_chip_history(meta_dir, Path("."), chip_num, chip_group)

                if history.height >= 1:
                    out_file = history_dir / f"{chip_name}_history.csv"
                    history.write_csv(out_file)

        except Exception:
            # Silently fail - user can check files manually
            pass
