"""Adjustment screens: Compass Rule, Helmert Transform, Transforms."""

from __future__ import annotations

import math

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static

from cogokit.tui.widgets.form_fields import FloatField, SelectField
from cogokit.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Compass Rule (Bowditch)
# ---------------------------------------------------------------------------
class CompassRuleScreen(Screen):
    """Bowditch traverse adjustment using points in the current job."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    CompassRuleScreen { layout: vertical; }

    #compass-point-list {
        margin: 1 2;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Compass Rule (Bowditch) Adjustment", classes="section-title"),
            Static(
                "Adjusts traverse coordinates using the Bowditch method. "
                "Uses points in the current job as the raw traverse.",
                classes="screen-subtitle",
            ),
            Static("", id="compass-point-list"),
            SelectField(
                "Traverse Type:", "compass-type",
                options=[
                    ("Closed Loop", "closed"),
                    ("Fixed Endpoint", "fixed"),
                ],
            ),
            FloatField("End Northing:", "compass-en", placeholder="(for fixed endpoint)"),
            FloatField("End Easting:", "compass-ee", placeholder="(for fixed endpoint)"),
            Horizontal(
                Button("Adjust", variant="primary", id="btn-compute"),
                classes="button-bar",
            ),
            ResultPanel("Adjustment Results", id="compass-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_mount(self) -> None:
        self._refresh_point_list()

    def _refresh_point_list(self) -> None:
        pts = self.app.current_job.points()
        if pts:
            lines = [f"  Pt {p.number}: N={p.northing:.4f}  E={p.easting:.4f}" for p in pts]
            self.query_one("#compass-point-list", Static).update(
                f"Traverse points ({len(pts)}):\n" + "\n".join(lines)
            )
        else:
            self.query_one("#compass-point-list", Static).update(
                "No points in job. Add traverse points via Point Manager first."
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.adjustments.compass_rule import compass_rule

            pts = self.app.current_job.points()
            if len(pts) < 3:
                self.query_one("#error-msg", Static).update("Need at least 3 points")
                return

            sel = self.query_one("#compass-type").parent
            trav_type = sel.get_value() or "closed"

            coords = [(p.northing, p.easting) for p in pts]

            known_end = None
            if trav_type == "fixed":
                en_field = self.query_one("#compass-en").parent
                ee_field = self.query_one("#compass-ee").parent
                en = en_field.get_value()
                ee = ee_field.get_value()
                if en is not None and ee is not None:
                    known_end = (en, ee)

            result = compass_rule(coords, known_end=known_end)

            rows = [
                ("Closure North:", f"{result.closure_north:.4f}"),
                ("Closure East:", f"{result.closure_east:.4f}"),
                ("Linear Closure:", f"{result.linear_closure:.4f}"),
                ("Perimeter:", f"{result.perimeter:.4f}"),
            ]
            if result.precision_ratio == float("inf"):
                rows.append(("Precision:", "Perfect (no misclosure)"))
            else:
                rows.append(("Precision:", f"1:{result.precision_ratio:.0f}"))
            rows.append(("", ""))
            rows.append(("--- Adjusted Coordinates ---", ""))
            for i, (n, e) in enumerate(result.adjusted):
                pt = pts[i] if i < len(pts) else None
                label = f"Pt {pt.number}:" if pt and pt.number else f"Pt {i + 1}:"
                rows.append((label, f"N={n:.4f}  E={e:.4f}"))

            panel = self.query_one("#compass-results", ResultPanel)
            panel.set_results(rows)
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Helmert Transform
# ---------------------------------------------------------------------------
class HelmertScreen(Screen):
    """2D similarity transformation between two point sets."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    HelmertScreen { layout: vertical; }

    .helmert-table {
        height: 10;
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Helmert 2D Similarity Transform", classes="section-title"),
            Static(
                "Compute translation, rotation, and scale between source and target point sets. "
                "Enter matching point pairs below.",
                classes="screen-subtitle",
            ),
            Static("Source Points (From)", classes="section-title"),
            DataTable(id="src-table", classes="helmert-table"),
            Static("Target Points (To)", classes="section-title"),
            DataTable(id="tgt-table", classes="helmert-table"),
            Static("Add Point Pair", classes="section-title"),
            FloatField("Source N:", "hlm-sn", placeholder="Source Northing"),
            FloatField("Source E:", "hlm-se", placeholder="Source Easting"),
            FloatField("Target N:", "hlm-tn", placeholder="Target Northing"),
            FloatField("Target E:", "hlm-te", placeholder="Target Easting"),
            Horizontal(
                Button("Add Pair", id="btn-add-pair"),
                Button("Compute", variant="primary", id="btn-compute"),
                Button("Apply to Job", id="btn-apply"),
                Button("Clear All", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Helmert Parameters", id="helmert-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_mount(self) -> None:
        src = self.query_one("#src-table", DataTable)
        src.add_columns("#", "Northing", "Easting")
        tgt = self.query_one("#tgt-table", DataTable)
        tgt.add_columns("#", "Northing", "Easting")
        self._source_pts: list[tuple[float, float]] = []
        self._target_pts: list[tuple[float, float]] = []
        self._helmert_result = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        if bid == "btn-add-pair":
            self._add_pair()
        elif bid == "btn-compute":
            self._compute()
        elif bid == "btn-apply":
            self._apply_to_job()
        elif bid == "btn-clear":
            self._clear_all()

    def _add_pair(self) -> None:
        try:
            sn = float(self.query_one("#hlm-sn").value)
            se = float(self.query_one("#hlm-se").value)
            tn = float(self.query_one("#hlm-tn").value)
            te = float(self.query_one("#hlm-te").value)
        except (ValueError, AttributeError):
            self.query_one("#error-msg", Static).update("Invalid numeric input")
            return

        idx = len(self._source_pts) + 1
        self._source_pts.append((sn, se))
        self._target_pts.append((tn, te))

        self.query_one("#src-table", DataTable).add_row(str(idx), f"{sn:.4f}", f"{se:.4f}")
        self.query_one("#tgt-table", DataTable).add_row(str(idx), f"{tn:.4f}", f"{te:.4f}")

        for fid in ("hlm-sn", "hlm-se", "hlm-tn", "hlm-te"):
            self.query_one(f"#{fid}").value = ""

    def _compute(self) -> None:
        if len(self._source_pts) < 2:
            self.query_one("#error-msg", Static).update("Need at least 2 point pairs")
            return

        try:
            from cogokit.adjustments.helmert import helmert_2d
            from cogokit.core import Point

            source = [Point(northing=n, easting=e) for n, e in self._source_pts]
            target = [Point(northing=n, easting=e) for n, e in self._target_pts]

            result = helmert_2d(source, target)
            self._helmert_result = result

            panel = self.query_one("#helmert-results", ResultPanel)
            panel.set_results([
                ("Translation N:", f"{result.translation_n:.6f}"),
                ("Translation E:", f"{result.translation_e:.6f}"),
                ("Rotation:", f"{math.degrees(result.rotation):.6f} deg"),
                ("Scale Factor:", f"{result.scale:.8f}"),
                ("RMS Residual:", f"{result.rms:.6f}"),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _apply_to_job(self) -> None:
        if self._helmert_result is None:
            self.query_one("#error-msg", Static).update("Compute transform first")
            return

        try:
            from cogokit.adjustments.helmert import apply_helmert

            pts = self.app.current_job.points()
            if not pts:
                self.query_one("#error-msg", Static).update("No points in job")
                return

            transformed = apply_helmert(pts, self._helmert_result)
            from cogokit.core.job import Job
            new_job = Job(name=self.app.current_job.name)
            for pt in transformed:
                new_job.add_point(pt)
            self.app.current_job = new_job
            self.query_one("#error-msg", Static).update(
                f"Transform applied to {len(transformed)} points"
            )
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _clear_all(self) -> None:
        self._source_pts.clear()
        self._target_pts.clear()
        self._helmert_result = None
        self.query_one("#src-table", DataTable).clear()
        self.query_one("#tgt-table", DataTable).clear()
        self.query_one("#helmert-results", ResultPanel).clear()
        self.query_one("#error-msg", Static).update("")


# ---------------------------------------------------------------------------
# Transforms (Rotate, Mirror, Shift, Scale)
# ---------------------------------------------------------------------------
class TransformsScreen(Screen):
    """Apply geometric transformations to job points."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    TransformsScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Point Transforms", classes="section-title"),
            Static(
                "Apply geometric transformations to all points in the current job",
                classes="screen-subtitle",
            ),
            SelectField(
                "Transform:", "tf-type",
                options=[
                    ("Rotate", "rotate"),
                    ("Shift (Translate)", "shift"),
                    ("Scale", "scale"),
                    ("Mirror", "mirror"),
                ],
            ),
            Static("Parameters", classes="section-title"),
            FloatField("Angle (degrees):", "tf-angle", placeholder="Rotation angle"),
            FloatField("Delta North:", "tf-dn", placeholder="Shift north"),
            FloatField("Delta East:", "tf-de", placeholder="Shift east"),
            FloatField("Scale Factor:", "tf-scale", placeholder="e.g. 1.0"),
            FloatField("Origin North:", "tf-on", placeholder="Transform origin N"),
            FloatField("Origin East:", "tf-oe", placeholder="Transform origin E"),
            FloatField("Mirror Pt2 North:", "tf-mn", placeholder="Second axis point N"),
            FloatField("Mirror Pt2 East:", "tf-me", placeholder="Second axis point E"),
            Horizontal(
                Button("Apply", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Transform Results", id="tf-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float | None:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("tf-angle", "tf-dn", "tf-de", "tf-scale", "tf-on", "tf-oe", "tf-mn", "tf-me"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#tf-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.adjustments.transforms import mirror, rotate, scale, shift
            from cogokit.core import Point
            from cogokit.core.job import Job

            pts = self.app.current_job.points()
            if not pts:
                self.query_one("#error-msg", Static).update("No points in job")
                return

            sel = self.query_one("#tf-type").parent
            tf_type = sel.get_value() or "rotate"

            if tf_type == "rotate":
                angle = self._field("tf-angle")
                if angle is None:
                    self.query_one("#error-msg", Static).update("Angle required")
                    return
                on = self._field("tf-on") or 0.0
                oe = self._field("tf-oe") or 0.0
                origin = Point(northing=on, easting=oe)
                result = rotate(pts, math.radians(angle), origin)

            elif tf_type == "shift":
                dn = self._field("tf-dn") or 0.0
                de = self._field("tf-de") or 0.0
                result = shift(pts, dn, de)

            elif tf_type == "scale":
                factor = self._field("tf-scale")
                if factor is None:
                    self.query_one("#error-msg", Static).update("Scale factor required")
                    return
                on = self._field("tf-on") or 0.0
                oe = self._field("tf-oe") or 0.0
                origin = Point(northing=on, easting=oe)
                result = scale(pts, factor, origin)

            elif tf_type == "mirror":
                on = self._field("tf-on") or 0.0
                oe = self._field("tf-oe") or 0.0
                mn = self._field("tf-mn")
                me = self._field("tf-me")
                if mn is None or me is None:
                    self.query_one("#error-msg", Static).update(
                        "Mirror axis points required"
                    )
                    return
                p1 = Point(northing=on, easting=oe)
                p2 = Point(northing=mn, easting=me)
                result = mirror(pts, p1, p2)
            else:
                return

            # Update job with transformed points
            new_job = Job(name=self.app.current_job.name)
            for pt in result:
                new_job.add_point(pt)
            self.app.current_job = new_job

            panel = self.query_one("#tf-results", ResultPanel)
            lines = [f"Applied '{tf_type}' to {len(result)} points\n"]
            for p in result:
                lines.append(
                    f"  {p.number or '-'}: N={p.northing:.4f}  E={p.easting:.4f}"
                )
            panel.set_text("\n".join(lines))
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")
