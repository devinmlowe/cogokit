"""Main COGOpro TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from cogopro.core.job import Job
from cogopro.tui.screens.main_menu import MainMenuScreen


class COGOProApp(App):
    """COGO+ Pro — interactive terminal user interface."""

    TITLE = "COGO+ Pro"
    SUB_TITLE = "Coordinate Geometry & Surveying"

    CSS = """
    Screen {
        background: $surface;
    }

    #main-menu {
        layout: vertical;
        align: center middle;
    }

    .menu-group {
        width: 60;
        height: auto;
        margin: 1 2;
        padding: 1 2;
        border: solid $primary;
    }

    .menu-group-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    .form-container {
        layout: vertical;
        padding: 1 2;
        overflow-y: auto;
    }

    .form-row {
        layout: horizontal;
        height: 3;
        margin-bottom: 0;
    }

    .form-label {
        width: 20;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }

    .form-input {
        width: 1fr;
        height: 3;
    }

    .result-panel {
        margin: 1 2;
        padding: 1 2;
        border: solid $accent;
        height: auto;
        max-height: 20;
        overflow-y: auto;
    }

    .result-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .result-row {
        height: 1;
    }

    .button-bar {
        layout: horizontal;
        height: 3;
        margin: 1 2;
        align: center middle;
    }

    .button-bar Button {
        margin: 0 1;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        margin: 1 2 0 2;
        text-align: center;
    }

    .error-text {
        color: $error;
        margin: 0 2;
    }

    .point-table {
        height: 1fr;
        margin: 1 2;
    }

    .screen-subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 2 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.current_job: Job = Job(name="Default")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())

    def action_go_back(self) -> None:
        if len(self.screen_stack) > 2:
            self.pop_screen()
