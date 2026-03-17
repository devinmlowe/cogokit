"""Basic coordinate transformations: rotate, mirror, shift, scale, average."""

from __future__ import annotations

import math

from cogokit.core import Point


def rotate(
    points: list[Point],
    angle: float,
    center: Point | None = None,
) -> list[Point]:
    """Rotate points about a center by a given angle.

    Args:
        points: Points to rotate.
        angle: Rotation angle in radians (positive = counterclockwise).
        center: Center of rotation. Defaults to origin.
    """
    if center is None:
        center = Point(northing=0.0, easting=0.0)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cn, ce = center.northing, center.easting
    result: list[Point] = []
    for pt in points:
        dn = pt.northing - cn
        de = pt.easting - ce
        result.append(Point(
            northing=cn + dn * cos_a - de * sin_a,
            easting=ce + dn * sin_a + de * cos_a,
            elevation=pt.elevation,
            number=pt.number,
            description=pt.description,
        ))
    return result


def mirror(
    points: list[Point],
    axis: str = "n",
    value: float = 0.0,
) -> list[Point]:
    """Mirror/reflect points across an axis.

    Args:
        points: Points to mirror.
        axis: ``"n"`` to reflect across a northing line (flips easting),
              ``"e"`` to reflect across an easting line (flips northing).
        value: Coordinate value of the axis line.
    """
    result: list[Point] = []
    for pt in points:
        if axis == "n":
            result.append(Point(
                northing=pt.northing,
                easting=2 * value - pt.easting,
                elevation=pt.elevation,
                number=pt.number,
                description=pt.description,
            ))
        elif axis == "e":
            result.append(Point(
                northing=2 * value - pt.northing,
                easting=pt.easting,
                elevation=pt.elevation,
                number=pt.number,
                description=pt.description,
            ))
        else:
            raise ValueError(f"axis must be 'n' or 'e', got '{axis}'")
    return result


def shift(
    points: list[Point],
    dn: float = 0.0,
    de: float = 0.0,
    dz: float = 0.0,
) -> list[Point]:
    """Shift/translate points by given offsets.

    Args:
        points: Points to shift.
        dn: Northing offset.
        de: Easting offset.
        dz: Elevation offset.
    """
    return [
        Point(
            northing=pt.northing + dn,
            easting=pt.easting + de,
            elevation=pt.elevation + dz,
            number=pt.number,
            description=pt.description,
        )
        for pt in points
    ]


def scale(
    points: list[Point],
    factor: float,
    center: Point | None = None,
) -> list[Point]:
    """Scale points from a center point by a given factor.

    Args:
        points: Points to scale.
        factor: Scale factor (1.0 = no change).
        center: Center of scaling. Defaults to origin.
    """
    if center is None:
        center = Point(northing=0.0, easting=0.0)
    cn, ce = center.northing, center.easting
    return [
        Point(
            northing=cn + (pt.northing - cn) * factor,
            easting=ce + (pt.easting - ce) * factor,
            elevation=pt.elevation,
            number=pt.number,
            description=pt.description,
        )
        for pt in points
    ]


def average(
    observations: list[Point],
) -> Point:
    """Average multiple coordinate observations to a single point.

    Args:
        observations: Points for the same location.

    Returns:
        Averaged Point.
    """
    if not observations:
        raise ValueError("At least one observation required")
    count = len(observations)
    sum_n = sum(obs.northing for obs in observations)
    sum_e = sum(obs.easting for obs in observations)
    return Point(northing=sum_n / count, easting=sum_e / count)
