"""Tests for live config reload on settings save."""

import pytest

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

pytestmark = pytest.mark.skipif(not HAS_TUI, reason="textual not installed")

if HAS_TUI:
    from cogokit.config import get_config
    from cogokit.config.loader import reset_config_cache
    from cogokit.core.units import LinearUnit
    from cogokit.tui.app import CogoKitApp


@pytest.mark.asyncio
async def test_apply_config_theme():
    """Theme change via apply_config updates app.theme."""
    reset_config_cache()
    app = CogoKitApp()
    async with app.run_test():
        cfg = get_config()
        cfg.set("display.theme", "light")
        messages = app.apply_config()
        assert any("Theme" in m for m in messages)
        assert app.theme == "textual-light"


@pytest.mark.asyncio
async def test_apply_config_units():
    """Unit change via apply_config updates Job units."""
    reset_config_cache()
    app = CogoKitApp()
    async with app.run_test():
        cfg = get_config()
        cfg.set("units.linear", "meter")
        messages = app.apply_config()
        assert any("Linear" in m for m in messages)
        assert app.current_job.linear_unit == LinearUnit.METER


@pytest.mark.asyncio
async def test_apply_config_no_change():
    """No changes produces no messages."""
    reset_config_cache()
    app = CogoKitApp()
    async with app.run_test():
        messages = app.apply_config()
        assert messages == []


@pytest.mark.asyncio
async def test_apply_config_keybinding_change_warns():
    """Keybinding changes produce a restart warning."""
    reset_config_cache()
    app = CogoKitApp()
    async with app.run_test():
        from cogokit.config.keybindings import DEFAULT_BINDINGS

        old = dict(DEFAULT_BINDINGS)
        # Simulate a change
        old["quit"] = "ctrl+q"  # different from actual default "q"
        messages = app.apply_config(old_keybindings=old)
        assert any("restart" in m.lower() for m in messages)
