"""Graph view-model: domain-agnostic data for the graph widget."""

from __future__ import annotations

from dataclasses import dataclass, field

from cogokit.core.job import Job


@dataclass
class GraphPointVM:
    """A single point ready for graph rendering.

    Coordinates use easting (x) and northing (y) so that the plot
    matches plan-view orientation (north = up).
    """

    x: float
    y: float
    label: str
    description: str
    selected: bool
    point_number: int | None = None


@dataclass
class GraphLineVM:
    """A polyline ready for graph rendering."""

    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)
    label: str = ""
    # TODO: implement line rendering in GraphWidget (see GH issue)


@dataclass
class GraphViewModel:
    """Complete state for a single graph render pass."""

    points: list[GraphPointVM] = field(default_factory=list)
    lines: list[GraphLineVM] = field(default_factory=list)


def build_graph_vm(job: Job, selected_numbers: set[int] | None = None) -> GraphViewModel:
    """Build a GraphViewModel from a Job and optional selection set.

    Maps Point.easting → x, Point.northing → y so that the plot
    shows a conventional plan view (north up, east right).
    """
    if selected_numbers is None:
        selected_numbers = set()

    points = []
    for pt in job.points():
        points.append(
            GraphPointVM(
                x=pt.easting,
                y=pt.northing,
                label=str(pt.number) if pt.number is not None else "",
                description=pt.description or "",
                selected=pt.number in selected_numbers,
                point_number=pt.number,
            )
        )

    return GraphViewModel(points=points)
