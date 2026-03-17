"""Solver screens: Triangle, Horizontal Curve, Vertical Curve."""

from __future__ import annotations

import math

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static

from cogokit.tui.widgets.form_fields import FloatField, SelectField
from cogokit.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Triangle Solver
# ---------------------------------------------------------------------------
class TriangleScreen(Screen):
    """Solve a triangle given sides and/or angles."""

    FOOTER_HINTS = "Enter Solve | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    TriangleScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Triangle Solver", classes="section-title"),
            SelectField(
                "Solution Case:", "tri-case",
                options=[
                    ("SSS - Three Sides", "sss"),
                    ("SAS - Side-Angle-Side", "sas"),
                    ("ASA - Angle-Side-Angle", "asa"),
                    ("AAS - Angle-Angle-Side", "aas"),
                    ("SSA - Side-Side-Angle", "ssa"),
                ],
            ),
            Static("Sides", classes="section-title"),
            FloatField("Side a:", "tri-a", placeholder="opposite angle A"),
            FloatField("Side b:", "tri-b", placeholder="opposite angle B"),
            FloatField("Side c:", "tri-c", placeholder="opposite angle C"),
            Static("Angles (degrees)", classes="section-title"),
            FloatField("Angle A:", "tri-A", placeholder="opposite side a"),
            FloatField("Angle B:", "tri-B", placeholder="opposite side b"),
            FloatField("Angle C:", "tri-C", placeholder="opposite side c"),
            Horizontal(
                Button("Solve", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Triangle Solution", id="tri-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float | None:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("tri-a", "tri-b", "tri-c", "tri-A", "tri-B", "tri-C"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#tri-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.solvers.triangle import (
                solve_aas,
                solve_asa,
                solve_sas,
                solve_ssa,
                solve_sss,
            )

            sel = self.query_one("#tri-case").parent
            case = sel.get_value() or "sss"
            a = self._field("tri-a")
            b = self._field("tri-b")
            c = self._field("tri-c")
            A = self._field("tri-A")
            B = self._field("tri-B")
            C = self._field("tri-C")

            # Convert angles from degrees to radians
            A_rad = math.radians(A) if A is not None else None
            B_rad = math.radians(B) if B is not None else None
            C_rad = math.radians(C) if C is not None else None

            if case == "sss":
                sol = solve_sss(a, b, c)
            elif case == "sas":
                sol = solve_sas(a, C_rad, b)
            elif case == "asa":
                sol = solve_asa(A_rad, c, B_rad)
            elif case == "aas":
                sol = solve_aas(A_rad, B_rad, a)
            elif case == "ssa":
                sol = solve_ssa(a, b, A_rad)
            else:
                self.query_one("#error-msg", Static).update("Select a case")
                return

            panel = self.query_one("#tri-results", ResultPanel)

            # Handle SSA which may return two solutions
            if case == "ssa" and isinstance(sol, tuple):
                rows = []
                for i, s in enumerate(sol, 1):
                    rows.append((f"--- Solution {i} ---", ""))
                    rows.extend(self._format_solution(s))
                panel.set_results(rows)
            else:
                panel.set_results(self._format_solution(sol))

            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _format_solution(self, sol) -> list[tuple[str, str]]:
        return [
            ("Side a:", f"{sol.a:.4f}"),
            ("Side b:", f"{sol.b:.4f}"),
            ("Side c:", f"{sol.c:.4f}"),
            ("Angle A:", f"{math.degrees(sol.A):.4f} deg"),
            ("Angle B:", f"{math.degrees(sol.B):.4f} deg"),
            ("Angle C:", f"{math.degrees(sol.C):.4f} deg"),
            ("Area:", f"{sol.area:.4f}"),
            ("Perimeter:", f"{sol.perimeter:.4f}"),
        ]


# ---------------------------------------------------------------------------
# Horizontal Curve
# ---------------------------------------------------------------------------
class HorizontalCurveScreen(Screen):
    """Solve a horizontal curve from any two elements."""

    FOOTER_HINTS = "Enter Solve | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    HorizontalCurveScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Horizontal Curve Solver", classes="section-title"),
            Static(
                "Enter exactly 2 curve elements to solve for the rest",
                classes="screen-subtitle",
            ),
            FloatField("Radius (R):", "hc-R", placeholder=""),
            FloatField("Delta (degrees):", "hc-delta", placeholder="Central angle"),
            FloatField("Tangent (T):", "hc-T", placeholder=""),
            FloatField("Arc Length (L):", "hc-L", placeholder=""),
            FloatField("Chord (C):", "hc-C", placeholder=""),
            FloatField("External (E):", "hc-E", placeholder=""),
            FloatField("Mid-Ordinate (M):", "hc-M", placeholder=""),
            FloatField("Degree of Curve (D):", "hc-D", placeholder=""),
            Horizontal(
                Button("Solve", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Curve Solution", id="hc-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("hc-R", "hc-delta", "hc-T", "hc-L", "hc-C", "hc-E", "hc-M", "hc-D"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#hc-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.core import Angle
            from cogokit.solvers.horizontal_curve import solve_curve

            kwargs: dict[str, float] = {}
            field_map = {
                "hc-R": "R",
                "hc-delta": "delta",
                "hc-T": "T",
                "hc-L": "L",
                "hc-C": "C",
                "hc-E": "E",
                "hc-M": "M",
                "hc-D": "D",
            }

            for fid, key in field_map.items():
                f = self.query_one(f"#{fid}").parent
                val = f.get_value()
                if val is not None:
                    if key == "delta":
                        kwargs[key] = math.radians(val)
                    else:
                        kwargs[key] = val

            if len(kwargs) != 2:
                self.query_one("#error-msg", Static).update(
                    f"Provide exactly 2 elements (got {len(kwargs)})"
                )
                return

            c = solve_curve(**kwargs)
            delta_str = Angle.from_radians(c.delta).to_dms_string()

            panel = self.query_one("#hc-results", ResultPanel)
            panel.set_results([
                ("Radius:", f"{c.R:.4f}"),
                ("Delta:", delta_str),
                ("Tangent:", f"{c.T:.4f}"),
                ("Arc Length:", f"{c.L:.4f}"),
                ("Chord:", f"{c.C:.4f}"),
                ("External:", f"{c.E:.4f}"),
                ("Mid-Ordinate:", f"{c.M:.4f}"),
                ("Degree of Curve:", f"{c.D:.4f}"),
            ])
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Vertical Curve
# ---------------------------------------------------------------------------
class VerticalCurveScreen(Screen):
    """Solve a parabolic vertical curve."""

    FOOTER_HINTS = "Enter Solve | Esc Back | q Quit | ? Help"

    DEFAULT_CSS = """
    VerticalCurveScreen { layout: vertical; }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static("Vertical Curve Solver", classes="section-title"),
            Static(
                "Solve a parabolic vertical curve and compute elevations",
                classes="screen-subtitle",
            ),
            FloatField("Grade In (g1) %:", "vc-g1", placeholder="e.g. 2.5"),
            FloatField("Grade Out (g2) %:", "vc-g2", placeholder="e.g. -1.5"),
            FloatField("Curve Length (L):", "vc-L", placeholder="e.g. 400"),
            FloatField("PVI Station:", "vc-pvi-sta", placeholder="e.g. 1000"),
            FloatField("PVI Elevation:", "vc-pvi-elev", placeholder="e.g. 500"),
            FloatField("Compute at Station:", "vc-sta", placeholder="(optional)"),
            Horizontal(
                Button("Solve", variant="primary", id="btn-compute"),
                Button("Clear", id="btn-clear"),
                classes="button-bar",
            ),
            ResultPanel("Vertical Curve Solution", id="vc-results"),
            Static("", id="error-msg", classes="error-text"),
        )

    def _field(self, fid: str) -> float | None:
        f = self.query_one(f"#{fid}").parent
        return f.get_value()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clear":
            for fid in ("vc-g1", "vc-g2", "vc-L", "vc-pvi-sta", "vc-pvi-elev", "vc-sta"):
                self.query_one(f"#{fid}").value = ""
            self.query_one("#vc-results", ResultPanel).clear()
            self.query_one("#error-msg", Static).update("")
            return

        if event.button.id != "btn-compute":
            return

        try:
            from cogokit.solvers.vertical_curve import (
                elevation_at,
                solve_vertical_curve,
            )

            g1 = self._field("vc-g1")
            g2 = self._field("vc-g2")
            length = self._field("vc-L")

            if g1 is None or g2 is None or length is None:
                self.query_one("#error-msg", Static).update(
                    "g1, g2, and L are required"
                )
                return

            curve = solve_vertical_curve(g1, g2, length)

            pvi_sta = self._field("vc-pvi-sta") or 0.0
            pvi_elev = self._field("vc-pvi-elev") or 0.0

            bvc_sta = pvi_sta - length / 2
            evc_sta = pvi_sta + length / 2
            bvc_elev = pvi_elev - (g1 / 100) * (length / 2)
            evc_elev = pvi_elev + (g2 / 100) * (length / 2)

            rows = [
                ("BVC Station:", f"{bvc_sta:.4f}"),
                ("BVC Elevation:", f"{bvc_elev:.4f}"),
                ("PVI Station:", f"{pvi_sta:.4f}"),
                ("PVI Elevation:", f"{pvi_elev:.4f}"),
                ("EVC Station:", f"{evc_sta:.4f}"),
                ("EVC Elevation:", f"{evc_elev:.4f}"),
                ("Curve Type:", curve.curve_type),
                ("Rate of Change:", f"{curve.r:.6f}"),
                ("K Value:", f"{curve.K:.4f}"),
            ]

            if curve.high_low_station is not None:
                hl_sta = bvc_sta + curve.high_low_station
                hl_elev = elevation_at(curve.high_low_station, curve)
                hl_elev_adj = bvc_elev + hl_elev
                rows.append(("High/Low Station:", f"{hl_sta:.4f}"))
                rows.append(("High/Low Elevation:", f"{hl_elev_adj:.4f}"))

            sta_query = self._field("vc-sta")
            if sta_query is not None:
                dist_from_bvc = sta_query - bvc_sta
                if 0 <= dist_from_bvc <= length:
                    elev_on_curve = elevation_at(dist_from_bvc, curve)
                    elev_adj = bvc_elev + elev_on_curve
                    rows.append(("", ""))
                    rows.append((f"Sta {sta_query:.2f}:", f"Elev = {elev_adj:.4f}"))
                else:
                    rows.append(("", ""))
                    rows.append(("Query station:", "outside curve limits"))

            panel = self.query_one("#vc-results", ResultPanel)
            panel.set_results(rows)
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")
