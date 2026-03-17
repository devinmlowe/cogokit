"""Keybinding registry with defaults and user overrides."""

from __future__ import annotations

from dataclasses import dataclass


# Action descriptions for help display, grouped by category
ACTION_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    # (description, category)
    "quit": ("Quit application", "App"),
    "go_back": ("Go back / close", "App"),
    "show_help": ("Show keybinding help", "App"),
    "cycle_layout": ("Cycle graph layout", "Point Manager"),
    "toggle_graph": ("Toggle graph visibility", "Point Manager"),
    "cycle_labels": ("Cycle point labels", "Point Manager"),
}

DEFAULT_BINDINGS: dict[str, str] = {
    # App-level
    "quit": "q",
    "go_back": "escape",
    "show_help": "question_mark",
    # Point Manager
    "cycle_layout": "ctrl+l",
    "toggle_graph": "ctrl+g",
    "cycle_labels": "ctrl+t",
}


@dataclass
class KeybindingRegistry:
    """Resolves action names to key sequences with user override support."""

    _bindings: dict[str, str]

    def __init__(
        self,
        defaults: dict[str, str] | None = None,
        user_overrides: dict[str, str] | None = None,
    ) -> None:
        self._bindings = dict(defaults or DEFAULT_BINDINGS)
        if user_overrides:
            self._bindings.update(user_overrides)

    def get_key(self, action: str) -> str:
        """Get the key sequence for an action name."""
        if action not in self._bindings:
            raise KeyError(f"Unknown action: {action}")
        return self._bindings[action]

    def get_action(self, key: str) -> str | None:
        """Reverse lookup: key sequence → action name, or None."""
        for action, bound_key in self._bindings.items():
            if bound_key == key:
                return action
        return None

    def all_bindings(self) -> dict[str, str]:
        """Return a copy of all action → key mappings."""
        return dict(self._bindings)

    def format_key(self, action: str) -> str:
        """Format a key sequence for display (e.g., 'ctrl+l' → '^L')."""
        key = self.get_key(action)
        return _format_key_display(key)

    def to_textual_bindings(
        self, actions: dict[str, str], show: bool = False
    ) -> list:
        """Generate Textual Binding objects for a set of actions.

        Args:
            actions: Mapping of action_name → description.
            show: Whether to show bindings in Textual's built-in footer.
        """
        from textual.binding import Binding

        bindings = []
        for action, description in actions.items():
            key = self._bindings.get(action)
            if key:
                bindings.append(Binding(key, action, description, show=show))
        return bindings


def _format_key_display(key: str) -> str:
    """Format a key string for compact footer display.

    Examples:
        'ctrl+l' → '^L'
        'escape' → 'Esc'
        'question_mark' → '?'
        'q' → 'q'
    """
    if key.startswith("ctrl+"):
        letter = key[5:].upper()
        return f"^{letter}"
    if key.startswith("alt+"):
        letter = key[4:].upper()
        return f"A-{letter}"
    display_map = {
        "escape": "Esc",
        "question_mark": "?",
        "enter": "Enter",
        "tab": "Tab",
        "delete": "Del",
        "backspace": "Bksp",
        "space": "Space",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
    }
    return display_map.get(key, key)
