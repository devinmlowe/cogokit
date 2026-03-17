"""Named line geometry: an ordered sequence of point references."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineString:
    """An ordered collection of point numbers forming a line or polygon.

    Points are referenced by number (not by value), so the geometry
    stays current as point coordinates are edited in the Job.

    Args:
        name: Human-readable identifier for this line.
        point_numbers: Ordered point numbers defining the geometry.
        closed: If True, the last point connects back to the first.
    """

    name: str
    point_numbers: tuple[int, ...]
    closed: bool = False

    # TODO: resolve_points(job) method to return actual Point objects
    # TODO: WKT / GeoJSON export

    def __len__(self) -> int:
        return len(self.point_numbers)

    def __contains__(self, point_number: int) -> bool:
        return point_number in self.point_numbers
