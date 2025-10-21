"""
Plot Type Selector Screen.

Step 2 of the wizard: Select the type of plot to generate.

Options:
- ITS (Current vs Time): Photocurrent time series with light/dark cycles
- IVg (Transfer Curves): Gate voltage sweep characteristics
- Transconductance: gm = dI/dVg derivative analysis
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, RadioButton, RadioSet
from textual.binding import Binding


class PlotTypeSelectorScreen(Screen):
    """Plot type selection screen (Step 2 of wizard)."""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+b", "back", "Back", show=False),
        Binding("ctrl+n", "next", "Next", show=False),
        Binding("enter", "handle_enter", "Select/Next", show=False),
        Binding("up", "focus_previous", "Up", show=False),
        Binding("down", "focus_next", "Down", show=False),
    ]

    CSS = """
    PlotTypeSelectorScreen {
        align: center middle;
    }

    #main-container {
        width: 70;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2 4;
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

    #step-indicator {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
        margin-bottom: 1;
    }

    RadioSet {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: $panel;
    }

    RadioButton {
        margin: 1 0;
    }

    .plot-description {
        width: 100%;
        color: $text-muted;
        margin: 0 2 1 2;
        padding: 1;
        background: $panel-lighten-1;
    }

    #button-container {
        width: 100%;
        height: auto;
        layout: horizontal;
    }

    .nav-button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create plot type selector widgets."""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="header-container"):
                yield Static("Select Plot Type", id="title")
                yield Static("[Step 1/6]", id="step-indicator")

            with RadioSet(id="plot-type-radio"):
                yield RadioButton("ITS (Current vs Time)", id="its-radio", value=True)
                yield RadioButton("IVg (Transfer Curves)", id="ivg-radio")
                yield RadioButton("Transconductance", id="transconductance-radio")

            # Descriptions below radio buttons
            yield Static(
                "[bold]ITS (Current vs Time)[/bold]\n"
                "Plot photocurrent time series with light/dark cycles. Best for analyzing photoresponse behavior.",
                classes="plot-description"
            )
            yield Static(
                "[bold]IVg (Transfer Curves)[/bold]\n"
                "Plot gate voltage sweep characteristics. Shows device transfer behavior (Id vs Vg).",
                classes="plot-description"
            )
            yield Static(
                "[bold]Transconductance[/bold]\n"
                "Plot gm = dI/dVg from IVg data. Derivative analysis of transfer curves.",
                classes="plot-description"
            )

            with Vertical(id="button-container"):
                yield Button("← Back", id="back-button", variant="default", classes="nav-button")
                yield Button("Next →", id="next-button", variant="primary", classes="nav-button")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen - focus the radio set."""
        self.query_one(RadioSet).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-button":
            self.action_back()
        elif event.button.id == "next-button":
            self.action_next()

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def action_handle_enter(self) -> None:
        """
        Handle Enter key intelligently:
        - If focused on RadioSet: select the focused radio button
        - If focused on Next button or radio already selected: proceed to next screen
        """
        focused = self.focused
        radio_set = self.query_one(RadioSet)

        # Check if we're focused on the RadioSet or a RadioButton
        if focused == radio_set or (hasattr(focused, 'parent') and focused.parent == radio_set):
            # First Enter: Select the radio button if not already selected
            if radio_set.pressed_button is None:
                # No selection yet, let the RadioSet handle it
                radio_set.action_toggle_button()
            else:
                # Already selected, proceed to next
                self.action_next()
        elif isinstance(focused, Button):
            # Focused on a button, press it
            focused.press()
        else:
            # Default: try to proceed if selection is made
            if radio_set.pressed_button is not None:
                self.action_next()

    def action_next(self) -> None:
        """Proceed to chip selector with selected plot type."""
        # Get selected plot type
        radio_set = self.query_one(RadioSet)
        selected = radio_set.pressed_button

        if selected is None:
            self.app.notify("Please select a plot type", severity="warning")
            return

        # Map radio button to plot type
        plot_type_map = {
            "its-radio": "ITS",
            "ivg-radio": "IVg",
            "transconductance-radio": "Transconductance",
        }

        plot_type = plot_type_map.get(selected.id)

        if plot_type is None:
            self.app.notify("Invalid plot type selected", severity="error")
            return

        # Save plot type to app state
        self.app.update_config(plot_type=plot_type)

        # Navigate to Chip Selector
        from src.tui.screens.chip_selector import ChipSelectorScreen

        self.app.push_screen(ChipSelectorScreen(
            metadata_dir=self.app.metadata_dir,
            raw_dir=self.app.raw_dir,
            history_dir=self.app.history_dir,
            chip_group=self.app.chip_group,
        ))
