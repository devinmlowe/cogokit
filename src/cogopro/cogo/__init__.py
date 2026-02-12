"""COGO functions: traverse, inverse, intersections, area."""

from typing import NamedTuple


class Point(NamedTuple):
    """Survey point with northing, easting, and optional elevation."""

    northing: float
    easting: float
    elevation: float = 0.0
