"""
Chip Selector Screen.

Step 3 of the wizard: Select which chip to plot from auto-discovered chips.

Auto-discovers chips from chip_histories/ directory and displays them
with experiment counts and procedure breakdowns.
"""

from __future__ import annotations
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, ListItem, ListView
from textual.binding import Binding

from src.tui.utils import discover_chips, format_chip_display, ChipInfo


class ChipSelectorScreen(Screen):
    """Chip selection screen with auto-discovery (Step 3 of wizard)."""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+b", "back", "Back", show=False),
        Binding("ctrl+n", "next", "Next", show=False),
        Binding("enter", "handle_enter", "Select/Next", show=False),
        Binding("up", "move_up", "Up", priority=True),
        Binding("down", "move_down", "Down", priority=True),
        Binding("r", "refresh", "Refresh", show=False),
    ]

    CSS = """
    ChipSelectorScreen {
        align: center middle;
    }

    #main-container {
        width: 70;
        height: auto;
        max-height: 90%;
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

    #loading-text {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin: 2 0;
    }

    #chip-list-container {
        width: 100%;
        height: auto;
        max-height: 20;
        border: solid $primary;
        margin-bottom: 2;
    }

    ListView {
        width: 100%;
        height: 100%;
    }

    ListItem {
        padding: 1 2;
    }

    ListItem:hover {
        background: $primary;
        color: $primary-background;
    }

    ListItem > .chip-name {
        text-style: bold;
        color: $accent;
    }

    ListItem > .chip-details {
        color: $text-muted;
        margin-top: 1;
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

    #error-text {
        width: 100%;
        content-align: center middle;
        color: $error;
        margin: 2 0;
    }
    """

    def __init__(
        self,
        metadata_dir: Path,
        raw_dir: Path,
        history_dir: Path,
        chip_group: str,
    ):
        super().__init__()
        self.metadata_dir = metadata_dir
        self.raw_dir = raw_dir
        self.history_dir = history_dir
        self.chip_group = chip_group
        self.chips: list[ChipInfo] = []
        self.selected_chip: ChipInfo | None = None

    def compose(self) -> ComposeResult:
        """Create chip selector widgets."""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="header-container"):
                yield Static("Select Chip", id="title")
                yield Static("[Step 2/6]", id="step-indicator")

            yield Static("Discovering chips...", id="loading-text")

            with VerticalScroll(id="chip-list-container"):
                yield ListView(id="chip-list")

            yield Static("", id="error-text")

            with Vertical(id="button-container"):
                yield Button("← Back", id="back-button", variant="default", classes="nav-button")
                yield Button("Refresh", id="refresh-button", variant="default", classes="nav-button")
                yield Button("Next →", id="next-button", variant="primary", classes="nav-button")

        yield Footer()

    def on_mount(self) -> None:
        """Discover chips when screen loads."""
        self._discover_and_populate()

    def _discover_and_populate(self) -> None:
        """Discover chips and populate the list."""
        loading = self.query_one("#loading-text", Static)
        error_text = self.query_one("#error-text", Static)
        chip_list = self.query_one("#chip-list", ListView)

        try:
            # Discover chips
            loading.update("⣾ Scanning chip histories...")
            self.chips = discover_chips(
                self.metadata_dir,
                self.raw_dir,
                self.history_dir,
                self.chip_group
            )

            # Clear loading text
            loading.update("")
            error_text.update("")

            # Populate list
            chip_list.clear()

            if not self.chips:
                error_text.update("⚠ No chips found. Check your chip_histories/ directory.")
                return

            for chip in self.chips:
                # Create list item with chip info
                item_text = format_chip_display(chip, show_details=True)
                chip_list.append(ListItem(Static(item_text)))

            # Focus the list
            chip_list.focus()

        except Exception as e:
            loading.update("")
            error_text.update(f"⚠ Error discovering chips: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle chip selection from list."""
        if event.list_view.index is not None and event.list_view.index < len(self.chips):
            self.selected_chip = self.chips[event.list_view.index]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back-button":
            self.action_back()
        elif event.button.id == "refresh-button":
            self.action_refresh()
        elif event.button.id == "next-button":
            self.action_next()

    def action_back(self) -> None:
        """Go back to plot type selector."""
        self.app.pop_screen()

    def action_refresh(self) -> None:
        """Refresh chip list."""
        self._discover_and_populate()

    def action_move_up(self) -> None:
        """Move selection up in list."""
        chip_list = self.query_one("#chip-list", ListView)
        if chip_list.index is not None and chip_list.index > 0:
            chip_list.index -= 1

    def action_move_down(self) -> None:
        """Move selection down in list."""
        chip_list = self.query_one("#chip-list", ListView)
        if chip_list.index is not None and chip_list.index < len(self.chips) - 1:
            chip_list.index += 1

    def action_handle_enter(self) -> None:
        """
        Handle Enter key intelligently:
        - If on ListView: select the chip
        - If chip selected: proceed to next
        """
        focused = self.focused

        if isinstance(focused, ListView):
            # Mark chip as selected
            if focused.index is not None and focused.index < len(self.chips):
                self.selected_chip = self.chips[focused.index]
                # Proceed to next if already selected
                if self.selected_chip:
                    self.action_next()
        elif isinstance(focused, Button):
            # Press the button
            focused.press()
        else:
            # Try to proceed if selection made
            if self.selected_chip:
                self.action_next()

    def action_next(self) -> None:
        """Proceed to config mode selector with selected chip."""
        # Get selected chip
        chip_list = self.query_one("#chip-list", ListView)

        if chip_list.index is None:
            self.app.notify("Please select a chip", severity="warning")
            return

        if chip_list.index >= len(self.chips):
            self.app.notify("Invalid chip selection", severity="error")
            return

        selected_chip = self.chips[chip_list.index]

        # Save to app config
        self.app.update_config(
            chip_number=selected_chip.chip_number,
            chip_group=selected_chip.chip_group
        )

        # Navigate to next screen (Config Mode Selector)
        # TODO: Import and navigate to ConfigModeSelectorScreen
        self.app.notify(f"Selected: {selected_chip} - Config Mode Selector coming next!")
