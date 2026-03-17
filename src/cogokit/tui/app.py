"""Main cogokit TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import DescendantBlur, DescendantFocus
from textual.message import Message
from textual.widgets import DataTable, Header, Input

from cogokit.config.loader import get_config, get_registry, reload_config
from cogokit.core.job import Job
from cogokit.core.units import AngularUnit, LinearUnit
from cogokit.tui.screens.main_menu import MainMenuScreen
from cogokit.tui.widgets.context_footer import (
    DEFAULT_HINTS,
    INPUT_HINTS,
    TABLE_HINTS,
    ContextFooter,
    FooterHintChanged,
)

# Map config string values to unit enums
_LINEAR_MAP = {u.value.lower(): u for u in LinearUnit}
_ANGULAR_MAP = {u.value.lower(): u for u in AngularUnit}


class ConfigChanged(Message):
    """Posted after config is saved and applied to notify screens."""

    def __init__(self, keybindings_changed: bool = False) -> None:
        super().__init__()
        self.keybindings_changed = keybindings_changed


class CogoKitApp(App):
    """cogokit — interactive terminal user interface."""

    TITLE = "cogokit"
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
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "go_back", "Back", show=False),
        Binding("question_mark", "show_help", "Help", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()

        # Apply config to Job defaults
        cfg = get_config()
        linear = _LINEAR_MAP.get(cfg.units.linear.lower(), LinearUnit.FOOT)
        angular = _ANGULAR_MAP.get(cfg.units.angular.lower(), AngularUnit.DMS)
        self.current_job: Job = Job(
            name="Default",
            linear_unit=linear,
            angular_unit=angular,
        )

        # Apply theme from config
        theme = cfg.display.theme
        if theme in ("dark", "light"):
            self.theme = f"textual-{theme}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield ContextFooter(id="context-footer")

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())

    def action_go_back(self) -> None:
        if len(self.screen_stack) > 2:
            self.pop_screen()

    def action_show_help(self) -> None:
        from cogokit.tui.screens.help_screen import HelpScreen

        self.push_screen(HelpScreen())

    # -- Live config reload --------------------------------------------

    def apply_config(self, old_keybindings: dict[str, str] | None = None) -> list[str]:
        """Apply current config to the running app. Returns status messages.

        Hot-reloads: theme, units, display settings.
        Cannot hot-reload: keybinding changes (requires restart).
        """
        cfg = get_config()
        messages: list[str] = []

        # Theme — fully live
        new_theme = cfg.display.theme
        theme_name = f"textual-{new_theme}" if new_theme in ("dark", "light") else None
        if theme_name and theme_name != self.theme:
            self.theme = theme_name
            messages.append(f"Theme changed to {new_theme}")

        # Units — update Job
        new_linear = _LINEAR_MAP.get(cfg.units.linear.lower(), LinearUnit.FOOT)
        new_angular = _ANGULAR_MAP.get(cfg.units.angular.lower(), AngularUnit.DMS)
        if self.current_job.linear_unit != new_linear:
            self.current_job.linear_unit = new_linear
            messages.append(f"Linear unit changed to {new_linear.value}")
        if self.current_job.angular_unit != new_angular:
            self.current_job.angular_unit = new_angular
            messages.append(f"Angular unit changed to {new_angular.value}")

        # Check keybinding changes
        keybindings_changed = False
        if old_keybindings is not None:
            registry = get_registry()
            new_bindings = registry.all_bindings()
            if old_keybindings != new_bindings:
                keybindings_changed = True
                messages.append(
                    "Keybinding changes require a restart to take effect"
                )

        # Broadcast to all screens
        self.post_message(ConfigChanged(keybindings_changed=keybindings_changed))

        return messages

    # -- Context-sensitive footer updates ------------------------------

    def _get_footer(self) -> ContextFooter | None:
        try:
            return self.query_one("#context-footer", ContextFooter)
        except Exception:
            return None

    def _get_screen_hints(self) -> str:
        """Get the FOOTER_HINTS from the current screen, or default."""
        screen = self.screen
        return getattr(screen, "FOOTER_HINTS", DEFAULT_HINTS)

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        footer = self._get_footer()
        if footer is None:
            return
        widget = event.widget
        if isinstance(widget, Input):
            footer.set_hints(INPUT_HINTS)
        elif isinstance(widget, DataTable):
            footer.set_hints(TABLE_HINTS)
        else:
            footer.set_hints(self._get_screen_hints())

    def on_descendant_blur(self, event: DescendantBlur) -> None:
        footer = self._get_footer()
        if footer is None:
            return
        footer.set_hints(self._get_screen_hints())

    def on_screen_resume(self) -> None:
        """Update footer when returning to a screen."""
        footer = self._get_footer()
        if footer is not None:
            footer.set_hints(self._get_screen_hints())

    def on_footer_hint_changed(self, event: FooterHintChanged) -> None:
        """Handle explicit hint updates from screens/widgets."""
        footer = self._get_footer()
        if footer is not None:
            footer.set_hints(event.hints)
