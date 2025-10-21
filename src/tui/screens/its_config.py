"""
ITS Configuration Screen (Custom Mode).

Step 4b of the wizard: Configure parameters for ITS (Current vs Time) plots.
"""

from __future__ import annotations
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Input, Select, RadioButton, RadioSet, Label
from textual.binding import Binding


class ITSConfigScreen(Screen):
    """ITS configuration screen (Step 4b - Custom mode)."""

    def __init__(self, chip_number: int, chip_group: str, plot_type: str):
        super().__init__()
        self.chip_number = chip_number
        self.chip_group = chip_group
        self.plot_type = plot_type

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+b", "back", "Back", show=False),
        Binding("ctrl+s", "save_config", "Save Config", show=False),
    ]

    CSS = """
    ITSConfigScreen {
        align: center middle;
    }

    #main-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 2 4;
        overflow-y: auto;
    }

    #header-container {
        width: 100%;
        height: auto;
        margin-bottom: 2;
    }

    #title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    #chip-info {
        width: 100%;
        content-align: center middle;
        color: $accent;
        margin-bottom: 1;
    }

    #step-indicator {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
        margin-bottom: 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }

    .form-row {
        height: 3;
        margin-bottom: 0;
    }

    .form-label {
        width: 20;
        padding-top: 1;
        color: $text;
    }

    .form-input {
        width: 30;
    }

    .form-help {
        width: 1fr;
        padding-top: 1;
        padding-left: 2;
        color: $text-muted;
        text-style: dim;
    }

    RadioSet {
        height: auto;
        margin-bottom: 1;
    }

    RadioButton {
        margin: 0 2 0 0;
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
    """

    def compose(self) -> ComposeResult:
        """Create ITS configuration widgets."""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="header-container"):
                yield Static("Custom Configuration - ITS", id="title")
                yield Static(
                    f"[bold]{self.chip_group}{self.chip_number}[/bold] - {self.plot_type}",
                    id="chip-info"
                )
                yield Static("[Step 4/6]", id="step-indicator")

            # Selection Mode
            yield Static("Selection Mode:", classes="section-title")
            with RadioSet(id="selection-mode-radio"):
                yield RadioButton("Interactive", id="interactive-radio", value=True)
                yield RadioButton("Auto", id="auto-radio")
                yield RadioButton("Manual", id="manual-radio")

            # Filters Section
            yield Static("─── Filters (Optional) ───────────────", classes="section-title")

            with Horizontal(classes="form-row"):
                yield Label("VG (V):", classes="form-label")
                yield Input(placeholder="Gate voltage filter", id="vg-filter", classes="form-input")
                yield Static("Gate voltage filter", classes="form-help")

            with Horizontal(classes="form-row"):
                yield Label("Wavelength (nm):", classes="form-label")
                yield Input(placeholder="Laser wavelength", id="wavelength-filter", classes="form-input")
                yield Static("Laser wavelength", classes="form-help")

            with Horizontal(classes="form-row"):
                yield Label("Date:", classes="form-label")
                yield Input(placeholder="YYYY-MM-DD", id="date-filter", classes="form-input")
                yield Static("YYYY-MM-DD format", classes="form-help")

            # Plot Options Section
            yield Static("─── Plot Options ──────────────────────", classes="section-title")

            with Horizontal(classes="form-row"):
                yield Label("Legend by:", classes="form-label")
                yield Select(
                    [
                        ("LED Voltage", "led_voltage"),
                        ("Wavelength", "wavelength"),
                        ("Gate Voltage", "vg"),
                    ],
                    value="led_voltage",
                    id="legend-by-select",
                    classes="form-input"
                )
                yield Static("Legend grouping", classes="form-help")

            with Horizontal(classes="form-row"):
                yield Label("Baseline (s):", classes="form-label")
                yield Input(value="60.0", id="baseline-input", classes="form-input")
                yield Static("Baseline time", classes="form-help")

            with Horizontal(classes="form-row"):
                yield Label("Padding:", classes="form-label")
                yield Input(value="0.05", id="padding-input", classes="form-input")
                yield Static("Y-axis padding", classes="form-help")

            with Horizontal(classes="form-row"):
                yield Label("Output dir:", classes="form-label")
                yield Input(
                    value=f"figs/{self.chip_group}{self.chip_number}/",
                    id="output-dir-input",
                    classes="form-input"
                )
                yield Static("Output directory", classes="form-help")

            # Buttons
            with Horizontal(id="button-container"):
                yield Button("Save Config", id="save-button", variant="default", classes="nav-button")
                yield Button("← Back", id="back-button", variant="default", classes="nav-button")
                yield Button("Next →", id="next-button", variant="primary", classes="nav-button")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen."""
        # Focus the first radio button
        self.query_one(RadioSet).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-button":
            self.action_back()
        elif event.button.id == "next-button":
            self.action_next()
        elif event.button.id == "save-button":
            self.action_save_config()

    def action_back(self) -> None:
        """Go back to config mode selector."""
        self.app.pop_screen()

    def action_next(self) -> None:
        """Collect configuration and proceed to next step."""
        # Collect all form values
        config = self._collect_config()

        # Validate configuration
        validation_error = self._validate_config(config)
        if validation_error:
            self.notify(validation_error, severity="error", timeout=5)
            return

        # Save to app state
        self.app.update_config(**config)

        # Navigate based on selection mode
        if config["selection_mode"] == "interactive":
            # Launch interactive selector
            from src.tui.screens.experiment_selector import ExperimentSelectorScreen

            self.app.push_screen(ExperimentSelectorScreen(
                chip_number=self.chip_number,
                chip_group=self.chip_group,
                plot_type=self.plot_type,
                metadata_dir=self.app.metadata_dir,
                raw_dir=self.app.raw_dir,
            ))
        else:
            # Go directly to preview (auto/manual mode)
            # For auto/manual, we need to determine seq_numbers automatically
            # TODO: Implement auto-selection logic
            # For now, use empty list as placeholder
            from src.tui.screens.preview_screen import PreviewScreen

            self.app.push_screen(PreviewScreen(
                chip_number=self.chip_number,
                chip_group=self.chip_group,
                plot_type=self.plot_type,
                seq_numbers=[],  # TODO: Auto-select based on filters
                config=config,
            ))

    def action_save_config(self) -> None:
        """Save configuration to JSON file."""
        config = self._collect_config()

        # TODO: Implement JSON export
        self.app.notify(
            f"Config saved (feature coming soon): {len(config)} parameters",
            severity="information",
            timeout=3
        )

    def _validate_config(self, config: dict) -> str | None:
        """Validate configuration values.

        Returns error message if validation fails, None if OK.
        """
        # Validate baseline (must be positive)
        baseline = config.get("baseline")
        if baseline is not None and baseline <= 0:
            return "Baseline must be a positive number"

        # Validate padding (must be between 0 and 1)
        padding = config.get("padding")
        if padding is not None and (padding < 0 or padding > 1):
            return "Padding must be between 0 and 1"

        # Validate wavelength (typical range 200-2000 nm)
        wavelength = config.get("wavelength_filter")
        if wavelength is not None and (wavelength < 200 or wavelength > 2000):
            return "Wavelength should be between 200 and 2000 nm"

        # Validate date format (basic check)
        date_filter = config.get("date_filter")
        if date_filter:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_filter):
                return "Date must be in YYYY-MM-DD format"

        return None

    def _collect_config(self) -> dict:
        """Collect all configuration values from the form."""
        # Get selection mode
        radio_set = self.query_one("#selection-mode-radio", RadioSet)
        selected_radio = radio_set.pressed_button

        mode_map = {
            "interactive-radio": "interactive",
            "auto-radio": "auto",
            "manual-radio": "manual",
        }
        selection_mode = mode_map.get(selected_radio.id if selected_radio else "", "interactive")

        # Get filter values
        vg_filter = self.query_one("#vg-filter", Input).value.strip()
        wavelength_filter = self.query_one("#wavelength-filter", Input).value.strip()
        date_filter = self.query_one("#date-filter", Input).value.strip()

        # Get plot options
        legend_by = self.query_one("#legend-by-select", Select).value
        baseline = self.query_one("#baseline-input", Input).value.strip()
        padding = self.query_one("#padding-input", Input).value.strip()
        output_dir = self.query_one("#output-dir-input", Input).value.strip()

        # Build config dict with type conversion and error handling
        config = {
            "selection_mode": selection_mode,
            "legend_by": legend_by,
            "output_dir": output_dir,
        }

        # Convert numeric values with error handling
        try:
            config["vg_filter"] = float(vg_filter) if vg_filter else None
        except ValueError:
            config["vg_filter"] = None

        try:
            config["wavelength_filter"] = float(wavelength_filter) if wavelength_filter else None
        except ValueError:
            config["wavelength_filter"] = None

        config["date_filter"] = date_filter if date_filter else None

        try:
            config["baseline"] = float(baseline) if baseline else 60.0
        except ValueError:
            config["baseline"] = 60.0

        try:
            config["padding"] = float(padding) if padding else 0.05
        except ValueError:
            config["padding"] = 0.05

        return config
