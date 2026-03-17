"""2D aerial graph widget for plan-view point visualization."""

from __future__ import annotations

import math

from textual.message import Message
from textual.reactive import reactive

from textual_plotext import PlotextPlot

from cogokit.tui.viewmodels.graph_vm import GraphLineVM, GraphPointVM, GraphViewModel


class GraphWidget(PlotextPlot):
    """MVVM-style 2D graph that renders a GraphViewModel.

    The widget is domain-agnostic: it knows about GraphPointVM (x, y,
    label, selected) but nothing about surveying Points or Jobs.  The
    parent screen is responsible for building the view-model.

    Label modes (cycled with cycle_labels):
        0 — point numbers only (default)
        1 — point numbers + descriptions
        2 — no labels
    """

    # -- Reactive state ------------------------------------------------

    view_model: reactive[GraphViewModel | None] = reactive(None)
    label_mode: reactive[int] = reactive(0)

    # -- Style constants -----------------------------------------------

    SELECTED_COLOR = "cyan"
    UNSELECTED_COLOR = "gray"
    SELECTED_MARKER = "dot"
    UNSELECTED_MARKER = "dot"
    LABEL_OFFSET_X = 0.0  # data-space offset for label placement
    LABEL_OFFSET_Y_FRAC = 0.02  # fraction of y-range for label offset

    # -- Messages ------------------------------------------------------

    class GraphPointClicked(Message):
        """Posted when the user clicks near a point in the graph."""

        def __init__(self, point_number: int) -> None:
            super().__init__()
            self.point_number = point_number

    # -- Lifecycle -----------------------------------------------------

    def on_mount(self) -> None:
        self.replot()

    # -- Watchers ------------------------------------------------------

    def watch_view_model(self, _old: GraphViewModel | None, _new: GraphViewModel | None) -> None:
        self.replot()

    def watch_label_mode(self, _old: int, _new: int) -> None:
        self.replot()

    # -- Public API ----------------------------------------------------

    def cycle_labels(self) -> None:
        """Advance label mode: numbers → numbers+desc → none → numbers."""
        self.label_mode = (self.label_mode + 1) % 3

    # -- Rendering -----------------------------------------------------

    def replot(self) -> None:
        """Redraw the plot from the current view_model."""
        plt = self.plt
        plt.clear_data()
        plt.clear_figure()

        vm = self.view_model
        if vm is None or not vm.points:
            plt.title("No Points")
            self.refresh()
            return

        # Partition points by selection state
        sel_xs, sel_ys = [], []
        unsel_xs, unsel_ys = [], []
        for pt in vm.points:
            if pt.selected:
                sel_xs.append(pt.x)
                sel_ys.append(pt.y)
            else:
                unsel_xs.append(pt.x)
                unsel_ys.append(pt.y)

        # Plot unselected first (behind), then selected (on top)
        if unsel_xs:
            plt.scatter(
                unsel_xs,
                unsel_ys,
                marker=self.UNSELECTED_MARKER,
                color=self.UNSELECTED_COLOR,
            )
        if sel_xs:
            plt.scatter(
                sel_xs,
                sel_ys,
                marker=self.SELECTED_MARKER,
                color=self.SELECTED_COLOR,
            )

        # Lines (linestrings)
        LINE_COLOR = "white"
        for line in vm.lines:
            if len(line.xs) >= 2:
                plt.plot(line.xs, line.ys, color=LINE_COLOR)

        # Labels
        if self.label_mode < 2:
            y_range = self._y_range(vm.points)
            y_offset = y_range * self.LABEL_OFFSET_Y_FRAC if y_range > 0 else 0.5
            for pt in vm.points:
                label_text = pt.label
                if self.label_mode == 1 and pt.description:
                    label_text = f"{pt.label} {pt.description}"
                if label_text:
                    color = self.SELECTED_COLOR if pt.selected else self.UNSELECTED_COLOR
                    plt.text(label_text, pt.x, pt.y + y_offset, color=color)

        plt.xlabel("Easting")
        plt.ylabel("Northing")
        self.refresh()

    # -- Mouse interaction ---------------------------------------------

    def on_click(self, event) -> None:
        """Map click position to nearest point and post message."""
        vm = self.view_model
        if vm is None or not vm.points:
            return

        # Map terminal character position to data coordinates
        data_x, data_y = self._screen_to_data(event.x, event.y)
        if data_x is None:
            return

        # Find nearest point
        nearest = self._find_nearest(vm.points, data_x, data_y)
        if nearest is not None and nearest.point_number is not None:
            self.post_message(self.GraphPointClicked(nearest.point_number))

    def _screen_to_data(self, sx: int, sy: int) -> tuple[float | None, float | None]:
        """Convert screen character coordinates to data coordinates.

        Uses plotext axis limits and widget size to compute a linear mapping.
        This is approximate due to plotext's internal padding/margins.
        """
        try:
            xlim = self.plt.xlim()
            ylim = self.plt.ylim()
        except Exception:
            return None, None

        if not xlim or not ylim:
            return None, None

        w = self.size.width
        h = self.size.height

        if w <= 0 or h <= 0:
            return None, None

        # Approximate margins (plotext uses ~10 chars left, ~2 right, ~2 top, ~3 bottom)
        margin_left = 10
        margin_right = 2
        margin_top = 2
        margin_bottom = 3

        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom

        if plot_w <= 0 or plot_h <= 0:
            return None, None

        # Linear interpolation from screen to data
        x_frac = (sx - margin_left) / plot_w
        y_frac = 1.0 - (sy - margin_top) / plot_h  # y is inverted in terminal

        data_x = xlim[0] + x_frac * (xlim[1] - xlim[0])
        data_y = ylim[0] + y_frac * (ylim[1] - ylim[0])

        return data_x, data_y

    def _find_nearest(
        self, points: list[GraphPointVM], data_x: float, data_y: float
    ) -> GraphPointVM | None:
        """Find the nearest point within a reasonable threshold."""
        if not points:
            return None

        x_range = self._x_range(points)
        y_range = self._y_range(points)
        # Threshold: 10% of the smaller axis range (generous for terminal precision)
        threshold = max(min(x_range, y_range) * 0.10, 1.0)

        best = None
        best_dist = float("inf")
        for pt in points:
            dist = math.hypot(pt.x - data_x, pt.y - data_y)
            if dist < best_dist:
                best_dist = dist
                best = pt

        if best_dist <= threshold:
            return best
        return None

    # -- Helpers -------------------------------------------------------

    @staticmethod
    def _x_range(points: list[GraphPointVM]) -> float:
        xs = [p.x for p in points]
        return max(xs) - min(xs) if xs else 0.0

    @staticmethod
    def _y_range(points: list[GraphPointVM]) -> float:
        ys = [p.y for p in points]
        return max(ys) - min(ys) if ys else 0.0
