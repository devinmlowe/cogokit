"""Main menu screen mirroring the cogokit menu system."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Static


class MainMenuScreen(Screen):
    """Top-level menu for navigating all cogokit modules."""

    FOOTER_HINTS = "1-8 Navigate | q Quit | ? Help"

    DEFAULT_CSS = """
    MainMenuScreen {
        layout: vertical;
    }

    #menu-scroll {
        height: 1fr;
    }

    #menu-wrapper {
        align: center middle;
        height: auto;
    }

    .menu-section {
        width: 56;
        height: auto;
        margin: 0 2 1 2;
        padding: 1 2;
        border: solid $primary;
    }

    .menu-section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    .menu-section Button {
        width: 100%;
        margin-bottom: 0;
    }

    #banner {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin: 1 0;
    }

    #job-info {
        text-align: center;
        color: $text-muted;
        margin: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Center(
                Vertical(
                    Static("cogokit", id="banner"),
                    Static("Job: Default | Points: 0", id="job-info"),

                    Vertical(
                        Static("Points & Job", classes="menu-section-title"),
                        Button("Point Manager", id="btn-points"),
                        Button("Load Points File", id="btn-load"),
                        Button("Save / Export", id="btn-export"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Coordinate Geometry", classes="menu-section-title"),
                        Button("Inverse", id="btn-inverse"),
                        Button("Traverse / Sideshot", id="btn-traverse"),
                        Button("Intersections", id="btn-intersections"),
                        Button("Area & Perimeter", id="btn-area"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Solvers", classes="menu-section-title"),
                        Button("Triangle Solver", id="btn-triangle"),
                        Button("Horizontal Curve", id="btn-hcurve"),
                        Button("Vertical Curve", id="btn-vcurve"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Geodetic", classes="menu-section-title"),
                        Button("Vincenty Direct", id="btn-vincenty-direct"),
                        Button("Vincenty Inverse", id="btn-vincenty-inverse"),
                        Button("Coordinate Conversion", id="btn-convert"),
                        Button("State Plane Zones", id="btn-zones"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Adjustments", classes="menu-section-title"),
                        Button("Compass Rule", id="btn-compass"),
                        Button("Helmert Transform", id="btn-helmert"),
                        Button("Transforms", id="btn-transforms"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Surveying", classes="menu-section-title"),
                        Button("Levelling", id="btn-levelling"),
                        Button("Traverse Workflow", id="btn-trav-workflow"),
                        classes="menu-section",
                    ),

                    Vertical(
                        Static("Application", classes="menu-section-title"),
                        Button("Settings", id="btn-settings"),
                        classes="menu-section",
                    ),

                    id="menu-wrapper",
                ),
            ),
            id="menu-scroll",
        )

    def on_mount(self) -> None:
        self._update_job_info()

    def on_screen_resume(self) -> None:
        self._update_job_info()

    def _update_job_info(self) -> None:
        job = self.app.current_job
        count = len(job.points())
        self.query_one("#job-info", Static).update(
            f"Job: {job.name} | Points: {count}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-points":
            from cogokit.tui.screens.point_manager import PointManagerScreen
            self.app.push_screen(PointManagerScreen())

        elif button_id == "btn-load":
            from cogokit.tui.screens.io_screen import LoadPointsScreen
            self.app.push_screen(LoadPointsScreen())

        elif button_id == "btn-export":
            from cogokit.tui.screens.io_screen import ExportScreen
            self.app.push_screen(ExportScreen())

        elif button_id == "btn-inverse":
            from cogokit.tui.screens.cogo import InverseScreen
            self.app.push_screen(InverseScreen())

        elif button_id == "btn-traverse":
            from cogokit.tui.screens.cogo import TraverseScreen
            self.app.push_screen(TraverseScreen())

        elif button_id == "btn-intersections":
            from cogokit.tui.screens.cogo import IntersectionsScreen
            self.app.push_screen(IntersectionsScreen())

        elif button_id == "btn-area":
            from cogokit.tui.screens.cogo import AreaScreen
            self.app.push_screen(AreaScreen())

        elif button_id == "btn-triangle":
            from cogokit.tui.screens.solvers import TriangleScreen
            self.app.push_screen(TriangleScreen())

        elif button_id == "btn-hcurve":
            from cogokit.tui.screens.solvers import HorizontalCurveScreen
            self.app.push_screen(HorizontalCurveScreen())

        elif button_id == "btn-vcurve":
            from cogokit.tui.screens.solvers import VerticalCurveScreen
            self.app.push_screen(VerticalCurveScreen())

        elif button_id == "btn-vincenty-direct":
            from cogokit.tui.screens.geodetic import VincentyDirectScreen
            self.app.push_screen(VincentyDirectScreen())

        elif button_id == "btn-vincenty-inverse":
            from cogokit.tui.screens.geodetic import VincentyInverseScreen
            self.app.push_screen(VincentyInverseScreen())

        elif button_id == "btn-convert":
            from cogokit.tui.screens.geodetic import ConvertScreen
            self.app.push_screen(ConvertScreen())

        elif button_id == "btn-zones":
            from cogokit.tui.screens.geodetic import ZonesScreen
            self.app.push_screen(ZonesScreen())

        elif button_id == "btn-compass":
            from cogokit.tui.screens.adjustments import CompassRuleScreen
            self.app.push_screen(CompassRuleScreen())

        elif button_id == "btn-helmert":
            from cogokit.tui.screens.adjustments import HelmertScreen
            self.app.push_screen(HelmertScreen())

        elif button_id == "btn-transforms":
            from cogokit.tui.screens.adjustments import TransformsScreen
            self.app.push_screen(TransformsScreen())

        elif button_id == "btn-levelling":
            from cogokit.tui.screens.surveying import LevellingScreen
            self.app.push_screen(LevellingScreen())

        elif button_id == "btn-trav-workflow":
            from cogokit.tui.screens.surveying import TraverseWorkflowScreen
            self.app.push_screen(TraverseWorkflowScreen())

        elif button_id == "btn-settings":
            from cogokit.tui.screens.settings import SettingsScreen
            self.app.push_screen(SettingsScreen())
