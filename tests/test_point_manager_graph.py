"""Integration tests for Point Manager + Graph interaction."""

import pytest

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Footer, Header

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

pytestmark = pytest.mark.skipif(not HAS_TUI, reason="textual not installed")

if HAS_TUI:
    from cogopro.core.job import Job
    from cogopro.tui.screens.point_manager import PointManagerScreen
    from cogopro.tui.widgets.graph_widget import GraphWidget

    class PMTestApp(App):
        """Minimal app wrapping PointManagerScreen for testing."""

        def __init__(self) -> None:
            super().__init__()
            self.current_job = Job(name="Test")

        def compose(self) -> ComposeResult:
            yield Header()
            yield Footer()

        def on_mount(self) -> None:
            self.push_screen(PointManagerScreen())


@pytest.mark.asyncio
async def test_point_manager_mounts_with_graph():
    """PointManagerScreen mounts with a GraphWidget present."""
    app = PMTestApp()
    async with app.run_test():
        graph = app.screen.query_one("#graph-panel", GraphWidget)
        assert graph is not None


@pytest.mark.asyncio
async def test_graph_updates_on_point_add():
    """Adding a point updates the graph view model."""
    from cogopro.core.point import Point

    app = PMTestApp()
    async with app.run_test():
        app.current_job.add_point(
            Point(northing=100, easting=200, number=1, description="A")
        )
        screen = app.screen
        screen._refresh_table()

        graph = screen.query_one("#graph-panel", GraphWidget)
        assert graph.view_model is not None
        assert len(graph.view_model.points) == 1
        assert graph.view_model.points[0].x == 200.0
        assert graph.view_model.points[0].y == 100.0


@pytest.mark.asyncio
async def test_layout_cycling_via_action():
    """Calling layout action directly cycles through modes."""
    app = PMTestApp()
    async with app.run_test():
        screen = app.screen
        assert screen._layout_mode.value == "side-by-side"

        screen.action_cycle_layout()
        assert screen._layout_mode.value == "stacked"

        screen.action_cycle_layout()
        assert screen._layout_mode.value == "overlay"

        screen.action_cycle_layout()
        assert screen._layout_mode.value == "side-by-side"
