"""
Plot Generation and Results Screens.

Step 6/6 of the wizard: Generate the plot and show results/errors.
"""

from __future__ import annotations
import time
import threading
from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, ProgressBar
from textual.binding import Binding
from textual import events


class PlotGenerationScreen(Screen):
    """Plot generation progress screen (Step 6/6)."""

    def __init__(
        self,
        chip_number: int,
        chip_group: str,
        plot_type: str,
        seq_numbers: List[int],
        config: dict,
    ):
        super().__init__()
        self.chip_number = chip_number
        self.chip_group = chip_group
        self.plot_type = plot_type
        self.seq_numbers = seq_numbers
        self.config = config
        self.generation_thread = None
        self.start_time = None

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    CSS = """
    PlotGenerationScreen {
        align: center middle;
    }

    #main-container {
        width: 70;
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

    #status {
        width: 100%;
        content-align: center middle;
        color: $text;
        margin-bottom: 2;
        min-height: 3;
    }

    #progress-bar {
        width: 100%;
        margin-bottom: 2;
    }

    #current-task {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create generation progress widgets."""
        yield Header()

        with Container(id="main-container"):
            yield Static("Generating Plot...", id="title")
            yield Static("⣾ Initializing...", id="status")
            yield ProgressBar(total=100, show_eta=False, id="progress-bar")
            yield Static("Starting plot generation", id="current-task")

        yield Footer()

    def on_mount(self) -> None:
        """Start plot generation when screen loads."""
        self.start_time = time.time()

        # Start generation in background thread
        self.generation_thread = threading.Thread(target=self._generate_plot, daemon=True)
        self.generation_thread.start()

    def _generate_plot(self) -> None:
        """Generate the plot in background thread."""
        try:
            # Force non-interactive matplotlib backend for thread-safety
            import matplotlib
            matplotlib.use('Agg')  # Non-GUI backend for headless plotting

            # Import plotting modules
            from pathlib import Path as PathLib
            from src.plotting import its, ivg, transconductance, plot_utils

            # Step 1: Load metadata
            self.app.call_from_thread(self._update_progress, 10, "⣾ Loading experiment metadata...")

            metadata_dir = PathLib(self.config.get("metadata_dir", "metadata"))
            raw_dir = PathLib(self.config.get("raw_dir", "."))

            # Load metadata using combine_metadata_by_seq
            meta = plot_utils.combine_metadata_by_seq(
                metadata_dir,
                raw_dir,
                float(self.chip_number),
                self.seq_numbers,
                self.chip_group
            )

            if meta.height == 0:
                raise ValueError("No metadata loaded for selected experiments")

            self.app.call_from_thread(self._update_progress, 30, f"⣾ Loaded {meta.height} experiment(s)...")

            # Step 2: Setup output directory
            output_dir = PathLib(self.config.get("output_dir", f"figs/{self.chip_group}{self.chip_number}/"))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Step 3: Generate plot tag from seq numbers
            seq_str = "_".join(map(str, self.seq_numbers[:10]))
            if len(self.seq_numbers) > 10:
                seq_str += f"_plus{len(self.seq_numbers) - 10}more"
            plot_tag = seq_str

            self.app.call_from_thread(self._update_progress, 50, "⣾ Generating plot...")

            # Step 4: Call appropriate plotting function based on plot type
            if self.plot_type == "ITS":
                # ITS plot
                its.FIG_DIR = output_dir

                # Get ITS-specific config
                legend_by = self.config.get("legend_by", "led_voltage")
                baseline_t = self.config.get("baseline", 60.0)
                padding = self.config.get("padding", 0.05)

                # Check if all ITS are dark (no laser)
                import polars as pl
                its_df = meta.filter(pl.col("proc") == "ITS")
                all_dark = False

                if its_df.height > 0:
                    # Check laser toggle column if available
                    if "Laser toggle" in its_df.columns:
                        try:
                            laser_toggle_col = its_df["Laser toggle"]
                            toggles = []
                            for val in laser_toggle_col.to_list():
                                if isinstance(val, bool):
                                    toggles.append(val)
                                elif isinstance(val, str):
                                    toggles.append(val.lower() == "true")
                                else:
                                    toggles.append(True)

                            if all(not t for t in toggles):
                                all_dark = True
                        except Exception:
                            pass

                # Call appropriate ITS plotting function
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

            elif self.plot_type == "IVg":
                # IVg plot
                ivg.FIG_DIR = output_dir
                ivg.plot_ivg_sequence(meta, raw_dir, plot_tag)

            elif self.plot_type == "Transconductance":
                # Transconductance plot
                transconductance.FIG_DIR = output_dir

                # Get transconductance-specific config
                method = self.config.get("method", "gradient")

                if method == "savgol":
                    window_length = self.config.get("window_length", 9)
                    polyorder = self.config.get("polyorder", 3)
                    transconductance.plot_ivg_transconductance_savgol(
                        meta,
                        raw_dir,
                        plot_tag,
                        window_length=window_length,
                        polyorder=polyorder
                    )
                else:
                    transconductance.plot_ivg_transconductance(
                        meta,
                        raw_dir,
                        plot_tag
                    )
            else:
                raise ValueError(f"Unknown plot type: {self.plot_type}")

            self.app.call_from_thread(self._update_progress, 90, "⣾ Saving file...")

            # Step 5: Determine output file path
            chip_name = f"{self.chip_group}{self.chip_number}".lower()
            plot_type_lower = self.plot_type.lower()

            if self.plot_type == "ITS":
                filename = f"chip{self.chip_number}_ITS_overlay_{plot_tag}.png"
            elif self.plot_type == "IVg":
                filename = f"Encap{self.chip_number}_IVg_sequence_{plot_tag}.png"
            elif self.plot_type == "Transconductance":
                method = self.config.get("method", "gradient")
                if method == "savgol":
                    filename = f"gm_savgol_{plot_tag}.png"
                else:
                    filename = f"gm_sequence_{plot_tag}.png"

            output_path = output_dir / filename

            # Get file size
            file_size = 0.0
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # Convert to MB

            # Complete
            self.app.call_from_thread(self._update_progress, 100, "✓ Complete!")
            time.sleep(0.3)

            # Show success screen
            elapsed = time.time() - self.start_time
            self.app.call_from_thread(self._on_success, elapsed, output_path, file_size)

        except Exception as e:
            # Show error screen
            import traceback
            error_details = traceback.format_exc()
            self.app.call_from_thread(self._on_error, str(e), type(e).__name__, error_details)

    def _update_progress(self, progress: float, status: str) -> None:
        """Update progress bar and status from background thread."""
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)

        status_widget = self.query_one("#status", Static)
        status_widget.update(status)

    def _on_success(self, elapsed: float, output_path: Path, file_size: float) -> None:
        """Handle successful plot generation."""
        # Replace current screen with success screen
        self.app.pop_screen()

        self.app.push_screen(PlotSuccessScreen(
            output_path=output_path,
            file_size=file_size,
            num_experiments=len(self.seq_numbers),
            elapsed=elapsed,
            chip_number=self.chip_number,
            chip_group=self.chip_group,
            plot_type=self.plot_type,
        ))

    def _on_error(self, error_msg: str, error_type: str, error_details: str) -> None:
        """Handle plot generation error."""
        # Replace current screen with error screen
        self.app.pop_screen()

        self.app.push_screen(PlotErrorScreen(
            error_type=error_type,
            error_msg=error_msg,
            config=self.config,
            error_details=error_details,
        ))

    def action_cancel(self) -> None:
        """Cancel plot generation."""
        # TODO: Implement cancellation
        self.app.notify("Cancellation not yet implemented", severity="warning")


