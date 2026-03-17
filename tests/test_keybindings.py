"""Tests for keybinding registry."""

from cogopro.config.keybindings import (
    DEFAULT_BINDINGS,
    KeybindingRegistry,
    _format_key_display,
)


class TestKeybindingRegistry:
    """Test keybinding resolution and overrides."""

    def test_defaults(self):
        reg = KeybindingRegistry()
        assert reg.get_key("quit") == "q"
        assert reg.get_key("cycle_layout") == "ctrl+l"

    def test_user_override(self):
        reg = KeybindingRegistry(user_overrides={"quit": "ctrl+q"})
        assert reg.get_key("quit") == "ctrl+q"
        # Non-overridden keys keep defaults
        assert reg.get_key("go_back") == "escape"

    def test_get_action_reverse(self):
        reg = KeybindingRegistry()
        assert reg.get_action("q") == "quit"
        assert reg.get_action("ctrl+l") == "cycle_layout"
        assert reg.get_action("nonexistent") is None

    def test_all_bindings(self):
        reg = KeybindingRegistry()
        bindings = reg.all_bindings()
        assert bindings == DEFAULT_BINDINGS
        # Returned dict is a copy
        bindings["new"] = "x"
        assert "new" not in reg.all_bindings()

    def test_unknown_action_raises(self):
        reg = KeybindingRegistry()
        import pytest

        with pytest.raises(KeyError):
            reg.get_key("nonexistent_action")

    def test_to_textual_bindings(self):
        reg = KeybindingRegistry()
        actions = {"cycle_layout": "Layout", "toggle_graph": "Graph"}
        bindings = reg.to_textual_bindings(actions)
        assert len(bindings) == 2
        keys = {b.key for b in bindings}
        assert "ctrl+l" in keys
        assert "ctrl+g" in keys

    def test_custom_defaults(self):
        reg = KeybindingRegistry(defaults={"my_action": "ctrl+x"})
        assert reg.get_key("my_action") == "ctrl+x"


class TestFormatKeyDisplay:
    """Test key display formatting."""

    def test_ctrl_modifier(self):
        assert _format_key_display("ctrl+l") == "^L"
        assert _format_key_display("ctrl+g") == "^G"

    def test_alt_modifier(self):
        assert _format_key_display("alt+x") == "A-X"

    def test_special_keys(self):
        assert _format_key_display("escape") == "Esc"
        assert _format_key_display("question_mark") == "?"
        assert _format_key_display("enter") == "Enter"
        assert _format_key_display("tab") == "Tab"
        assert _format_key_display("delete") == "Del"

    def test_plain_key(self):
        assert _format_key_display("q") == "q"
        assert _format_key_display("a") == "a"

    def test_format_key_via_registry(self):
        reg = KeybindingRegistry()
        assert reg.format_key("quit") == "q"
        assert reg.format_key("cycle_layout") == "^L"
        assert reg.format_key("show_help") == "?"
