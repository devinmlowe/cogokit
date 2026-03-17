"""Context-sensitive footer widget showing keybinding hints."""

from __future__ import annotations

from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class FooterHintChanged(Message):
    """Posted by screens/widgets to update footer hints."""

    def __init__(self, hints: str) -> None:
        super().__init__()
        self.hints = hints


class ContextFooter(Static):
    """A context-aware footer bar displaying keyboard shortcut hints.

    Replaces Textual's built-in Footer with a widget that changes its
    content based on the current screen, focused widget, and selection state.

    Communication:
        - Screens set FOOTER_HINTS class attribute for default hints
        - FooterHintChanged messages override with contextual hints
        - Focus changes (Input/DataTable) auto-update via the app
    """

    DEFAULT_CSS = """
    ContextFooter {
        dock: bottom;
        height: 1;
        background: $primary-background;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    """

    hints: reactive[str] = reactive("q Quit | Esc Back")

    def render(self) -> str:
        return self.hints

    def watch_hints(self, _old: str, _new: str) -> None:
        self.refresh()

    def set_hints(self, hints: str) -> None:
        """Update the displayed hints."""
        self.hints = hints


# Standard hint strings for common contexts
INPUT_HINTS = "Enter Confirm | Tab Next | Esc Back | q Quit"
TABLE_HINTS = "Enter Select | Arrows Navigate | Esc Back | q Quit"
DEFAULT_HINTS = "Esc Back | q Quit | ? Help"
