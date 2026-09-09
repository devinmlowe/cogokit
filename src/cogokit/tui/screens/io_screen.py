"""I/O screens: Load Points, Save/Export."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static

from cogokit.tui.widgets.form_fields import SelectField, TextField
from cogokit.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Load Points
# ---------------------------------------------------------------------------
class LoadPointsScreen(Screen):
    """Load points from a file into the current job."""

    FOOTER_HINTS = "Enter Execute | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    LoadPointsScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Load Points File", classes="section-title"),
            Static(
                "Import points from ASCII, CSV, or LandXML files into the current job",
                classes="screen-subtitle",
            ),
            TextField("File Path:", "load-path", placeholder="/path/to/points.txt"),
            SelectField(
                "Format:", "load-format",
                options=[
                    ("Auto-detect (ASCII)", "ascii"),
                    ("LandXML", "landxml"),
                ],
            ),
            SelectField(
                "Action:", "load-action",
                options=[
                    ("Replace current job", "replace"),
                    ("Append to current job", "append"),
                ],
            ),
            Horizontal(
                Button("Load", variant="primary", id="btn-load"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Load Results", id="load-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            self.query_one("#load-path").value = ""
            self.query_one("#load-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-load":
            return

        try:
            path_field = self.query_one("#load-path").parent
            file_path = path_field.get_value()
            if not file_path:
                self.query_one("#error-msg", Static).update("File path required")
                return

            p = Path(file_path)
            if not p.exists():
                self.query_one("#error-msg", Static).update(f"File not found: {file_path}")
                return

            fmt_field = self.query_one("#load-format").parent
            fmt = fmt_field.get_value() or "ascii"

            action_field = self.query_one("#load-action").parent
            action = action_field.get_value() or "replace"

            if fmt == "landxml":
                from cogokit.io.landxml import import_landxml
                result = import_landxml(p)
                loaded_job = result.job
            else:
                from cogokit.io import read_points
                loaded_job = read_points(p)

            loaded_pts = loaded_job.points()

            if action == "replace":
                self.app.current_job = loaded_job
            else:
                for pt in loaded_pts:
                    self.app.current_job.add_point(pt)

            panel = self.query_one("#load-results", ResultPanel)
            lines = [f"Loaded {len(loaded_pts)} points from {p.name}\n"]
            for pt in loaded_pts[:20]:
                lines.append(
                    f"  {pt.number or '-'}: N={pt.northing:.4f}  E={pt.easting:.4f}  Z={pt.elevation:.4f}"
                )
            if len(loaded_pts) > 20:
                lines.append(f"  ... and {len(loaded_pts) - 20} more")
            panel.set_text("\n".join(lines))
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
class ExportScreen(Screen):
    """Export job points to various formats."""

    FOOTER_HINTS = "Enter Execute | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    ExportScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Export Points", classes="section-title"),
            Static(
                "Export current job points to ASCII, DXF, KML, or LandXML format",
                classes="screen-subtitle",
            ),
            TextField("Output Path:", "export-path", placeholder="/path/to/output.txt"),
            SelectField(
                "Format:", "export-format",
                options=[
                    ("ASCII (space-delimited)", "ascii"),
                    ("CSV (comma-delimited)", "csv"),
                    ("DXF", "dxf"),
                    ("KML", "kml"),
                ],
            ),
            Horizontal(
                Button("Export", variant="primary", id="btn-export"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Export Results", id="export-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            self.query_one("#export-path").value = ""
            self.query_one("#export-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-export":
            return

        try:
            path_field = self.query_one("#export-path").parent
            file_path = path_field.get_value()
            if not file_path:
                self.query_one("#error-msg", Static).update("Output path required")
                return

            fmt_field = self.query_one("#export-format").parent
            fmt = fmt_field.get_value() or "ascii"

            pts = self.app.current_job.points()
            if not pts:
                self.query_one("#error-msg", Static).update("No points in job to export")
                return

            out_path = Path(file_path)

            if fmt == "ascii":
                from cogokit.io import Delimiter, write_points
                write_points(self.app.current_job, out_path, delimiter=Delimiter.SPACE)
            elif fmt == "csv":
                from cogokit.io import Delimiter, write_points
                write_points(self.app.current_job, out_path, delimiter=Delimiter.COMMA)
            elif fmt == "dxf":
                from cogokit.io import export_dxf
                export_dxf(self.app.current_job, out_path)
            elif fmt == "kml":
                from cogokit.io import export_kml
                export_kml(self.app.current_job, out_path)

            panel = self.query_one("#export-results", ResultPanel)
            panel.set_results([
                ("Format:", fmt.upper()),
                ("Points:", str(len(pts))),
                ("Output:", str(out_path)),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")
