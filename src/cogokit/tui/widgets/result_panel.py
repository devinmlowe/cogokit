"""Result display panel widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class ResultPanel(Vertical):
    """Displays computation results in a styled panel."""

    DEFAULT_CSS = """
    ResultPanel {
        margin: 1 2;
        padding: 1 2;
        border: solid $accent;
        height: auto;
        max-height: 24;
        overflow-y: auto;
    }
    """

    def __init__(self, title: str = "Results", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._lines: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="result-title")
        yield Static("", id="result-content")

    def set_results(self, rows: list[tuple[str, str]]) -> None:
        """Set result rows as (label, value) pairs."""
        self._lines = rows
        content = self.query_one("#result-content", Static)
        text = "\n".join(f"  {label:<20} {value}" for label, value in rows)
        content.update(text)

    def set_text(self, text: str) -> None:
        """Set raw text content."""
        content = self.query_one("#result-content", Static)
        content.update(text)

    def clear(self) -> None:
        """Clear all results."""
        self._lines = []
        content = self.query_one("#result-content", Static)
        content.update("")
