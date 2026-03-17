"""Tests verifying the keybinding conflict fix (l/g/t → ctrl+l/ctrl+g/ctrl+t)."""

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
    from cogopro.tui.screens.point_manager import PointManagerScreen
    from cogopro.tui.widgets.context_footer import ContextFooter

    class PMTestApp(App):
        def __init__(self) -> None:
            super().__init__()
            self.current_job = Job(name="Test")

        def compose(self) -> ComposeResult:
            yield Header()
            yield ContextFooter(id="context-footer")

        def on_mount(self) -> None:
            self.push_screen(PointManagerScreen())


@pytest.mark.asyncio
async def test_ctrl_l_cycles_layout():
    """ctrl+l should cycle layout mode."""
    reset_config_cache()
    app = PMTestApp()
    async with app.run_test():
        screen = app.screen
        assert screen._layout_mode.value == "side-by-side"

        # Call action directly (ctrl+key testing requires special handling)
        screen.action_cycle_layout()
        assert screen._layout_mode.value == "stacked"


@pytest.mark.asyncio
async def test_bindings_use_ctrl_modifiers():
    """Verify BINDINGS use ctrl+ modifiers, not bare keys."""
    reset_config_cache()
    app = PMTestApp()
    async with app.run_test():
        screen = app.screen
        binding_keys = [b.key for b in screen.BINDINGS]
        # Must use ctrl+ modifiers
        assert "ctrl+l" in binding_keys
        assert "ctrl+g" in binding_keys
        assert "ctrl+t" in binding_keys
        # Must NOT have bare keys
        assert "l" not in binding_keys
        assert "g" not in binding_keys
        assert "t" not in binding_keys
