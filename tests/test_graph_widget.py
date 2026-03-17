"""Integration tests for the GraphWidget."""

import pytest

try:
    from textual.app import App, ComposeResult
    from textual_plotext import PlotextPlot

    HAS_TUI = True
except ImportError:
    HAS_TUI = False

pytestmark = pytest.mark.skipif(not HAS_TUI, reason="textual/textual-plotext not installed")


if HAS_TUI:
    from cogokit.tui.viewmodels.graph_vm import GraphPointVM, GraphViewModel
    from cogokit.tui.widgets.graph_widget import GraphWidget

    class GraphTestApp(App):
        """Minimal app for testing GraphWidget."""

        def compose(self) -> ComposeResult:
            yield GraphWidget(id="graph")


def _make_vm(selected: set[int] | None = None) -> "GraphViewModel":
    selected = selected or set()
    points = [
        GraphPointVM(x=100, y=200, label="1", description="HUB", selected=1 in selected, point_number=1),
        GraphPointVM(x=300, y=400, label="2", description="IP", selected=2 in selected, point_number=2),
        GraphPointVM(x=500, y=600, label="3", description="", selected=3 in selected, point_number=3),
    ]
    return GraphViewModel(points=points)


@pytest.mark.asyncio
async def test_graph_mounts_without_error():
    """GraphWidget mounts and renders without crashing."""
    app = GraphTestApp()
    async with app.run_test():
        graph = app.query_one("#graph", GraphWidget)
        assert graph is not None


@pytest.mark.asyncio
async def test_graph_accepts_view_model():
    """Setting a view model triggers replot without error."""
    app = GraphTestApp()
    async with app.run_test():
        graph = app.query_one("#graph", GraphWidget)
        graph.view_model = _make_vm()
        # No assertion beyond "didn't crash"


@pytest.mark.asyncio
async def test_label_cycling():
    """Cycling labels advances through 3 modes."""
    app = GraphTestApp()
    async with app.run_test():
        graph = app.query_one("#graph", GraphWidget)
        graph.view_model = _make_vm()
        assert graph.label_mode == 0

        graph.cycle_labels()
        assert graph.label_mode == 1

        graph.cycle_labels()
        assert graph.label_mode == 2

        graph.cycle_labels()
        assert graph.label_mode == 0  # wraps around
