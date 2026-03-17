"""Surveying screens: Levelling, Traverse Workflow."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static

from cogopro.tui.widgets.form_fields import FloatField
from cogopro.tui.widgets.result_panel import ResultPanel


# ---------------------------------------------------------------------------
# Levelling
# ---------------------------------------------------------------------------
class LevellingScreen(Screen):
    """Differential level run reduction and loop closure."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    LevellingScreen { layout: vertical; }

    #level-obs-table {
        height: 12;
        margin: 1 2;
    }

    .obs-input-row {
        height: 3;
        margin: 0 2;
    }

    .obs-input-row Label {
        width: 8;
        height: 3;
        content-align-vertical: middle;
        padding: 1 0 0 0;
    }

    .obs-input-row Input {
        width: 1fr;
        height: 3;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Differential Levelling", classes="section-title")
            yield Static(
                "Reduce a level run and compute adjusted elevations",
                classes="screen-subtitle",
            )
            yield FloatField("Start Elevation:", "lev-start-elev", placeholder="e.g. 100.0")
            yield FloatField("End Elevation:", "lev-end-elev", placeholder="(for loop closure)")

            yield Static("Observations", classes="section-title")
            yield DataTable(id="level-obs-table")

            yield Static("Add Observation", classes="section-title")
            with Horizontal(classes="obs-input-row"):
                yield Label("BS:")
                yield Input(placeholder="Backsight", id="lev-bs", type="number")
                yield Label("FS:")
                yield Input(placeholder="Foresight", id="lev-fs", type="number")
                yield Label("IS:")
                yield Input(placeholder="Intermediate (opt)", id="lev-is", type="number")

            with Horizontal(classes="button-bar"):
                yield Button("Add", id="btn-add-obs")
                yield Button("Reduce", variant="primary", id="btn-compute")
                yield Button("Clear All", id="btn-clear")

            yield ResultPanel("Levelling Results", id="level-results")
            yield Static("", id="error-msg", classes="error-text")

    def on_mount(self) -> None:
        table = self.query_one("#level-obs-table", DataTable)
        table.add_columns("#", "BS", "FS", "IS")
        self._observations: list[dict] = []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        if bid == "btn-add-obs":
            self._add_obs()
        elif bid == "btn-compute":
            self._compute()
        elif bid == "btn-clear":
            self._clear_all()

    def _add_obs(self) -> None:
        try:
            bs_str = self.query_one("#lev-bs", Input).value.strip()
            fs_str = self.query_one("#lev-fs", Input).value.strip()
            is_str = self.query_one("#lev-is", Input).value.strip()

            bs = float(bs_str) if bs_str else None
            fs = float(fs_str) if fs_str else None
            is_val = float(is_str) if is_str else None

            if bs is None and fs is None and is_val is None:
                self.query_one("#error-msg", Static).update("Enter at least BS or FS")
                return

            obs = {"bs": bs, "fs": fs, "is": is_val}
            self._observations.append(obs)

            idx = len(self._observations)
            table = self.query_one("#level-obs-table", DataTable)
            table.add_row(
                str(idx),
                f"{bs:.4f}" if bs is not None else "-",
                f"{fs:.4f}" if fs is not None else "-",
                f"{is_val:.4f}" if is_val is not None else "-",
            )

            for fid in ("lev-bs", "lev-fs", "lev-is"):
                self.query_one(f"#{fid}", Input).value = ""
        except ValueError:
            self.query_one("#error-msg", Static).update("Invalid numeric input")

    def _compute(self) -> None:
        if not self._observations:
            self.query_one("#error-msg", Static).update("Add observations first")
            return

        try:
            from cogopro.surveying.levelling import (
                LevelObservation,
                adjust_level_loop,
                reduce_level_run,
            )

            start_elev_f = self.query_one("#lev-start-elev").parent
            start_elev = start_elev_f.get_value()
            if start_elev is None:
                self.query_one("#error-msg", Static).update("Start elevation required")
                return

            observations = []
            for obs in self._observations:
                observations.append(LevelObservation(
                    bs=obs["bs"],
                    fs=obs["fs"],
                    intermediate=obs["is"],
                ))

            end_elev_f = self.query_one("#lev-end-elev").parent
            end_elev = end_elev_f.get_value()

            if end_elev is not None:
                result = adjust_level_loop(observations, start_elev, end_elev)
            else:
                result = reduce_level_run(observations, start_elev)

            rows = [
                ("Start Elevation:", f"{start_elev:.4f}"),
            ]
            if hasattr(result, "misclosure") and result.misclosure is not None:
                rows.append(("Misclosure:", f"{result.misclosure:.4f}"))
            if hasattr(result, "correction_per_station") and result.correction_per_station is not None:
                rows.append(("Correction/Stn:", f"{result.correction_per_station:.4f}"))

            rows.append(("", ""))
            rows.append(("--- Elevations ---", ""))
            for i, elev in enumerate(result.elevations):
                rows.append((f"Station {i + 1}:", f"{elev:.4f}"))

            panel = self.query_one("#level-results", ResultPanel)
            panel.set_results(rows)
            self.query_one("#error-msg", Static).update("")
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _clear_all(self) -> None:
        self._observations.clear()
        self.query_one("#level-obs-table", DataTable).clear()
        self.query_one("#level-results", ResultPanel).clear()
        self.query_one("#error-msg", Static).update("")


# ---------------------------------------------------------------------------
# Traverse Workflow
# ---------------------------------------------------------------------------
class TraverseWorkflowScreen(Screen):
    """End-to-end traverse workflow from field observations."""

    FOOTER_HINTS = "Enter Calculate | Esc Back | ? Help"

    DEFAULT_CSS = """
    TraverseWorkflowScreen { layout: vertical; }

    #trav-obs-table {
        height: 12;
        margin: 1 2;
    }

    .trav-input-row {
        height: 3;
        margin: 0 2;
    }

    .trav-input-row Label {
        width: 8;
        height: 3;
        content-align-vertical: middle;
        padding: 1 0 0 0;
    }

    .trav-input-row Input {
        width: 1fr;
        height: 3;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Traverse Workflow", classes="section-title")
            yield Static(
                "End-to-end traverse: observation reduction, angular closure, "
                "coordinate computation, compass rule adjustment",
                classes="screen-subtitle",
            )

            yield Static("Starting Setup", classes="section-title")
            yield FloatField("Start Pt Number:", "tw-start-num", placeholder="e.g. 1")
            yield FloatField("Start Northing:", "tw-start-n", placeholder="e.g. 1000.0")
            yield FloatField("Start Easting:", "tw-start-e", placeholder="e.g. 5000.0")
            yield FloatField("Start Elevation:", "tw-start-z", placeholder="e.g. 100.0")
            yield FloatField("Start Azimuth (HP):", "tw-start-az", placeholder="HP notation, e.g. 45.0")

            yield Static("Observations", classes="section-title")
            yield DataTable(id="trav-obs-table")

            yield Static("Add Leg", classes="section-title")
            with Horizontal(classes="trav-input-row"):
                yield Label("Occ:")
                yield Input(placeholder="Occupied", id="tw-occ", type="integer")
                yield Label("BS:")
                yield Input(placeholder="Backsight", id="tw-bs", type="integer")
                yield Label("FS:")
                yield Input(placeholder="Foresight", id="tw-fs", type="integer")
            with Horizontal(classes="trav-input-row"):
                yield Label("Angle:")
                yield Input(placeholder="DMS angle", id="tw-angle", type="number")
                yield Label("Dist:")
                yield Input(placeholder="Distance", id="tw-dist", type="number")
            with Horizontal(classes="trav-input-row"):
                yield Label("HI:")
                yield Input(placeholder="Height of Inst.", id="tw-hi", type="number")
                yield Label("HT:")
                yield Input(placeholder="Height of Target", id="tw-ht", type="number")

            with Horizontal(classes="button-bar"):
                yield Button("Add Leg", id="btn-add-leg")
                yield Button("Run Traverse", variant="primary", id="btn-compute")
                yield Button("Clear All", id="btn-clear")

            yield ResultPanel("Traverse Results", id="trav-results")
            yield Static("", id="error-msg", classes="error-text")

    def on_mount(self) -> None:
        table = self.query_one("#trav-obs-table", DataTable)
        table.add_columns("Occ", "BS", "FS", "Angle", "Dist", "HI", "HT")
        self._legs: list[dict] = []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        if bid == "btn-add-leg":
            self._add_leg()
        elif bid == "btn-compute":
            self._compute()
        elif bid == "btn-clear":
            self._clear_all()

    def _add_leg(self) -> None:
        try:
            occ = int(self.query_one("#tw-occ", Input).value)
            bs = int(self.query_one("#tw-bs", Input).value)
            fs = int(self.query_one("#tw-fs", Input).value)
            angle = float(self.query_one("#tw-angle", Input).value)
            dist = float(self.query_one("#tw-dist", Input).value)
            hi_str = self.query_one("#tw-hi", Input).value.strip()
            ht_str = self.query_one("#tw-ht", Input).value.strip()
            hi = float(hi_str) if hi_str else 0.0
            ht = float(ht_str) if ht_str else 0.0
        except (ValueError, AttributeError):
            self.query_one("#error-msg", Static).update("Invalid input")
            return

        leg = {
            "occ": occ, "bs": bs, "fs": fs,
            "angle": angle, "dist": dist, "hi": hi, "ht": ht,
        }
        self._legs.append(leg)

        table = self.query_one("#trav-obs-table", DataTable)
        table.add_row(
            str(occ), str(bs), str(fs),
            f"{angle:.4f}", f"{dist:.4f}",
            f"{hi:.2f}", f"{ht:.2f}",
        )

        for fid in ("tw-occ", "tw-bs", "tw-fs", "tw-angle", "tw-dist", "tw-hi", "tw-ht"):
            self.query_one(f"#{fid}", Input).value = ""

    def _compute(self) -> None:
        if not self._legs:
            self.query_one("#error-msg", Static).update("Add legs first")
            return

        try:
            from cogopro.core import Point
            from cogopro.surveying.workflow import TraverseWorkflow

            start_num_f = self.query_one("#tw-start-num").parent
            start_num = start_num_f.get_value()
            start_n_f = self.query_one("#tw-start-n").parent
            start_n = start_n_f.get_value()
            start_e_f = self.query_one("#tw-start-e").parent
            start_e = start_e_f.get_value()
            start_z_f = self.query_one("#tw-start-z").parent
            start_z = start_z_f.get_value() or 0.0
            start_az_f = self.query_one("#tw-start-az").parent
            start_az = start_az_f.get_value()

            if any(v is None for v in (start_num, start_n, start_e, start_az)):
                self.query_one("#error-msg", Static).update(
                    "Start point and azimuth required"
                )
                return

            sp = Point(
                number=int(start_num),
                northing=start_n,
                easting=start_e,
                elevation=start_z,
            )

            wf = TraverseWorkflow(
                start_point=sp,
                start_azimuth=start_az,
                close_to_start=True,
            )

            for leg in self._legs:
                wf.add_leg(
                    occupied=leg["occ"],
                    backsight=leg["bs"],
                    foresight=leg["fs"],
                    angle_dms=leg["angle"],
                    distance=leg["dist"],
                    hi=leg["hi"],
                    ht=leg["ht"],
                )

            result = wf.run()

            rows = [
                ("Angular Misclosure:", result.angular_misclosure.to_dms_string(4)),
                ("Angular Tolerance:", result.angular_tolerance.to_dms_string(4)),
                ("Closure North:", f"{result.closure_north:.4f}"),
                ("Closure East:", f"{result.closure_east:.4f}"),
                ("Linear Misclosure:", f"{result.linear_misclosure:.4f}"),
                ("Perimeter:", f"{result.perimeter:.4f}"),
            ]

            if result.precision_ratio == float("inf"):
                rows.append(("Precision Ratio:", "Perfect (no misclosure)"))
            else:
                rows.append(("Precision Ratio:", f"1:{result.precision_ratio:.0f}"))

            rows.append(("", ""))
            rows.append(("--- Adjusted Coordinates ---", ""))
            for pt in result.adjusted_job.points():
                rows.append((
                    f"Pt {pt.number}:",
                    f"N={pt.northing:.4f}  E={pt.easting:.4f}  Z={pt.elevation:.4f}",
                ))

            # Store adjusted points in current job
            self.app.current_job = result.adjusted_job

            panel = self.query_one("#trav-results", ResultPanel)
            panel.set_results(rows)
            self.query_one("#error-msg", Static).update(
                "Adjusted coordinates stored in current job"
            )
        except Exception as exc:
            self.query_one("#error-msg", Static).update(f"Error: {exc}")

    def _clear_all(self) -> None:
        self._legs.clear()
        self.query_one("#trav-obs-table", DataTable).clear()
        self.query_one("#trav-results", ResultPanel).clear()
        self.query_one("#error-msg", Static).update("")
