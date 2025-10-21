"""
Experiment Selector Screen (Quick Plot Mode).

Step 4a of the wizard: Interactively select experiments for quick plotting.
Wraps the existing interactive_selector.py into the wizard flow.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List

import polars as pl
from textual.app import ComposeResult
from textual.screen import Screen
from textual.binding import Binding

from src.interactive_selector import ExperimentSelectorScreen as BaseExperimentSelector
from src.core.timeline import build_chip_history


class ExperimentSelectorScreen(Screen):
    """
    Experiment selector screen for the wizard (Step 4a - Quick mode).

    Wraps the existing ExperimentSelectorScreen and integrates it into the wizard.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        chip_number: int,
        chip_group: str,
        plot_type: str,
        metadata_dir: Path,
        raw_dir: Path,
    ):
        super().__init__()
        self.chip_number = chip_number
        self.chip_group = chip_group
        self.plot_type = plot_type
        self.metadata_dir = metadata_dir
        self.raw_dir = raw_dir

    def compose(self) -> ComposeResult:
        """Compose is handled by the nested screen."""
        # This screen doesn't have its own widgets - it immediately pushes the selector
        return []

    def on_mount(self) -> None:
        """Load chip history and launch the interactive selector."""
        # Build chip history
        try:
            history_df = build_chip_history(
                self.metadata_dir,
                self.raw_dir,
                self.chip_number,
                self.chip_group
            )

            if history_df.height == 0:
                self.app.notify(
                    f"No experiments found for {self.chip_group}{self.chip_number}",
                    severity="error",
                    timeout=5
                )
                self.app.pop_screen()
                return

            # Create the selector screen with proper filtering
            title = f"Select {self.plot_type} Experiments - {self.chip_group}{self.chip_number}"

            selector = BaseExperimentSelector(
                chip_number=self.chip_number,
                chip_group=self.chip_group,
                history_df=history_df,
                proc_filter=self.plot_type,
                title=title
            )

            # Push the selector and handle the result
            self.app.push_screen(selector, callback=self._on_selection)

        except Exception as e:
            self.app.notify(
                f"Error loading experiments: {str(e)}",
                severity="error",
                timeout=5
            )
            self.app.pop_screen()

    def _on_selection(self, result: Optional[List[int]]) -> None:
        """Handle the selection result from the interactive selector."""
        if result is None:
            # User cancelled - go back to config mode
            self.app.pop_screen()
        else:
            # User confirmed selection - save and proceed to preview
            self.app.update_config(seq_numbers=result)

            # Pop this screen (experiment selector wrapper)
            self.app.pop_screen()

            # Navigate to preview screen (Step 5/6)
            from src.tui.screens.preview_screen import PreviewScreen

            # Get current config
            config = self.app.plot_config.copy()

            self.app.push_screen(PreviewScreen(
                chip_number=self.chip_number,
                chip_group=self.chip_group,
                plot_type=self.plot_type,
                seq_numbers=result,
                config=config,
            ))

    def action_cancel(self) -> None:
        """Cancel and return to config mode."""
        self.app.pop_screen()