class PlotSuccessScreen(Screen):
    """Success screen after plot generation."""

    def __init__(
        self,
        output_path: Path,
        file_size: float,
        num_experiments: int,
        elapsed: float,
        chip_number: int = None,
        chip_group: str = None,
        plot_type: str = None,
    ):
        super().__init__()
        self.output_path = output_path
        self.file_size = file_size
        self.num_experiments = num_experiments
        self.elapsed = elapsed
        self.chip_number = chip_number
        self.chip_group = chip_group
        self.plot_type = plot_type

    BINDINGS = [
        Binding("escape", "main_menu", "Main Menu", priority=True),
    ]

    CSS = """
    PlotSuccessScreen {
        align: center middle;
    }

    #main-container {
        width: 70;
        height: auto;
        background: $surface;
        border: thick $success;
        padding: 2 4;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $success;
        margin-bottom: 2;
    }

    .info-row {
        color: $text;
        margin-left: 2;
        margin-bottom: 0;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 2;
    }

    .nav-button {
        width: 1fr;
        margin: 0 1;
    }

    .nav-button:focus {
        background: $primary;
        border: tall $accent;
        color: $primary-background;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Create success screen widgets."""
        yield Header()

        with Container(id="main-container"):
            yield Static("Plot Generated Successfully! ✓", id="title")

            yield Static("Output file:", classes="section-title")
            yield Static(str(self.output_path), classes="info-row")

            yield Static(f"File size: {self.file_size:.1f} MB", classes="info-row")
            yield Static(f"Experiments plotted: {self.num_experiments}", classes="info-row")
            yield Static(f"Generation time: {self.elapsed:.1f}s", classes="info-row")

            yield Static("", classes="info-row")
            yield Static("Configuration saved to recent history.", classes="info-row")

            with Horizontal(id="button-container"):
                yield Button("Open File", id="open-button", variant="default", classes="nav-button")
                yield Button("Plot Another", id="another-button", variant="default", classes="nav-button")
                yield Button("Main Menu", id="menu-button", variant="default", classes="nav-button")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the main menu button."""
        self.query_one("#menu-button", Button).focus()

    def on_key(self, event: events.Key) -> None:
        """Handle arrow key navigation between buttons."""
        buttons = [
            self.query_one("#open-button", Button),
            self.query_one("#another-button", Button),
            self.query_one("#menu-button", Button),
        ]

        focused_idx = next((i for i, b in enumerate(buttons) if b.has_focus), None)

        if focused_idx is not None:
            if event.key in ("left", "up"):
                new_idx = (focused_idx - 1) % len(buttons)
                buttons[new_idx].focus()
                event.prevent_default()
            elif event.key in ("right", "down"):
                new_idx = (focused_idx + 1) % len(buttons)
                buttons[new_idx].focus()
                event.prevent_default()

    def on_button_focus(self, event) -> None:
        """Add arrow indicator to focused button."""
        # Remove arrows from all buttons
        for button in self.query(".nav-button"):
            label = str(button.label)
            if label.startswith("→ "):
                button.label = label[2:]

        # Add arrow to focused button
        focused_button = event.button
        label = str(focused_button.label)
        if not label.startswith("→ "):
            focused_button.label = f"→ {label}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "open-button":
            self.action_open_file()
        elif event.button.id == "another-button":
            self.action_plot_another()
        elif event.button.id == "menu-button":
            self.action_main_menu()

    def action_open_file(self) -> None:
        """Open the generated file."""
        # TODO: Implement file opening
        self.app.notify(f"Opening {self.output_path.name}...", severity="information")

    def action_plot_another(self) -> None:
        """Start a new plot of the same type."""
        # Pop all wizard screens to get back to main menu
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

        # If we have the required info, jump directly to experiment selector
        if self.chip_number and self.chip_group and self.plot_type:
            from src.tui.screens.experiment_selector import ExperimentSelectorScreen
            from pathlib import Path as PathLib

            # Get config paths
            metadata_dir = PathLib(self.app.plot_config.get("metadata_dir", "metadata"))
            raw_dir = PathLib(self.app.plot_config.get("raw_dir", "."))

            # Push experiment selector for the same plot type and chip
            self.app.push_screen(ExperimentSelectorScreen(
                chip_number=self.chip_number,
                chip_group=self.chip_group,
                plot_type=self.plot_type,
                metadata_dir=metadata_dir,
                raw_dir=raw_dir,
            ))

    def action_main_menu(self) -> None:
        """Return to main menu."""
        # Pop screens until we're back at the main menu (keep base + MainMenuScreen)
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()


class PlotErrorScreen(Screen):
    """Error screen if plot generation fails."""

    def __init__(self, error_type: str, error_msg: str, config: dict, error_details: str = ""):
        super().__init__()
        self.error_type = error_type
        self.error_msg = error_msg
        self.config = config
        self.error_details = error_details

    BINDINGS = [
        Binding("escape", "main_menu", "Main Menu", priority=True),
    ]

    CSS = """
    PlotErrorScreen {
        align: center middle;
    }

    #main-container {
        width: 70;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 2 4;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
        margin-bottom: 2;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    .error-text {
        color: $text;
        margin-left: 2;
        margin-bottom: 1;
    }

    .suggestion-text {
        color: $warning;
        margin-left: 2;
        margin-bottom: 1;
        text-style: italic;
    }

    #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 2;
    }

    .nav-button {
        width: 1fr;
        margin: 0 1;
    }

    .nav-button:focus {
        background: $primary;
        border: tall $accent;
        color: $primary-background;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Create error screen widgets."""
        yield Header()

        with Container(id="main-container"):
            yield Static("Plot Generation Failed ✗", id="title")

            yield Static("Error Type:", classes="section-title")
            yield Static(self.error_type, classes="error-text")

            yield Static("Message:", classes="section-title")
            yield Static(self.error_msg, classes="error-text")

            # Generate suggestion based on error
            suggestion = self._generate_suggestion()
            if suggestion:
                yield Static("Suggestion:", classes="section-title")
                yield Static(suggestion, classes="suggestion-text")

            with Horizontal(id="button-container"):
                yield Button("View Details", id="details-button", variant="default", classes="nav-button")
                yield Button("Edit Config", id="edit-button", variant="default", classes="nav-button")
                yield Button("Main Menu", id="menu-button", variant="default", classes="nav-button")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the edit config button."""
        self.query_one("#edit-button", Button).focus()

    def on_key(self, event: events.Key) -> None:
        """Handle arrow key navigation between buttons."""
        buttons = [
            self.query_one("#details-button", Button),
            self.query_one("#edit-button", Button),
            self.query_one("#menu-button", Button),
        ]

        focused_idx = next((i for i, b in enumerate(buttons) if b.has_focus), None)

        if focused_idx is not None:
            if event.key in ("left", "up"):
                new_idx = (focused_idx - 1) % len(buttons)
                buttons[new_idx].focus()
                event.prevent_default()
            elif event.key in ("right", "down"):
                new_idx = (focused_idx + 1) % len(buttons)
                buttons[new_idx].focus()
                event.prevent_default()

    def on_button_focus(self, event) -> None:
        """Add arrow indicator to focused button."""
        # Remove arrows from all buttons
        for button in self.query(".nav-button"):
            label = str(button.label)
            if label.startswith("→ "):
                button.label = label[2:]

        # Add arrow to focused button
        focused_button = event.button
        label = str(focused_button.label)
        if not label.startswith("→ "):
            focused_button.label = f"→ {label}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "details-button":
            self.action_view_details()
        elif event.button.id == "edit-button":
            self.action_edit_config()
        elif event.button.id == "menu-button":
            self.action_main_menu()

    def action_view_details(self) -> None:
        """View error details."""
        if self.error_details:
            # Show full traceback in a notification
            self.app.notify(
                f"Full traceback:\n{self.error_details}",
                severity="error",
                timeout=10
            )
        else:
            self.app.notify("No additional error details available", severity="information")

    def action_edit_config(self) -> None:
        """Go back to edit configuration."""
        # Pop this error screen to go back to preview
        self.app.pop_screen()

    def action_main_menu(self) -> None:
        """Return to main menu."""
        # Pop screens until we're back at the main menu (keep base + MainMenuScreen)
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def _generate_suggestion(self) -> Optional[str]:
        """Generate helpful suggestion based on error."""
        error_lower = self.error_msg.lower()

        if "filter" in error_lower:
            return "Try adjusting or removing filters to include more experiments."
        elif "not found" in error_lower or "does not exist" in error_lower:
            return "Check that all required files exist in the specified directories."
        elif "empty" in error_lower or "no data" in error_lower:
            return "Verify that the selected experiments contain valid measurement data."
        else:
            return "Check your configuration and try again."
