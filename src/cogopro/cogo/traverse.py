"""Traverse: compute new point from starting point, azimuth, and distance."""

import math

from . import Point


def traverse(origin: Point, azimuth: float, distance: float, elevation: float = 0.0) -> Point:
    """Compute a new point by traversing from origin along azimuth for distance.

    Args:
        origin: Starting point.
        azimuth: Direction in radians, clockwise from north.
        distance: Horizontal distance to traverse.
        elevation: Elevation of the new point (default 0.0).

    Returns:
        New Point at the computed location.
    """
    northing = origin.northing + distance * math.cos(azimuth)
    easting = origin.easting + distance * math.sin(azimuth)
    return Point(northing=northing, easting=easting, elevation=elevation)


def sideshot(
    origin: Point,
    backsight_azimuth: float,
    angle_right: float,
    distance: float,
    elevation: float = 0.0,
) -> Point:
    """Compute a point from a sideshot (angle turn from backsight + distance).

    Args:
        origin: Instrument point.
        backsight_azimuth: Azimuth from origin to backsight (radians).
        angle_right: Clockwise angle measured from backsight to foresight (radians).
        distance: Horizontal distance to the new point.
        elevation: Elevation of the new point (default 0.0).

    Returns:
        New Point at the computed location.
    """
    foresight_azimuth = (backsight_azimuth + angle_right) % (2 * math.pi)
    return traverse(origin, foresight_azimuth, distance, elevation)
