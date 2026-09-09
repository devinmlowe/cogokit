"""Coordinate Geometry screens: Inverse, Traverse, Intersections, Area."""

from __future__ import annotations

import math

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static

from cogokit.tui.widgets.form_fields import FloatField, SelectField
from cogokit.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Inverse
# ---------------------------------------------------------------------------
class InverseScreen(Screen):
    """Compute azimuth, distance, and grade between two points."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    InverseScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Inverse Calculation", classes="section-title"),
            Static(
                "Compute bearing, distance, and grade between two points",
                classes="screen-subtitle",
            ),
            FloatField("Northing 1:", "inv-n1", placeholder="e.g. 1000.0"),
            FloatField("Easting 1:", "inv-e1", placeholder="e.g. 2000.0"),
            FloatField("Elevation 1:", "inv-z1", placeholder="0.0"),
            FloatField("Northing 2:", "inv-n2", placeholder="e.g. 1500.0"),
            FloatField("Easting 2:", "inv-e2", placeholder="e.g. 2500.0"),
            FloatField("Elevation 2:", "inv-z2", placeholder="0.0"),
            Horizontal(
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Store Result", id="btn-store"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Inverse Results", id="inverse-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float:
        f = self.query_one(f"#{fid}").parent
        val = f.get_value()
        return val if val is not None else 0.0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("inv-n1", "inv-e1", "inv-z1", "inv-n2", "inv-e2", "inv-z2"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#inverse-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id == "btn-store":
            self._store_result()
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.cogo.inverse import inverse
            from cogokit.core import Angle, Point

            p1 = Point(
                northing=self._field("inv-n1"),
                easting=self._field("inv-e1"),
                elevation=self._field("inv-z1"),
            )
            p2 = Point(
                northing=self._field("inv-n2"),
                easting=self._field("inv-e2"),
                elevation=self._field("inv-z2"),
            )
            result = inverse(p1, p2)
            bearing = Angle.from_radians(result.azimuth).to_bearing_string()
            az_dms = Angle.from_radians(result.azimuth).to_dms_string()

            panel = self.query_one("#inverse-results", ResultPanel)
            panel.set_results([
                ("Bearing:", bearing),
                ("Azimuth:", az_dms),
                ("Horiz. Distance:", f"{result.horizontal_distance:.4f}"),
                ("Slope Distance:", f"{result.slope_distance:.4f}"),
                ("Vert. Distance:", f"{result.vertical_distance:.4f}"),
                ("Grade:", f"{result.grade:.4f}%"),
            ])
            self.query_one("#error-msg", Static).update("")
            self._last_result = result
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _store_result(self) -> None:
        """Store the endpoint as a point in the job."""
        try:
            from cogokit.core import Point
            n = self._field("inv-n2")
            e = self._field("inv-e2")
            z = self._field("inv-z2")
            pt = Point(northing=n, easting=e, elevation=z)
            self.app.current_job.add_point(pt)
            self.query_one("#error-msg", Static).update("Point stored in job")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Traverse
# ---------------------------------------------------------------------------
class TraverseScreen(Screen):
    """Compute a new point from origin, azimuth, and distance."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    TraverseScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Forward Traverse / Sideshot", classes="section-title"),
            Static(
                "Compute a new point from origin, bearing, and distance",
                classes="screen-subtitle",
            ),
            FloatField("Origin Northing:", "trav-n", placeholder="e.g. 1000.0"),
            FloatField("Origin Easting:", "trav-e", placeholder="e.g. 2000.0"),
            FloatField("Azimuth (degrees):", "trav-az", placeholder="e.g. 45.0"),
            FloatField("Horiz. Distance:", "trav-dist", placeholder="e.g. 100.0"),
            FloatField("New Elevation:", "trav-elev", placeholder="0.0"),
            FloatField("Store as Pt #:", "trav-ptnum", placeholder="(optional)"),
            Horizontal(
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Store Point", id="btn-store"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Traverse Result", id="traverse-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float:
        f = self.query_one(f"#{fid}").parent
        val = f.get_value()
        return val if val is not None else 0.0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("trav-n", "trav-e", "trav-az", "trav-dist", "trav-elev", "trav-ptnum"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#traverse-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id == "btn-store":
            self._store_result()
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.cogo.traverse import traverse
            from cogokit.core import Angle, Point

            origin = Point(
                northing=self._field("trav-n"),
                easting=self._field("trav-e"),
            )
            az_deg = self._field("trav-az")
            az_rad = math.radians(az_deg)
            dist = self._field("trav-dist")
            elev = self._field("trav-elev")

            pt = traverse(origin, az_rad, dist, elev)
            bearing = Angle.from_radians(az_rad).to_bearing_string()

            panel = self.query_one("#traverse-results", ResultPanel)
            panel.set_results([
                ("Bearing:", bearing),
                ("New Northing:", f"{pt.northing:.4f}"),
                ("New Easting:", f"{pt.easting:.4f}"),
                ("Elevation:", f"{pt.elevation:.4f}"),
            ])
            self._last_point = pt
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _store_result(self) -> None:
        try:
            from cogokit.core import Point
            if not hasattr(self, "_last_point"):
                self.query_one("#error-msg", Static).update("Compute first")
                return
            pt_num_val = self._field("trav-ptnum")
            pt_num = int(pt_num_val) if pt_num_val else None
            pt = Point(
                northing=self._last_point.northing,
                easting=self._last_point.easting,
                elevation=self._last_point.elevation,
                number=pt_num,
            )
            self.app.current_job.add_point(pt)
            self.query_one("#error-msg", Static).update(
                f"Point {pt_num or ''} stored in job"
            )
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Intersections
# ---------------------------------------------------------------------------
class IntersectionsScreen(Screen):
    """Bearing-bearing, bearing-distance, and distance-distance intersections."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    IntersectionsScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Intersections", classes="section-title"),
            SelectField(
                "Type:", "int-type",
                options=[
                    ("Bearing-Bearing", "bb"),
                    ("Bearing-Distance", "bd"),
                    ("Distance-Distance", "dd"),
                ],
            ),
            Static("Point 1", classes="section-title"),
            FloatField("Northing 1:", "int-n1", placeholder="e.g. 1000.0"),
            FloatField("Easting 1:", "int-e1", placeholder="e.g. 2000.0"),
            FloatField("Bearing/Dist 1:", "int-v1", placeholder="Bearing (deg) or Radius"),
            Static("Point 2", classes="section-title"),
            FloatField("Northing 2:", "int-n2", placeholder="e.g. 1500.0"),
            FloatField("Easting 2:", "int-e2", placeholder="e.g. 2500.0"),
            FloatField("Bearing/Dist 2:", "int-v2", placeholder="Bearing (deg) or Radius"),
            Horizontal(
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Intersection Results", id="int-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float:
        f = self.query_one(f"#{fid}").parent
        val = f.get_value()
        return val if val is not None else 0.0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("int-n1", "int-e1", "int-v1", "int-n2", "int-e2", "int-v2"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#int-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.cogo.intersections import (
                bearing_bearing,
                bearing_distance,
                distance_distance,
            )
            from cogokit.core import Point

            p1 = Point(northing=self._field("int-n1"), easting=self._field("int-e1"))
            p2 = Point(northing=self._field("int-n2"), easting=self._field("int-e2"))
            v1 = self._field("int-v1")
            v2 = self._field("int-v2")

            sel = self.query_one("#int-type").parent
            int_type = sel.get_value() or "bb"

            panel = self.query_one("#int-results", ResultPanel)

            if int_type == "bb":
                result = bearing_bearing(p1, math.radians(v1), p2, math.radians(v2))
                if result is None:
                    panel.set_text("  No intersection found (parallel bearings)")
                else:
                    panel.set_results([
                        ("Northing:", f"{result.northing:.4f}"),
                        ("Easting:", f"{result.easting:.4f}"),
                    ])

            elif int_type == "bd":
                result = bearing_distance(p1, math.radians(v1), p2, v2)
                if result is None:
                    panel.set_text("  No intersection found")
                else:
                    pt1, pt2 = result
                    panel.set_results([
                        ("Solution 1 N:", f"{pt1.northing:.4f}"),
                        ("Solution 1 E:", f"{pt1.easting:.4f}"),
                        ("Solution 2 N:", f"{pt2.northing:.4f}"),
                        ("Solution 2 E:", f"{pt2.easting:.4f}"),
                    ])

            elif int_type == "dd":
                result = distance_distance(p1, v1, p2, v2)
                if result is None:
                    panel.set_text("  No intersection found")
                else:
                    pt1, pt2 = result
                    panel.set_results([
                        ("Solution 1 N:", f"{pt1.northing:.4f}"),
                        ("Solution 1 E:", f"{pt1.easting:.4f}"),
                        ("Solution 2 N:", f"{pt2.northing:.4f}"),
                        ("Solution 2 E:", f"{pt2.easting:.4f}"),
                    ])

            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Area & Perimeter
# ---------------------------------------------------------------------------
class AreaScreen(Screen):
    """Compute polygon area and perimeter from job points."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    AreaScreen { layout: vertical; }

    #area-point-list {
        height: 1fr;
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Area & Perimeter", classes="section-title"),
            Static(
                "Uses all points in the current job as polygon vertices (in order)",
                classes="screen-subtitle",
            ),
            Static("", id="area-point-list"),
            Horizontal(
                Button("Compute from Job", variant="primary", id="btn-compute"),
                classes="button-bar",
            ),
            ResultPanel("Area Results", id="area-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_mount(self) -> None:
        pts = self.app.current_job.points()
        if pts:
            lines = [f"  Pt {p.number}: N={p.northing:.4f}  E={p.easting:.4f}" for p in pts]
            self.query_one("#area-point-list", Static).update(
                f"Points in job ({len(pts)}):\n" + "\n".join(lines)
            )
        else:
            self.query_one("#area-point-list", Static).update(
                "No points in job. Add points via Point Manager first."
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.cogo.area import polygon_area, polygon_perimeter

            pts = self.app.current_job.points()
            if len(pts) < 3:
                self.query_one("#error-msg", Static).update(
                    "Error: need at least 3 points"
                )
                return

            a = polygon_area(pts)
            p = polygon_perimeter(pts)
            panel = self.query_one("#area-results", ResultPanel)
            panel.set_results([
                ("Area:", f"{a:.4f}"),
                ("Perimeter:", f"{p:.4f}"),
                ("Vertices:", str(len(pts))),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")
