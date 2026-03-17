"""Point and Job management screen with 2D graph visualization."""

from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from cogopro.core import Point
from cogopro.tui.viewmodels.graph_vm import build_graph_vm
from cogopro.tui.widgets.graph_widget import GraphWidget


class LayoutMode(Enum):
    """Graph/table layout arrangements."""

    SIDE_BY_SIDE = "side-by-side"
    STACKED = "stacked"
    OVERLAY = "overlay"


_LAYOUT_CYCLE = [LayoutMode.SIDE_BY_SIDE, LayoutMode.STACKED, LayoutMode.OVERLAY]


class PointManagerScreen(Screen):
    """View, add, edit, and remove points in the current job."""

    BINDINGS = [
        Binding("ctrl+l", "cycle_layout", "Layout", show=False),
        Binding("ctrl+g", "toggle_graph", "Graph", show=False),
        Binding("ctrl+t", "cycle_labels", "Labels", show=False),
    ]

    FOOTER_HINTS = "^L Layout | ^G Graph | ^T Labels | ? Help"

    DEFAULT_CSS = """
    PointManagerScreen {
        layout: vertical;
    }

    #pm-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 2;
    }

    /* --- Layout modes --- */
    #pm-content.layout-side-by-side {
        layout: horizontal;
        height: 1fr;
    }

    #pm-content.layout-side-by-side #table-panel {
        width: 1fr;
    }

    #pm-content.layout-side-by-side #graph-panel {
        width: 1fr;
    }

    #pm-content.layout-stacked {
        layout: vertical;
        height: 1fr;
    }

    #pm-content.layout-stacked #table-panel {
        height: 1fr;
    }

    #pm-content.layout-stacked #graph-panel {
        height: 1fr;
    }

    #pm-content.layout-overlay {
        layout: vertical;
        height: 1fr;
    }

    #pm-content.layout-overlay #table-panel {
        display: none;
    }

    #pm-content.layout-overlay #graph-panel {
        width: 1fr;
        height: 1fr;
    }

    /* --- Table panel internals --- */
    #pm-job-row {
        height: 3;
        margin: 0 2;
    }

    #pm-job-row Label {
        width: 12;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }

    #pm-job-row Input {
        width: 1fr;
        height: 3;
    }

    #pm-job-row Button {
        width: 16;
        margin-left: 1;
    }

    #point-table {
        height: 1fr;
        margin: 1 2;
    }

    #add-point-section {
        height: auto;
        margin: 0 2 1 2;
        padding: 1 2;
        border: solid $accent;
    }

    #add-point-section .add-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .add-row {
        layout: horizontal;
        height: 3;
    }

    .add-row Label {
        width: 8;
        height: 3;
        content-align-vertical: middle;
        padding: 1 0 0 0;
    }

    .add-row Input {
        width: 1fr;
        height: 3;
        margin-right: 1;
    }

    #add-buttons {
        layout: horizontal;
        height: 3;
        margin-top: 1;
    }

    #add-buttons Button {
        margin-right: 1;
    }

    #pm-status {
        height: 1;
        margin: 0 2;
        color: $text-muted;
    }

    /* --- Graph panel --- */
    #graph-panel {
        border: solid $accent;
        margin: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._layout_mode = LayoutMode.SIDE_BY_SIDE
        self._selected_point_numbers: set[int] = set()
        self._graph_visible = True

    def compose(self) -> ComposeResult:
        yield Static("Point Manager", id="pm-title")

        with Container(id="pm-content", classes="layout-side-by-side"):
            with Vertical(id="table-panel"):
                with Horizontal(id="pm-job-row"):
                    yield Label("Job Name:")
                    yield Input(value=self.app.current_job.name, id="job-name-input")
                    yield Button("Rename", id="btn-rename-job")

                yield DataTable(id="point-table")

                with Vertical(id="add-point-section"):
                    yield Static("Add / Edit Point", classes="add-title")
                    with Horizontal(classes="add-row"):
                        yield Label("Number:")
                        yield Input(placeholder="Point #", id="add-number", type="integer")
                        yield Label("North:")
                        yield Input(placeholder="Northing", id="add-north", type="number")
                    with Horizontal(classes="add-row"):
                        yield Label("East:")
                        yield Input(placeholder="Easting", id="add-east", type="number")
                        yield Label("Elev:")
                        yield Input(placeholder="Elevation", id="add-elev", type="number")
                    with Horizontal(classes="add-row"):
                        yield Label("Desc:")
                        yield Input(placeholder="Description", id="add-desc")
                    with Horizontal(id="add-buttons"):
                        yield Button("Add Point", variant="primary", id="btn-add-point")
                        yield Button("Remove Selected", variant="error", id="btn-remove-point")
                        yield Button("Clear Fields", id="btn-clear-fields")

            yield GraphWidget(id="graph-panel")

        yield Static("", id="pm-status")

    def on_mount(self) -> None:
        table = self.query_one("#point-table", DataTable)
        table.add_columns("Pt#", "Northing", "Easting", "Elevation", "Description")
        table.cursor_type = "row"
        self._refresh_table()

    def on_screen_resume(self) -> None:
        """Re-sync when returning from another screen."""
        self._refresh_table()
        self._apply_display_config()

    def on_config_changed(self, event) -> None:
        """React to live config changes (theme, units, display)."""
        self._apply_display_config()

    def _apply_display_config(self) -> None:
        """Apply display config values to current screen state."""
        from cogopro.config import get_config

        cfg = get_config()

        # Apply graph visibility
        try:
            graph = self.query_one("#graph-panel", GraphWidget)
            if graph.display != cfg.display.show_graph:
                graph.display = cfg.display.show_graph
                self._graph_visible = cfg.display.show_graph
        except Exception:
            pass

        # Apply label mode
        try:
            graph = self.query_one("#graph-panel", GraphWidget)
            if graph.label_mode != cfg.display.label_mode:
                graph.label_mode = cfg.display.label_mode
        except Exception:
            pass

        # Apply layout mode
        target = cfg.display.default_layout
        for mode in _LAYOUT_CYCLE:
            if mode.value == target and mode != self._layout_mode:
                self._layout_mode = mode
                self._apply_layout()
                break

    # -- Table refresh + graph sync ------------------------------------

    def _refresh_table(self) -> None:
        table = self.query_one("#point-table", DataTable)
        table.clear()
        for pt in self.app.current_job.points():
            table.add_row(
                str(pt.number or ""),
                f"{pt.northing:.4f}",
                f"{pt.easting:.4f}",
                f"{pt.elevation:.4f}",
                pt.description or "",
                key=str(pt.number),
            )
        self._set_status(f"{len(self.app.current_job.points())} points in job")
        self._update_graph()

    def _update_graph(self) -> None:
        """Rebuild the graph view-model and push to the widget."""
        try:
            graph = self.query_one("#graph-panel", GraphWidget)
        except Exception:
            return
        vm = build_graph_vm(self.app.current_job, self._selected_point_numbers)
        graph.view_model = vm

    # -- Status --------------------------------------------------------

    def _set_status(self, msg: str) -> None:
        self.query_one("#pm-status", Static).update(msg)

    def _get_input(self, field_id: str) -> str:
        return self.query_one(f"#{field_id}", Input).value.strip()

    # -- Selection logic -----------------------------------------------

    def _select_point(self, point_number: int) -> None:
        """Select a point by number: update set, highlight table row, populate fields."""
        self._selected_point_numbers = {point_number}

        # Populate edit fields
        pt = self.app.current_job.get_point(point_number)
        if pt:
            self.query_one("#add-number", Input).value = str(pt.number or "")
            self.query_one("#add-north", Input).value = f"{pt.northing:.4f}"
            self.query_one("#add-east", Input).value = f"{pt.easting:.4f}"
            self.query_one("#add-elev", Input).value = f"{pt.elevation:.4f}"
            self.query_one("#add-desc", Input).value = pt.description or ""

        # Move table cursor to matching row
        table = self.query_one("#point-table", DataTable)
        for idx in range(table.row_count):
            row_key = table._row_order[idx]  # noqa: SLF001
            if str(row_key.value) == str(point_number):
                table.move_cursor(row=idx)
                break

        self._update_graph()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Populate fields when a row is selected for editing."""
        table = self.query_one("#point-table", DataTable)
        row = table.get_row(event.row_key)
        if row:
            pt_num_str = str(row[0])
            self.query_one("#add-number", Input).value = pt_num_str
            self.query_one("#add-north", Input).value = str(row[1])
            self.query_one("#add-east", Input).value = str(row[2])
            self.query_one("#add-elev", Input).value = str(row[3])
            self.query_one("#add-desc", Input).value = str(row[4])

            if pt_num_str:
                try:
                    self._selected_point_numbers = {int(pt_num_str)}
                except ValueError:
                    self._selected_point_numbers = set()
            else:
                self._selected_point_numbers = set()
            self._update_graph()

    def on_graph_widget_graph_point_clicked(
        self, event: GraphWidget.GraphPointClicked
    ) -> None:
        """Handle click on a point in the graph — select it."""
        self._select_point(event.point_number)

    # -- Button handlers -----------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        if bid == "btn-rename-job":
            name = self._get_input("job-name-input")
            if name:
                self.app.current_job.name = name
                self._set_status(f"Job renamed to '{name}'")

        elif bid == "btn-add-point":
            self._add_point()

        elif bid == "btn-remove-point":
            self._remove_selected()

        elif bid == "btn-clear-fields":
            for fid in ("add-number", "add-north", "add-east", "add-elev", "add-desc"):
                self.query_one(f"#{fid}", Input).value = ""
            self._selected_point_numbers = set()
            self._update_graph()

    def _add_point(self) -> None:
        try:
            num_str = self._get_input("add-number")
            number = int(num_str) if num_str else None
            northing = float(self._get_input("add-north"))
            easting = float(self._get_input("add-east"))
            elev_str = self._get_input("add-elev")
            elevation = float(elev_str) if elev_str else 0.0
            desc = self._get_input("add-desc") or None
        except ValueError:
            self._set_status("Error: invalid numeric input")
            return

        pt = Point(
            northing=northing,
            easting=easting,
            elevation=elevation,
            number=number,
            description=desc,
        )
        self.app.current_job.add_point(pt)
        if number is not None:
            self._selected_point_numbers = {number}
        self._refresh_table()
        self._set_status(f"Point {number} added")

    def _remove_selected(self) -> None:
        table = self.query_one("#point-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(
                table.cursor_coordinate
            )
            pt_num = int(str(row_key.value))
            try:
                self.app.current_job.remove_point(pt_num)
                self._selected_point_numbers.discard(pt_num)
                self._refresh_table()
                self._set_status(f"Point {pt_num} removed")
            except (ValueError, KeyError):
                self._set_status(f"Could not remove point {pt_num}")
        else:
            self._set_status("No point selected")

    # -- Layout actions ------------------------------------------------

    def action_cycle_layout(self) -> None:
        """Cycle through layout modes: side-by-side → stacked → overlay."""
        idx = _LAYOUT_CYCLE.index(self._layout_mode)
        self._layout_mode = _LAYOUT_CYCLE[(idx + 1) % len(_LAYOUT_CYCLE)]
        self._apply_layout()
        self._set_status(f"Layout: {self._layout_mode.value}")

    def action_toggle_graph(self) -> None:
        """Show or hide the graph panel."""
        self._graph_visible = not self._graph_visible
        try:
            graph = self.query_one("#graph-panel", GraphWidget)
            graph.display = self._graph_visible
        except Exception:
            pass
        self._set_status(f"Graph: {'visible' if self._graph_visible else 'hidden'}")

    def action_cycle_labels(self) -> None:
        """Cycle graph label mode: numbers → numbers+desc → none."""
        try:
            graph = self.query_one("#graph-panel", GraphWidget)
            graph.cycle_labels()
            modes = ["Point numbers", "Numbers + descriptions", "No labels"]
            self._set_status(f"Labels: {modes[graph.label_mode]}")
        except Exception:
            pass

    def _apply_layout(self) -> None:
        """Update CSS classes on the content container for the current layout."""
        container = self.query_one("#pm-content", Container)
        for mode in _LAYOUT_CYCLE:
            container.remove_class(f"layout-{mode.value}")
        container.add_class(f"layout-{self._layout_mode.value}")
