"""Settings screen for editing application configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Label, Select, Static

from cogopro.config import get_config, get_registry, reload_config, save_config
from cogopro.config.keybindings import ACTION_DESCRIPTIONS, _format_key_display
from cogopro.core.units import AngularUnit, LinearUnit


class KeyCaptureModal(ModalScreen[str | None]):
    """Modal that captures a key press for keybinding assignment."""

    DEFAULT_CSS = """
    KeyCaptureModal {
        align: center middle;
    }

    #capture-container {
        width: 40;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 2;
    }

    #capture-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #capture-action {
        text-align: center;
        color: $accent;
        margin-bottom: 1;
    }

    #capture-current {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #capture-waiting {
        text-align: center;
        text-style: italic;
        color: $text;
        margin-bottom: 1;
    }

    #capture-cancel {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, action_name: str, current_key: str) -> None:
        super().__init__()
        self.action_name = action_name
        self.current_key = current_key

    def compose(self) -> ComposeResult:
        with Vertical(id="capture-container"):
            yield Static("Press new key combo", id="capture-title")
            yield Static(f"Action: {self.action_name}", id="capture-action")
            yield Static(
                f"Current: {_format_key_display(self.current_key)}",
                id="capture-current",
            )
            yield Static("Waiting for input...", id="capture-waiting")
            yield Button("Cancel", id="capture-cancel", variant="error")

    def on_key(self, event: Key) -> None:
        key = event.key
        # Ignore modifier-only presses and escape (handled by binding)
        if key in ("escape", "shift", "ctrl", "alt", "meta"):
            return
        event.prevent_default()
        event.stop()
        self.dismiss(key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "capture-cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SettingsScreen(Screen):
    """Application settings: units, display, paths, keybindings."""

    FOOTER_HINTS = "Enter Edit | Esc Back | ? Help"

    DEFAULT_CSS = """
    SettingsScreen {
        layout: vertical;
    }

    #settings-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 2;
    }

    .settings-section {
        margin: 0 2 1 2;
        padding: 1 2;
        border: solid $accent;
        height: auto;
    }

    .settings-section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .settings-row {
        layout: horizontal;
        height: 3;
    }

    .settings-row Label {
        width: 20;
        height: 3;
        content-align-vertical: middle;
        padding: 1 0 0 0;
    }

    .settings-row Select {
        width: 1fr;
        height: 3;
    }

    #keybinding-table {
        height: auto;
        max-height: 12;
        margin-top: 1;
    }

    #save-bar {
        layout: horizontal;
        height: 3;
        margin: 1 2;
        align: center middle;
    }

    #save-bar Button {
        margin: 0 1;
    }

    #settings-status {
        height: 1;
        margin: 0 2;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        cfg = get_config()

        yield Static("Settings", id="settings-title")

        with VerticalScroll():
            # Units section
            with Vertical(classes="settings-section"):
                yield Static("Units", classes="settings-section-title")
                with Horizontal(classes="settings-row"):
                    yield Label("Linear Unit:")
                    yield Select(
                        [(u.value, u.value) for u in LinearUnit],
                        value=cfg.units.linear,
                        id="sel-linear-unit",
                    )
                with Horizontal(classes="settings-row"):
                    yield Label("Angular Unit:")
                    yield Select(
                        [(u.value, u.value) for u in AngularUnit],
                        value=cfg.units.angular,
                        id="sel-angular-unit",
                    )

            # Display section
            with Vertical(classes="settings-section"):
                yield Static("Display", classes="settings-section-title")
                with Horizontal(classes="settings-row"):
                    yield Label("Default Layout:")
                    yield Select(
                        [
                            ("Side-by-Side", "side-by-side"),
                            ("Stacked", "stacked"),
                            ("Overlay", "overlay"),
                        ],
                        value=cfg.display.default_layout,
                        id="sel-layout",
                    )
                with Horizontal(classes="settings-row"):
                    yield Label("Show Graph:")
                    yield Select(
                        [("Yes", "true"), ("No", "false")],
                        value="true" if cfg.display.show_graph else "false",
                        id="sel-show-graph",
                    )
                with Horizontal(classes="settings-row"):
                    yield Label("Label Mode:")
                    yield Select(
                        [
                            ("Point Numbers", "0"),
                            ("Numbers + Descriptions", "1"),
                            ("No Labels", "2"),
                        ],
                        value=str(cfg.display.label_mode),
                        id="sel-label-mode",
                    )
                with Horizontal(classes="settings-row"):
                    yield Label("Theme:")
                    yield Select(
                        [("Dark", "dark"), ("Light", "light")],
                        value=cfg.display.theme,
                        id="sel-theme",
                    )

            # Keybindings section
            with Vertical(classes="settings-section"):
                yield Static("Keybindings (click to edit)", classes="settings-section-title")
                yield DataTable(id="keybinding-table")

        with Horizontal(id="save-bar"):
            yield Button("Save (Project)", variant="primary", id="btn-save-project")
            yield Button("Save (Global)", variant="default", id="btn-save-global")

        yield Static("", id="settings-status")

    def on_mount(self) -> None:
        self._refresh_keybinding_table()

    def _refresh_keybinding_table(self) -> None:
        table = self.query_one("#keybinding-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Action", "Key", "Category")
        table.cursor_type = "row"

        registry = get_registry()
        bindings = registry.all_bindings()

        for action in sorted(bindings):
            key = bindings[action]
            desc, category = ACTION_DESCRIPTIONS.get(action, (action, "Other"))
            display_key = _format_key_display(key)
            table.add_row(desc, display_key, category, key=action)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open key capture modal for the selected keybinding."""
        action = str(event.row_key.value)
        registry = get_registry()
        current_key = registry.get_key(action)

        def on_capture(result: str | None) -> None:
            if result is not None:
                cfg = get_config()
                cfg.keybindings[action] = result
                self._refresh_keybinding_table()
                self._set_status(f"Changed {action} to {_format_key_display(result)}")

        self.app.push_screen(KeyCaptureModal(action, current_key), on_capture)

    def _collect_settings(self) -> None:
        """Read all widget values back into the config."""
        cfg = get_config()

        # Units
        linear = self.query_one("#sel-linear-unit", Select).value
        if linear is not None and linear != Select.BLANK:
            cfg.set("units.linear", str(linear))
        angular = self.query_one("#sel-angular-unit", Select).value
        if angular is not None and angular != Select.BLANK:
            cfg.set("units.angular", str(angular))

        # Display
        layout = self.query_one("#sel-layout", Select).value
        if layout is not None and layout != Select.BLANK:
            cfg.set("display.default_layout", str(layout))
        show_graph = self.query_one("#sel-show-graph", Select).value
        if show_graph is not None and show_graph != Select.BLANK:
            cfg.set("display.show_graph", str(show_graph))
        label_mode = self.query_one("#sel-label-mode", Select).value
        if label_mode is not None and label_mode != Select.BLANK:
            cfg.set("display.label_mode", str(label_mode))
        theme = self.query_one("#sel-theme", Select).value
        if theme is not None and theme != Select.BLANK:
            cfg.set("display.theme", str(theme))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid in ("btn-save-project", "btn-save-global"):
            # Snapshot current keybindings before save to detect changes
            old_bindings = get_registry().all_bindings()

            self._collect_settings()
            cfg = get_config()
            global_ = bid == "btn-save-global"
            path = save_config(cfg, global_=global_)

            # Reload config from disk to sync the registry
            reload_config()

            # Apply live changes (theme, units, display)
            status_parts = [f"Saved to {path}"]
            apply_messages = self.app.apply_config(old_keybindings=old_bindings)
            if apply_messages:
                status_parts.extend(apply_messages)
            self._set_status(" | ".join(status_parts))

    def _set_status(self, msg: str) -> None:
        self.query_one("#settings-status", Static).update(msg)
