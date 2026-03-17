"""Geodetic screens: Vincenty Direct/Inverse, Coordinate Conversion, State Plane Zones."""

from __future__ import annotations

import math

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from cogopro.tui.widgets.form_fields import FloatField, SelectField, TextField
from cogopro.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Vincenty Direct
# ---------------------------------------------------------------------------
class VincentyDirectScreen(Screen):
    """Compute destination point on the ellipsoid given start, azimuth, and distance."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    VincentyDirectScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Vincenty Direct Solution", classes="section-title"),
            Static(
                "Given a starting point, azimuth, and distance on the ellipsoid",
                classes="screen-subtitle",
            ),
            SelectField(
                "Ellipsoid:", "vd-ellipsoid",
                options=[
                    ("WGS84", "wgs84"),
                    ("GRS80 / NAD83", "grs80"),
                    ("Clarke 1866", "clarke1866"),
                ],
            ),
            FloatField("Latitude (deg):", "vd-lat", placeholder="e.g. 40.0"),
            FloatField("Longitude (deg):", "vd-lon", placeholder="e.g. -75.0"),
            FloatField("Azimuth (deg):", "vd-az", placeholder="e.g. 45.0"),
            FloatField("Distance (m):", "vd-dist", placeholder="e.g. 10000.0"),
            Horizontal(
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Direct Solution", id="vd-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float | None:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def _get_ellipsoid(self):
        from cogopro.geodetic.ellipsoid import CLARKE_1866, GRS80, WGS84
        sel = self.query_one("#vd-ellipsoid").parent
        name = sel.get_value() or "wgs84"
        return {"wgs84": WGS84, "grs80": GRS80, "clarke1866": CLARKE_1866}[name]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("vd-lat", "vd-lon", "vd-az", "vd-dist"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#vd-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogopro.geodetic.vincenty import vincenty_direct

            lat = self._field("vd-lat")
            lon = self._field("vd-lon")
            az = self._field("vd-az")
            dist = self._field("vd-dist")

            if any(v is None for v in (lat, lon, az, dist)):
                self.query_one("#error-msg", Static).update("All fields required")
                return

            ellipsoid = self._get_ellipsoid()
            result = vincenty_direct(
                math.radians(lat), math.radians(lon),
                math.radians(az), dist,
                ellipsoid,
            )

            panel = self.query_one("#vd-results", ResultPanel)
            panel.set_results([
                ("Dest. Latitude:", f"{math.degrees(result.lat2):.8f} deg"),
                ("Dest. Longitude:", f"{math.degrees(result.lon2):.8f} deg"),
                ("Reverse Azimuth:", f"{math.degrees(result.az2):.6f} deg"),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Vincenty Inverse
# ---------------------------------------------------------------------------
class VincentyInverseScreen(Screen):
    """Compute geodesic distance and azimuths between two points on the ellipsoid."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    VincentyInverseScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Vincenty Inverse Solution", classes="section-title"),
            Static(
                "Geodesic distance and azimuths between two points on the ellipsoid",
                classes="screen-subtitle",
            ),
            SelectField(
                "Ellipsoid:", "vi-ellipsoid",
                options=[
                    ("WGS84", "wgs84"),
                    ("GRS80 / NAD83", "grs80"),
                    ("Clarke 1866", "clarke1866"),
                ],
            ),
            FloatField("Latitude 1 (deg):", "vi-lat1", placeholder="e.g. 40.0"),
            FloatField("Longitude 1 (deg):", "vi-lon1", placeholder="e.g. -75.0"),
            FloatField("Latitude 2 (deg):", "vi-lat2", placeholder="e.g. 41.0"),
            FloatField("Longitude 2 (deg):", "vi-lon2", placeholder="e.g. -74.0"),
            Horizontal(
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Inverse Solution", id="vi-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float | None:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def _get_ellipsoid(self):
        from cogopro.geodetic.ellipsoid import CLARKE_1866, GRS80, WGS84
        sel = self.query_one("#vi-ellipsoid").parent
        name = sel.get_value() or "wgs84"
        return {"wgs84": WGS84, "grs80": GRS80, "clarke1866": CLARKE_1866}[name]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("vi-lat1", "vi-lon1", "vi-lat2", "vi-lon2"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#vi-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogopro.geodetic.vincenty import vincenty_inverse

            lat1 = self._field("vi-lat1")
            lon1 = self._field("vi-lon1")
            lat2 = self._field("vi-lat2")
            lon2 = self._field("vi-lon2")

            if any(v is None for v in (lat1, lon1, lat2, lon2)):
                self.query_one("#error-msg", Static).update("All fields required")
                return

            ellipsoid = self._get_ellipsoid()
            result = vincenty_inverse(
                math.radians(lat1), math.radians(lon1),
                math.radians(lat2), math.radians(lon2),
                ellipsoid,
            )

            panel = self.query_one("#vi-results", ResultPanel)
            panel.set_results([
                ("Distance:", f"{result.distance:.4f} m"),
                ("Forward Azimuth:", f"{math.degrees(result.az1):.6f} deg"),
                ("Reverse Azimuth:", f"{math.degrees(result.az2):.6f} deg"),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Coordinate Conversion
# ---------------------------------------------------------------------------
class ConvertScreen(Screen):
    """Transform coordinates between CRS types."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    ConvertScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Coordinate Conversion", classes="section-title"),
            Static(
                "Transform points between coordinate reference systems",
                classes="screen-subtitle",
            ),
            TextField("Source CRS:", "cv-from", placeholder="e.g. utm:17:N or geodetic:wgs84"),
            TextField("Target CRS:", "cv-to", placeholder="e.g. epsg:26917 or sp:CA:5"),
            FloatField("Northing / Lat:", "cv-n", placeholder="Northing or Latitude (deg)"),
            FloatField("Easting / Lon:", "cv-e", placeholder="Easting or Longitude (deg)"),
            FloatField("Elevation:", "cv-z", placeholder="0.0"),
            Horizontal(
                Button("Convert", variant="primary", id="btn-compute"),
                Button("Convert Job", id="btn-convert-job"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Conversion Results", id="cv-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field_float(self, fid: str) -> float:
        f = self.query_one(f"#{fid}").parent
        val = f.get_value()
        return val if val is not None else 0.0

    def _field_text(self, fid: str) -> str:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("cv-n", "cv-e", "cv-z"):
                self.query_one(f"#{fid}").value = ""
            for fid in ("cv-from", "cv-to"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#cv-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id == "btn-convert-job":
            self._convert_job()
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogopro.cli import _parse_crs
            from cogopro.core import Point
            from cogopro.core.crs import transform_point

            from_str = self._field_text("cv-from")
            to_str = self._field_text("cv-to")
            if not from_str or not to_str:
                self.query_one("#error-msg", Static).update("Both CRS fields required")
                return

            src = _parse_crs(from_str)
            dst = _parse_crs(to_str)
            if src is None or dst is None:
                self.query_one("#error-msg", Static).update("Invalid CRS string")
                return

            pt = Point(
                northing=self._field_float("cv-n"),
                easting=self._field_float("cv-e"),
                elevation=self._field_float("cv-z"),
            )
            result = transform_point(pt, dst, from_crs=src)

            panel = self.query_one("#cv-results", ResultPanel)
            panel.set_results([
                ("From:", from_str),
                ("To:", to_str),
                ("Northing / Lat:", f"{result.northing:.8f}"),
                ("Easting / Lon:", f"{result.easting:.8f}"),
                ("Elevation:", f"{result.elevation:.4f}"),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _convert_job(self) -> None:
        try:
            from cogopro.cli import _parse_crs
            from cogopro.core.crs import transform_job

            from_str = self._field_text("cv-from")
            to_str = self._field_text("cv-to")
            if not from_str or not to_str:
                self.query_one("#error-msg", Static).update("Both CRS fields required")
                return

            src = _parse_crs(from_str)
            dst = _parse_crs(to_str)
            if src is None or dst is None:
                self.query_one("#error-msg", Static).update("Invalid CRS string")
                return

            job = self.app.current_job
            if not job.points():
                self.query_one("#error-msg", Static).update("No points in job")
                return

            transformed = transform_job(job, dst, from_crs=src)
            # Replace current job with transformed
            self.app.current_job = transformed

            panel = self.query_one("#cv-results", ResultPanel)
            lines = [f"Converted {len(transformed.points())} points from {from_str} to {to_str}"]
            for p in transformed.points():
                lines.append(
                    f"  {p.number}: N={p.northing:.4f}  E={p.easting:.4f}  Z={p.elevation:.4f}"
                )
            panel.set_text("\n".join(lines))
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# State Plane Zones
# ---------------------------------------------------------------------------
class ZonesScreen(Screen):
    """Browse and search State Plane coordinate system zones."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    ZonesScreen { layout: vertical; }

    #zones-table {
        height: 1fr;
        margin: 1 2;
    }

    #zone-filter-row {
        layout: horizontal;
        height: 3;
        margin: 0 2;
    }

    #zone-filter-row Label {
        width: 16;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }

    #zone-filter-row Input {
        width: 20;
        height: 3;
        margin-right: 1;
    }

    #zone-filter-row Button {
        width: 12;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("State Plane Coordinate Zones", classes="section-title")
        with Horizontal(id="zone-filter-row"):
            yield Label("Filter by State:")
            yield Input(placeholder="e.g. TX, CA", id="zone-state-filter")
            yield Button("Search", variant="primary", id="btn-search")
            yield Button("Show All", id="btn-all")
        yield DataTable(id="zones-table")
        yield ResultPanel("Zone Details", id="zone-details")
        yield Static("", id="error-msg", classes="error-text")

    def on_mount(self) -> None:
        table = self.query_one("#zones-table", DataTable)
        table.add_columns("EPSG", "State", "Zone", "Projection")
        table.cursor_type = "row"
        self._load_zones()

    def _load_zones(self, state: str | None = None) -> None:
        from cogopro.geodetic.state_plane import list_zones

        table = self.query_one("#zones-table", DataTable)
        table.clear()

        zones = list_zones(state=state)
        for z in zones:
            table.add_row(
                str(z.epsg),
                z.state,
                z.zone,
                z.proj_def.proj_type,
                key=str(z.epsg),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-search":
            state = self.query_one("#zone-state-filter", Input).value.strip().upper()
            self._load_zones(state if state else None)
        elif event.button.id == "btn-all":
            self.query_one("#zone-state-filter", Input).value = ""
            self._load_zones()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            from cogopro.geodetic.state_plane import get_zone

            epsg = int(str(event.row_key.value))
            zone = get_zone(epsg)
            panel = self.query_one("#zone-details", ResultPanel)
            panel.set_results([
                ("EPSG:", str(zone.epsg)),
                ("Name:", zone.name),
                ("State:", zone.state),
                ("Zone:", zone.zone),
                ("Projection:", zone.proj_def.proj_type),
                ("Units:", zone.proj_def.units),
            ])
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")
