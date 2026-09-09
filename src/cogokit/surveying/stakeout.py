"""Stakeout calculations for surveying field layout."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from cogokit.core import Point
from cogokit.cogo.inverse import inverse
from cogokit.surveying.cross_sections import (
    CrossSection,
    DesignTemplate,
    interpolate_surface,
)


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


# ---------------------------------------------------------------------------
# 3-D slope staking
# ---------------------------------------------------------------------------


@dataclass
class SlopeStakePoint:
    """A single catch point from 3D slope staking."""

    station: float
    offset: float  # negative=left, positive=right
    ground_elevation: float
    design_elevation: float
    cut_fill: float  # ground - design; positive=cut
    point: Point  # 3D coordinate (N, E, Z)
    converged: bool
    iterations: int


@dataclass
class SlopeStakeResult:
    """Complete slope stake result at one station."""

    station: float
    left: SlopeStakePoint
    right: SlopeStakePoint
    centerline_point: Point
    design_cl_elevation: float
    ground_cl_elevation: float


def _find_catch_point(
    sections: List[CrossSection],
    station: float,
    design_cl_elevation: float,
    template: DesignTemplate,
    side: str,
    tolerance: float = 0.001,
    max_iterations: int = 50,
) -> tuple[float, float, float, bool, int]:
    """Iteratively find where a design template slope meets the ground.

    Args:
        sections: Ground cross-sections for surface interpolation.
        station: Station along the alignment.
        design_cl_elevation: Design elevation at centerline.
        template: Design template with offset/elevation pairs.
        side: ``'left'`` (offset <= 0) or ``'right'`` (offset >= 0).
        tolerance: Convergence tolerance in offset units.
        max_iterations: Maximum iteration count.

    Returns:
        (catch_offset, ground_elev, design_elev, converged, iterations)
    """
    sorted_pts = sorted(template.points, key=lambda p: p.offset)

    # Extract template half for given side
    if side == "left":
        half = [p for p in sorted_pts if p.offset <= 0]
        if not half:
            half = [sorted_pts[0]]
    else:
        half = [p for p in sorted_pts if p.offset >= 0]
        if not half:
            half = [sorted_pts[-1]]

    half = sorted(half, key=lambda p: p.offset)

    # Compute extension slope from last two points on this side
    if side == "left":
        # For left side, the "outer" edge is the most negative offset
        edge_pts = half[:2] if len(half) >= 2 else half
        if len(edge_pts) >= 2:
            p0, p1 = edge_pts[0], edge_pts[1]
            if p1.offset != p0.offset:
                ext_slope = (p0.elevation - p1.elevation) / (p0.offset - p1.offset)
            else:
                ext_slope = 0.0
        else:
            ext_slope = 0.0
        last_offset = half[0].offset
        last_rel_elev = half[0].elevation
    else:
        # For right side, the "outer" edge is the most positive offset
        edge_pts = half[-2:] if len(half) >= 2 else half
        if len(edge_pts) >= 2:
            p0, p1 = edge_pts[0], edge_pts[1]
            if p1.offset != p0.offset:
                ext_slope = (p1.elevation - p0.elevation) / (p1.offset - p0.offset)
            else:
                ext_slope = 0.0
        else:
            ext_slope = 0.0
        last_offset = half[-1].offset
        last_rel_elev = half[-1].elevation

    last_abs_elev = design_cl_elevation + last_rel_elev

    # Initial guess: start at the template edge
    if side == "left":
        guess_offset = last_offset - 5.0  # start 5m beyond edge
    else:
        guess_offset = last_offset + 5.0

    converged = False
    iterations = 0

    for iterations in range(1, max_iterations + 1):
        ground_elev = interpolate_surface(sections, station, guess_offset)
        design_elev = last_abs_elev + ext_slope * (guess_offset - last_offset)
        diff = ground_elev - design_elev

        if abs(diff) < tolerance:
            converged = True
            break

        # Adjust: move outward if design is below ground (cut territory),
        # move inward if design is above ground (fill territory)
        # New guess: where would the template slope hit this ground elevation?
        if abs(ext_slope) > 1e-10:
            new_offset = last_offset + (ground_elev - last_abs_elev) / ext_slope
        else:
            # Flat extension slope — can't converge via slope
            new_offset = guess_offset
            break

        if abs(new_offset - guess_offset) < tolerance:
            guess_offset = new_offset
            converged = True
            break

        guess_offset = new_offset

    ground_elev = interpolate_surface(sections, station, guess_offset)
    design_elev = last_abs_elev + ext_slope * (guess_offset - last_offset)

    return (guess_offset, ground_elev, design_elev, converged, iterations)


def slope_stake_3d(
    alignment,
    sections: List[CrossSection],
    template: DesignTemplate,
    station: float,
    tolerance: float = 0.001,
    max_iterations: int = 50,
) -> SlopeStakeResult:
    """Compute 3D slope stake at a single station.

    Args:
        alignment: 3D alignment with point_at_station() and vertical profile.
        sections: Ground cross-sections for surface interpolation.
        template: Design cross-section template.
        station: Station along the alignment.
        tolerance: Convergence tolerance.
        max_iterations: Maximum iterations for catch-point search.

    Returns:
        SlopeStakeResult with left and right catch points.
    """
    cl_point = alignment.point_at_station(station)
    design_cl_elev = alignment.vertical.elevation_at(station)
    ground_cl_elev = interpolate_surface(sections, station, 0.0)

    # Get tangent azimuth for offset-to-coordinate conversion
    delta = 0.01
    p_before = alignment.point_at_station(station - delta)
    p_after = alignment.point_at_station(station + delta)
    tangent_az = inverse(p_before, p_after).azimuth

    # Find catch points
    left_result = _find_catch_point(
        sections, station, design_cl_elev, template, "left",
        tolerance, max_iterations,
    )
    right_result = _find_catch_point(
        sections, station, design_cl_elev, template, "right",
        tolerance, max_iterations,
    )

    def _offset_to_point(off: float, elev: float) -> Point:
        """Convert an offset to a 3D point using the tangent azimuth."""
        perp_az = tangent_az + math.pi / 2
        return Point(
            northing=cl_point.northing + off * math.cos(perp_az),
            easting=cl_point.easting + off * math.sin(perp_az),
            elevation=elev,
        )

    l_off, l_ground, l_design, l_conv, l_iter = left_result
    r_off, r_ground, r_design, r_conv, r_iter = right_result

    left_pt = _offset_to_point(l_off, l_ground)
    right_pt = _offset_to_point(r_off, r_ground)

    left = SlopeStakePoint(
        station=station,
        offset=l_off,
        ground_elevation=l_ground,
        design_elevation=l_design,
        cut_fill=l_ground - l_design,
        point=left_pt,
        converged=l_conv,
        iterations=l_iter,
    )
    right = SlopeStakePoint(
        station=station,
        offset=r_off,
        ground_elevation=r_ground,
        design_elevation=r_design,
        cut_fill=r_ground - r_design,
        point=right_pt,
        converged=r_conv,
        iterations=r_iter,
    )

    return SlopeStakeResult(
        station=station,
        left=left,
        right=right,
        centerline_point=cl_point,
        design_cl_elevation=design_cl_elev,
        ground_cl_elevation=ground_cl_elev,
    )


def slope_stake_3d_batch(
    alignment,
    sections: List[CrossSection],
    template: DesignTemplate,
    stations: List[float],
    tolerance: float = 0.001,
    max_iterations: int = 50,
) -> list[SlopeStakeResult]:
    """Compute 3D slope stakes at multiple stations.

    Args:
        alignment: 3D alignment with point_at_station() and vertical profile.
        sections: Ground cross-sections for surface interpolation.
        template: Design cross-section template.
        stations: List of station values.
        tolerance: Convergence tolerance.
        max_iterations: Maximum iterations per catch-point.

    Returns:
        List of SlopeStakeResult, one per station.
    """
    return [
        slope_stake_3d(alignment, sections, template, sta, tolerance, max_iterations)
        for sta in stations
    ]


def stake_catch_point(
    instrument: Point, catch_point: SlopeStakePoint
) -> StakeoutResult:
    """Compute stakeout data from instrument to a catch point.

    Args:
        instrument: Instrument setup point.
        catch_point: A catch point from slope staking.

    Returns:
        StakeoutResult with azimuth, distance, cut/fill, station, and offset.
    """
    inv = inverse(instrument, catch_point.point)
    return StakeoutResult(
        azimuth=inv.azimuth,
        distance=inv.horizontal_distance,
        cut_fill=catch_point.cut_fill,
        station=catch_point.station,
        offset=catch_point.offset,
    )
