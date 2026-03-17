"""Integration tests for the Settings screen."""

import pytest

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Footer, Header

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

pytestmark = pytest.mark.skipif(not HAS_TUI, reason="textual not installed")

if HAS_TUI:
    from cogopro.config.loader import reset_config_cache
    from cogopro.core.job import Job
    from cogopro.tui.screens.settings import SettingsScreen
    from cogopro.tui.widgets.context_footer import ContextFooter

    class SettingsTestApp(App):
        def __init__(self) -> None:
            super().__init__()
            self.current_job = Job(name="Test")

        def compose(self) -> ComposeResult:
            yield Header()
            yield ContextFooter(id="context-footer")

        def on_mount(self) -> None:
            self.push_screen(SettingsScreen())


@pytest.mark.asyncio
async def test_settings_mounts():
    reset_config_cache()
    app = SettingsTestApp()
    async with app.run_test():
        # Verify the screen mounted without error
        screen = app.screen
        assert isinstance(screen, SettingsScreen)


@pytest.mark.asyncio
async def test_settings_has_keybinding_table():
    reset_config_cache()
    app = SettingsTestApp()
    async with app.run_test():
        from textual.widgets import DataTable

        table = app.screen.query_one("#keybinding-table", DataTable)
        assert table is not None
        assert table.row_count > 0
