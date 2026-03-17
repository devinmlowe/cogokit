"""Integration tests for context-sensitive footer."""

import pytest

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Input, Static

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

pytestmark = pytest.mark.skipif(not HAS_TUI, reason="textual not installed")

if HAS_TUI:
    from cogokit.config.loader import reset_config_cache
    from cogokit.tui.widgets.context_footer import ContextFooter

    class FooterTestApp(App):
        def compose(self) -> ComposeResult:
            yield Header()
            yield Input(id="test-input")
            yield Static("content")
            yield ContextFooter(id="footer")

    class ScreenHintApp(App):
        def compose(self) -> ComposeResult:
            yield Header()
            yield ContextFooter(id="footer")


@pytest.mark.asyncio
async def test_footer_mounts():
    reset_config_cache()
    app = FooterTestApp()
    async with app.run_test():
        footer = app.query_one("#footer", ContextFooter)
        assert footer is not None


@pytest.mark.asyncio
async def test_footer_set_hints():
    reset_config_cache()
    app = FooterTestApp()
    async with app.run_test():
        footer = app.query_one("#footer", ContextFooter)
        footer.set_hints("Custom | Hints")
        assert footer.hints == "Custom | Hints"


@pytest.mark.asyncio
async def test_footer_default_hints():
    reset_config_cache()
    app = FooterTestApp()
    async with app.run_test():
        footer = app.query_one("#footer", ContextFooter)
        assert "Quit" in footer.hints or "Back" in footer.hints
