"""Stakeout calculations for surveying field layout."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogopro.core import Point
from cogopro.cogo.inverse import inverse


@dataclass
class StakeoutResult:
    """Result of a stakeout calculation."""

    azimuth: float  # radians, from instrument to target
    distance: float  # horizontal distance
    cut_fill: float | None = None  # positive=cut, negative=fill
    station: float | None = None
    offset: float | None = None


def stake_point(
    instrument: Point,
    target: Point,
    design_elevation: float | None = None,
) -> StakeoutResult:
    """Compute stakeout data from instrument to target point.

    Args:
        instrument: Instrument setup point.
        target: Point to stake out.
        design_elevation: If provided, computes cut/fill.

    Returns:
        StakeoutResult with azimuth and distance from instrument to target.
    """
    inv = inverse(instrument, target)

    cut_fill = None
    if design_elevation is not None:
        cut_fill = target.elevation - design_elevation

    return StakeoutResult(
        azimuth=inv.azimuth,
        distance=inv.horizontal_distance,
        cut_fill=cut_fill,
    )


def batch_stake(
    instrument: Point,
    targets: list[tuple[Point, float | None]],
) -> list[StakeoutResult]:
    """Stake multiple points from a single instrument position.

    Args:
        instrument: Instrument setup point.
        targets: List of (target_point, design_elevation_or_None).

    Returns:
        List of StakeoutResult for each target.
    """
    return [
        stake_point(instrument, target, design_elev)
        for target, design_elev in targets
    ]


def stake_alignment_station(
    instrument: Point,
    alignment,
    station: float,
    offset: float = 0.0,
) -> StakeoutResult:
    """Compute stakeout data for a station/offset on an alignment.

    Uses duck typing: alignment must have a point_at_station(float) -> Point method.

    Args:
        instrument: Instrument setup point.
        alignment: Object with point_at_station(station) method.
        station: Station value along the alignment.
        offset: Perpendicular offset (positive=right, negative=left).

    Returns:
        StakeoutResult with station and offset included.
    """
    target = alignment.point_at_station(station)

    if offset != 0.0:
        delta = 0.01
        p_before = alignment.point_at_station(station - delta)
        p_after = alignment.point_at_station(station + delta)
        tangent_az = inverse(p_before, p_after).azimuth

        perp_az = tangent_az + math.pi / 2
        target = Point(
            northing=target.northing + offset * math.cos(perp_az),
            easting=target.easting + offset * math.sin(perp_az),
            elevation=target.elevation,
        )

    inv = inverse(instrument, target)

    return StakeoutResult(
        azimuth=inv.azimuth,
        distance=inv.horizontal_distance,
        station=station,
        offset=offset if offset != 0.0 else None,
    )


def slope_stake(
    centerline_point: Point,
    design_elevation: float,
    ground_points: list[tuple[float, float]],
    template_slopes: list[tuple[float, float]],
) -> tuple[float, float]:
    """Find where a design template intersects the ground surface.

    Args:
        centerline_point: Centerline point of the cross-section.
        design_elevation: Design elevation at the centerline.
        ground_points: Ground cross-section as [(offset, elevation), ...].
        template_slopes: Design template as [(offset, relative_elevation), ...].
            Relative elevations are added to design_elevation. The slope of the
            last segment is extended until it intersects the ground.

    Returns:
        (catch_offset, catch_elevation) where the template meets the ground.
    """
    ground = sorted(ground_points, key=lambda p: p[0])
    template = sorted(template_slopes, key=lambda p: p[0])

    abs_template = [(o, design_elevation + rel_e) for o, rel_e in template]

    if len(abs_template) >= 2:
        o1, e1 = abs_template[-2]
        o2, e2 = abs_template[-1]
        ext_slope = (e2 - e1) / (o2 - o1) if o2 != o1 else 0.0
    else:
        ext_slope = 0.0

    last_offset, last_elev = abs_template[-1]

    for i in range(len(ground) - 1):
        go1, ge1 = ground[i]
        go2, ge2 = ground[i + 1]

        if go2 <= last_offset:
            continue

        seg_start = max(go1, last_offset)
        if seg_start > go1 and go2 != go1:
            t = (seg_start - go1) / (go2 - go1)
            seg_ge1 = ge1 + t * (ge2 - ge1)
        else:
            seg_ge1 = ge1
            seg_start = go1

        seg_end = go2
        seg_ge2 = ge2

        g_slope = (seg_ge2 - seg_ge1) / (seg_end - seg_start) if seg_end != seg_start else 0.0

        denom = ext_slope - g_slope
        if abs(denom) < 1e-10:
            continue

        x = (seg_ge1 - g_slope * seg_start - last_elev + ext_slope * last_offset) / denom

        if seg_start - 1e-9 <= x <= seg_end + 1e-9:
            y = last_elev + ext_slope * (x - last_offset)
            return (round(x, 6), round(y, 6))

    o = ground[-1][0]
    e = last_elev + ext_slope * (o - last_offset)
    return (o, e)
