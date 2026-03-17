"""Traverse-plus: field observation processing, station setup, and resection."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cogokit.core import Point
from cogokit.cogo.inverse import inverse
from cogokit.cogo.traverse import traverse


@dataclass
class FieldObservation:
    """A single field observation from a total station."""

    from_point: int
    to_point: int
    hz_angle: float  # radians, clockwise from backsight
    vertical_angle: float  # radians from horizontal (+ up, - down)
    slope_distance: float
    instrument_height: float = 0.0
    target_height: float = 0.0


def reduce_observation(obs: FieldObservation) -> tuple[float, float, float]:
    """Reduce a slope observation to horizontal distance, vertical distance, and delta elevation.

    Args:
        obs: Field observation with slope distance and vertical angle.

    Returns:
        Tuple of (horizontal_distance, vertical_distance, delta_elevation).
        delta_elevation accounts for instrument and target heights.
    """
    horizontal_distance = obs.slope_distance * math.cos(obs.vertical_angle)
    vertical_distance = obs.slope_distance * math.sin(obs.vertical_angle)
    delta_elevation = vertical_distance + obs.instrument_height - obs.target_height
    return (horizontal_distance, vertical_distance, delta_elevation)


@dataclass
class StationSetup:
    """A station setup with occupy point, backsight, and observations."""

    occupy_point: Point
    backsight_point: Point
    observations: list[FieldObservation] = field(default_factory=list)


def process_station(setup: StationSetup) -> list[Point]:
    """Process all observations from a station setup to compute foresight points.

    Computes backsight azimuth via inverse, then for each observation:
    - Computes foresight azimuth = backsight_azimuth + hz_angle
    - Reduces slope observation to horizontal distance
    - Traverses from occupy point along foresight azimuth

    Args:
        setup: Station setup with occupy point, backsight, and observations.

    Returns:
        List of computed foresight Points.
    """
    inv = inverse(setup.occupy_point, setup.backsight_point)
    backsight_az = inv.azimuth

    results: list[Point] = []
    for obs in setup.observations:
        foresight_az = (backsight_az + obs.hz_angle) % (2 * math.pi)
        hz_dist, _, delta_elev = reduce_observation(obs)
        new_elevation = setup.occupy_point.elevation + delta_elev
        pt = traverse(setup.occupy_point, foresight_az, hz_dist, elevation=new_elevation)
        pt = Point(
            northing=pt.northing,
            easting=pt.easting,
            elevation=pt.elevation,
            number=obs.to_point,
        )
        results.append(pt)
    return results


def resection_3point(
    p1: Point,
    p2: Point,
    p3: Point,
    angle_at_1_2: float,
    angle_at_2_3: float,
) -> Point:
    """Compute position of unknown point using Tienstra's 3-point resection.

    Given three known points and two subtended angles measured at the unknown
    point, computes the coordinates of the unknown point.

    Args:
        p1: First known point.
        p2: Second known point.
        p3: Third known point.
        angle_at_1_2: Angle subtended at unknown point between p1 and p2 (radians).
        angle_at_2_3: Angle subtended at unknown point between p2 and p3 (radians).

    Returns:
        Point at the computed resection position.
    """
    # Compute interior angles of triangle p1-p2-p3
    inv_1_2 = inverse(p1, p2)
    inv_1_3 = inverse(p1, p3)
    inv_2_1 = inverse(p2, p1)
    inv_2_3 = inverse(p2, p3)
    inv_3_1 = inverse(p3, p1)
    inv_3_2 = inverse(p3, p2)

    # Angle at p1 (between sides p1-p2 and p1-p3)
    angle_a = (inv_1_3.azimuth - inv_1_2.azimuth) % (2 * math.pi)
    if angle_a > math.pi:
        angle_a = 2 * math.pi - angle_a

    # Angle at p2 (between sides p2-1 and p2-p3)
    angle_b = (inv_2_3.azimuth - inv_2_1.azimuth) % (2 * math.pi)
    if angle_b > math.pi:
        angle_b = 2 * math.pi - angle_b

    # Angle at p3 (between sides p3-p1 and p3-p2)
    angle_c = (inv_3_2.azimuth - inv_3_1.azimuth) % (2 * math.pi)
    if angle_c > math.pi:
        angle_c = 2 * math.pi - angle_c

    # Tienstra's method
    # alpha subtends side p1-p2 (opposite vertex p3)
    # beta subtends side p2-p3 (opposite vertex p1)
    # gamma subtends side p3-p1 (opposite vertex p2)
    alpha = angle_at_1_2
    beta = angle_at_2_3
    gamma = 2 * math.pi - alpha - beta

    # Each vertex angle pairs with the subtended angle for its OPPOSITE side
    # K1: angle at p1 paired with beta (subtending p2-p3, opposite p1)
    # K2: angle at p2 paired with gamma (subtending p3-p1, opposite p2)
    # K3: angle at p3 paired with alpha (subtending p1-p2, opposite p3)
    k1 = 1.0 / (1.0 / math.tan(angle_a) - 1.0 / math.tan(beta))
    k2 = 1.0 / (1.0 / math.tan(angle_b) - 1.0 / math.tan(gamma))
    k3 = 1.0 / (1.0 / math.tan(angle_c) - 1.0 / math.tan(alpha))

    k_sum = k1 + k2 + k3

    northing = (k1 * p1.northing + k2 * p2.northing + k3 * p3.northing) / k_sum
    easting = (k1 * p1.easting + k2 * p2.easting + k3 * p3.easting) / k_sum

    return Point(northing=northing, easting=easting)
