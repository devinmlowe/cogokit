"""Basic coordinate transformations: rotate, mirror, shift, scale, average."""

from __future__ import annotations

import math


def rotate(
    points: list[tuple[float, float]],
    angle: float,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[tuple[float, float]]:
    """Rotate points about a center by a given angle.

    Args:
        points: (northing, easting) tuples.
        angle: Rotation angle in radians (positive = counterclockwise).
        center: Center of rotation (northing, easting).
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    cn, ce = center
    result: list[tuple[float, float]] = []
    for n, e in points:
        dn = n - cn
        de = e - ce
        result.append((cn + dn * cos_a - de * sin_a, ce + dn * sin_a + de * cos_a))
    return result


def mirror(
    points: list[tuple[float, float]],
    axis: str = "n",
    value: float = 0.0,
) -> list[tuple[float, float]]:
    """Mirror/reflect points across an axis.

    Args:
        points: (northing, easting) tuples.
        axis: ``"n"`` to reflect across a northing line (flips easting),
              ``"e"`` to reflect across an easting line (flips northing).
        value: Coordinate value of the axis line.
    """
    result: list[tuple[float, float]] = []
    for n, e in points:
        if axis == "n":
            result.append((n, 2 * value - e))
        elif axis == "e":
            result.append((2 * value - n, e))
        else:
            raise ValueError(f"axis must be 'n' or 'e', got '{axis}'")
    return result


def shift(
    points: list[tuple[float, float]],
    dn: float = 0.0,
    de: float = 0.0,
) -> list[tuple[float, float]]:
    """Shift/translate points by given offsets.

    Args:
        points: (northing, easting) tuples.
        dn: Northing offset.
        de: Easting offset.
    """
    return [(n + dn, e + de) for n, e in points]


def scale(
    points: list[tuple[float, float]],
    factor: float,
    center: tuple[float, float] = (0.0, 0.0),
) -> list[tuple[float, float]]:
    """Scale points from a center point by a given factor.

    Args:
        points: (northing, easting) tuples.
        factor: Scale factor (1.0 = no change).
        center: Center of scaling (northing, easting).
    """
    cn, ce = center
    return [(cn + (n - cn) * factor, ce + (e - ce) * factor) for n, e in points]


def average(
    observations: list[tuple[float, float]],
) -> tuple[float, float]:
    """Average multiple coordinate observations to a single point.

    Args:
        observations: (northing, easting) tuples for the same point.

    Returns:
        Averaged (northing, easting) tuple.
    """
    if not observations:
        raise ValueError("At least one observation required")
    count = len(observations)
    sum_n = sum(obs[0] for obs in observations)
    sum_e = sum(obs[1] for obs in observations)
    return (sum_n / count, sum_e / count)
