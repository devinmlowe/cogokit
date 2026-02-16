"""Point and Job management screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from cogopro.core import Point


class PointManagerScreen(Screen):
    """View, add, edit, and remove points in the current job."""

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
    """

    def compose(self) -> ComposeResult:
        yield Static("Point Manager", id="pm-title")

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

        yield Static("", id="pm-status")

    def on_mount(self) -> None:
        table = self.query_one("#point-table", DataTable)
        table.add_columns("Pt#", "Northing", "Easting", "Elevation", "Description")
        table.cursor_type = "row"
        self._refresh_table()

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

    def _set_status(self, msg: str) -> None:
        self.query_one("#pm-status", Static).update(msg)

    def _get_input(self, field_id: str) -> str:
        return self.query_one(f"#{field_id}", Input).value.strip()

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
                self._refresh_table()
                self._set_status(f"Point {pt_num} removed")
            except (ValueError, KeyError):
                self._set_status(f"Could not remove point {pt_num}")
        else:
            self._set_status("No point selected")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Populate fields when a row is selected for editing."""
        table = self.query_one("#point-table", DataTable)
        row = table.get_row(event.row_key)
        if row:
            self.query_one("#add-number", Input).value = str(row[0])
            self.query_one("#add-north", Input).value = str(row[1])
            self.query_one("#add-east", Input).value = str(row[2])
            self.query_one("#add-elev", Input).value = str(row[3])
            self.query_one("#add-desc", Input).value = str(row[4])
