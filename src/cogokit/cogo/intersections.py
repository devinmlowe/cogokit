"""Intersection problems: bearing-bearing, bearing-distance, distance-distance."""

import math

from . import Point


def bearing_bearing(
    p1: Point, bearing1: float, p2: Point, bearing2: float
) -> Point | None:
    """Find the intersection of two lines defined by point + bearing.

    Args:
        p1: Point on the first line.
        bearing1: Azimuth of the first line (radians, clockwise from north).
        p2: Point on the second line.
        bearing2: Azimuth of the second line (radians, clockwise from north).

    Returns:
        Intersection Point, or None if lines are parallel.
    """
    sin1, cos1 = math.sin(bearing1), math.cos(bearing1)
    sin2, cos2 = math.sin(bearing2), math.cos(bearing2)

    det = sin1 * cos2 - cos1 * sin2
    if abs(det) < 1e-12:
        return None  # parallel lines

    dn = p2.northing - p1.northing
    de = p2.easting - p1.easting

    t1 = (de * cos2 - dn * sin2) / det

    northing = p1.northing + t1 * cos1
    easting = p1.easting + t1 * sin1
    return Point(northing=northing, easting=easting)


def bearing_distance(
    p1: Point, bearing: float, p2: Point, radius: float
) -> tuple[Point, Point] | None:
    """Find intersection of a line (point + bearing) with a circle (center + radius).

    Args:
        p1: Point on the line.
        bearing: Azimuth of the line (radians, clockwise from north).
        p2: Center of the circle.
        radius: Radius of the circle.

    Returns:
        Tuple of two intersection Points, or None if no intersection.
        First point is the nearer intersection along the bearing direction.
    """
    cos_b, sin_b = math.cos(bearing), math.sin(bearing)
    dn = p1.northing - p2.northing
    de = p1.easting - p2.easting

    # Quadratic: t^2 + 2bt + c = 0 where b = dn*cos + de*sin, c = dn^2 + de^2 - r^2
    b_coeff = dn * cos_b + de * sin_b
    c_coeff = dn**2 + de**2 - radius**2

    discriminant = b_coeff**2 - c_coeff
    if discriminant < 0:
        return None

    sqrt_disc = math.sqrt(discriminant)
    t1 = -b_coeff - sqrt_disc
    t2 = -b_coeff + sqrt_disc

    pt1 = Point(northing=p1.northing + t1 * cos_b, easting=p1.easting + t1 * sin_b)
    pt2 = Point(northing=p1.northing + t2 * cos_b, easting=p1.easting + t2 * sin_b)
    return (pt1, pt2)


def distance_distance(
    p1: Point, r1: float, p2: Point, r2: float
) -> tuple[Point, Point] | None:
    """Find intersection of two circles defined by center + radius.

    Args:
        p1: Center of the first circle.
        r1: Radius of the first circle.
        p2: Center of the second circle.
        r2: Radius of the second circle.

    Returns:
        Tuple of two intersection Points (left and right when facing from p1 to p2),
        or None if no intersection.
    """
    dn = p2.northing - p1.northing
    de = p2.easting - p1.easting
    d = math.hypot(dn, de)

    if d < 1e-12 or d > r1 + r2 or d < abs(r1 - r2):
        return None  # no intersection

    a = (r1**2 - r2**2 + d**2) / (2 * d)
    h_sq = r1**2 - a**2
    if h_sq < 0:
        return None
    h = math.sqrt(h_sq)

    # Point on line between centers at distance a from p1
    n_mid = p1.northing + a * dn / d
    e_mid = p1.easting + a * de / d

    # Perpendicular offset
    pt1 = Point(northing=n_mid + h * de / d, easting=e_mid - h * dn / d)
    pt2 = Point(northing=n_mid - h * de / d, easting=e_mid + h * dn / d)
    return (pt1, pt2)
