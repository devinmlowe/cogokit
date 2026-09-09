"""Polygon area and perimeter calculation using the coordinate (shoelace) method."""

import math

from . import Point


def polygon_area(points: list[Point]) -> float:
    """Compute the area of a polygon using the shoelace formula.

    Args:
        points: Ordered list of polygon vertices (minimum 3).
            The polygon is automatically closed (last point connects to first).

    Returns:
        Area in square units (always positive).

    Raises:
        ValueError: If fewer than 3 points are provided.
    """
    n = len(points)
    if n < 3:
        raise ValueError("At least 3 points required for area calculation")

    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        total += points[i].northing * points[j].easting
        total -= points[j].northing * points[i].easting

    return abs(total) / 2.0


def polygon_perimeter(points: list[Point]) -> float:
    """Compute the perimeter of a polygon.

    Args:
        points: Ordered list of polygon vertices (minimum 3).
            The polygon is automatically closed (last point connects to first).

    Returns:
        Perimeter length in linear units.

    Raises:
        ValueError: If fewer than 3 points are provided.
    """
    n = len(points)
    if n < 3:
        raise ValueError("At least 3 points required for perimeter calculation")

    total = 0.0
    for i in range(n):
        j = (i + 1) % n
        dn = points[j].northing - points[i].northing
        de = points[j].easting - points[i].easting
        total += math.hypot(dn, de)

    return total
