"""Compass Rule (Bowditch) traverse adjustment."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class CompassRuleResult:
    """Result of a compass rule adjustment."""

    adjusted: list[tuple[float, float]]
    misclosure_n: float
    misclosure_e: float
    linear_misclosure: float
    total_length: float
    precision_ratio: float  # the N in "1:N"


def compass_rule(
    coordinates: list[tuple[float, float]],
    known_end: tuple[float, float] | None = None,
) -> CompassRuleResult:
    """Adjust traverse coordinates using the Compass Rule (Bowditch method).

    Distributes linear misclosure proportionally by cumulative leg length.

    Args:
        coordinates: List of (northing, easting) tuples. First point is the
            fixed starting point. Last point is the observed ending point.
        known_end: For fixed-endpoint traverses, the known coordinates of the
            ending point. If None, assumes a closed-loop traverse where the
            ending point should coincide with the starting point.

    Returns:
        CompassRuleResult with adjusted coordinates and statistics.
    """
    if len(coordinates) < 3:
        raise ValueError("Traverse must have at least 3 points")

    # Determine target ending point
    target = coordinates[0] if known_end is None else known_end

    # Compute misclosure
    last = coordinates[-1]
    misclosure_n = last[0] - target[0]
    misclosure_e = last[1] - target[1]
    linear_misclosure = math.hypot(misclosure_n, misclosure_e)

    # Compute leg lengths
    leg_lengths: list[float] = []
    for i in range(1, len(coordinates)):
        dn = coordinates[i][0] - coordinates[i - 1][0]
        de = coordinates[i][1] - coordinates[i - 1][1]
        leg_lengths.append(math.hypot(dn, de))

    total_length = sum(leg_lengths)
    if total_length < 1e-12:
        raise ValueError("Total traverse length is zero")

    precision_ratio = (
        total_length / linear_misclosure if linear_misclosure > 1e-12 else float("inf")
    )

    # Apply corrections proportional to cumulative distance
    adjusted: list[tuple[float, float]] = [coordinates[0]]
    cumulative = 0.0
    for i, leg in enumerate(leg_lengths):
        cumulative += leg
        ratio = cumulative / total_length
        adj_n = coordinates[i + 1][0] - misclosure_n * ratio
        adj_e = coordinates[i + 1][1] - misclosure_e * ratio
        adjusted.append((adj_n, adj_e))

    return CompassRuleResult(
        adjusted=adjusted,
        misclosure_n=misclosure_n,
        misclosure_e=misclosure_e,
        linear_misclosure=linear_misclosure,
        total_length=total_length,
        precision_ratio=precision_ratio,
    )
