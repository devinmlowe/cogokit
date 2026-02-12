"""Inverse calculation: azimuth and distance between two points."""

import math
from typing import NamedTuple

from . import Point


class InverseResult(NamedTuple):
    """Result of an inverse calculation."""

    azimuth: float  # radians, clockwise from north (0 to 2*pi)
    horizontal_distance: float
    vertical_distance: float  # positive = up from P1 to P2
    slope_distance: float
    grade: float  # percent (rise/run * 100), 0 if horizontal_distance is 0


def inverse(p1: Point, p2: Point) -> InverseResult:
    """Compute azimuth, distances, and grade from p1 to p2.

    Args:
        p1: Starting point (northing, easting, elevation).
        p2: Ending point (northing, easting, elevation).

    Returns:
        InverseResult with azimuth (radians), horizontal distance,
        vertical distance, slope distance, and grade (%).
    """
    dn = p2.northing - p1.northing
    de = p2.easting - p1.easting
    dz = p2.elevation - p1.elevation

    azimuth = math.atan2(de, dn) % (2 * math.pi)
    horizontal_distance = math.hypot(dn, de)
    slope_distance = math.sqrt(dn**2 + de**2 + dz**2)
    grade = (dz / horizontal_distance * 100) if horizontal_distance > 0 else 0.0

    return InverseResult(
        azimuth=azimuth,
        horizontal_distance=horizontal_distance,
        vertical_distance=dz,
        slope_distance=slope_distance,
        grade=grade,
    )
