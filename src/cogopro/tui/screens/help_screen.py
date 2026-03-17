"""Keybinding help overlay modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from cogopro.config.keybindings import ACTION_DESCRIPTIONS, _format_key_display
from cogopro.config.loader import get_registry


class HelpScreen(ModalScreen):
    """Modal overlay showing all available keybindings."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 60;
        height: auto;
        max-height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #help-table {
        height: auto;
        max-height: 20;
    }

    #help-footer {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Static("Keyboard Shortcuts", id="help-title")
            yield DataTable(id="help-table")
            yield Static("Press Esc or ? to close", id="help-footer")

    def on_mount(self) -> None:
        table = self.query_one("#help-table", DataTable)
        table.add_columns("Key", "Action", "Category")
        table.cursor_type = "none"
        table.show_header = True

        registry = get_registry()
        bindings = registry.all_bindings()

        # Sort by category then action name
        rows = []
        for action, key in sorted(bindings.items()):
            desc, category = ACTION_DESCRIPTIONS.get(action, (action, "Other"))
            display_key = _format_key_display(key)
            rows.append((category, display_key, desc))

        rows.sort(key=lambda r: (r[0], r[2]))
        for category, display_key, desc in rows:
            table.add_row(display_key, desc, category)

    def action_dismiss(self) -> None:
        self.app.pop_screen()
