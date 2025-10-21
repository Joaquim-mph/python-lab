"""
Main Menu Screen.

The entry point for the TUI wizard, providing options to:
- Start a new plot
- Load recent configurations
- Access batch mode
- Configure settings
- View help
- Quit
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding


class MainMenuScreen(Screen):
    """Main menu screen with wizard entry points."""

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("n", "new_plot", "New Plot", show=False),
        Binding("r", "recent", "Recent", show=False),
        Binding("b", "batch", "Batch", show=False),
        Binding("s", "settings", "Settings", show=False),
        Binding("h", "help", "Help", show=False),
    ]

    CSS = """
    MainMenuScreen {
        align: center middle;
    }

    #main-container {
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
        margin-bottom: 1;
    }

    #subtitle {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 2;
    }

    .menu-button {
        width: 100%;
        margin: 1 0;
    }

    .menu-button:hover {
        background: $primary;
    }

    #help-text {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        margin-top: 2;
        text-style: dim;
    }
    """

    def compose(self) -> ComposeResult:
        """Create main menu widgets."""
        yield Header()

        with Container(id="main-container"):
            yield Static("🔬 Experiment Plotting Assistant", id="title")
            yield Static("Alisson Lab - Device Characterization", id="subtitle")

            with Vertical():
                yield Button("→ New Plot", id="new-plot", variant="primary", classes="menu-button")
                yield Button("Recent Configurations (0)", id="recent", variant="default", classes="menu-button")
                yield Button("Batch Mode", id="batch", variant="default", classes="menu-button")
                yield Button("Settings", id="settings", variant="default", classes="menu-button")
                yield Button("Help", id="help-button", variant="default", classes="menu-button")
                yield Button("Quit", id="quit", variant="error", classes="menu-button")

            yield Static("Use arrow keys to navigate, Enter to select", id="help-text")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the first button when mounted."""
        self.query_one("#new-plot", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "new-plot":
            self.action_new_plot()
        elif button_id == "recent":
            self.action_recent()
        elif button_id == "batch":
            self.action_batch()
        elif button_id == "settings":
            self.action_settings()
        elif button_id == "help-button":
            self.action_help()
        elif button_id == "quit":
            self.action_quit()

    def action_new_plot(self) -> None:
        """Start new plot wizard."""
        # TODO: Navigate to Plot Type Selector (Phase 2)
        self.app.notify("New Plot - Coming in Phase 2!")

    def action_recent(self) -> None:
        """Show recent configurations."""
        # TODO: Navigate to Recent Configs (Phase 5)
        self.app.notify("Recent Configurations - Coming in Phase 5!")

    def action_batch(self) -> None:
        """Show batch mode."""
        # TODO: Navigate to Batch Mode (Phase 6)
        self.app.notify("Batch Mode - Coming in Phase 6!")

    def action_settings(self) -> None:
        """Show settings."""
        # TODO: Navigate to Settings (Phase 6)
        self.app.notify("Settings - Coming in Phase 6!")

    def action_help(self) -> None:
        """Show help."""
        # TODO: Show help screen (Phase 7)
        help_text = """
        Keyboard Shortcuts:
        - N: New Plot
        - R: Recent Configurations
        - B: Batch Mode
        - S: Settings
        - H: Help
        - Q: Quit
        - Ctrl+Q: Quit (global)
        """
        self.app.notify(help_text.strip())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
