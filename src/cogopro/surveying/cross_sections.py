"""Cross-section analysis and earthwork volume computations.

Provides tools for computing cut/fill areas from ground cross-sections
and design templates, and for calculating earthwork volumes using
average-end-area and prismoidal methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class CrossSectionPoint:
    """A single point on a cross-section profile.

    Attributes:
        offset: Distance from centerline (negative = left, positive = right).
        elevation: Elevation at this offset.
    """

    offset: float
    elevation: float


@dataclass
class CrossSection:
    """A ground cross-section at a given station.

    Attributes:
        station: Station value along the alignment.
        points: List of measured cross-section points.
        centerline_elevation: Elevation at the centerline (offset = 0).
    """

    station: float
    points: List[CrossSectionPoint] = field(default_factory=list)
    centerline_elevation: float = 0.0

    @property
    def sorted_points(self) -> List[CrossSectionPoint]:
        """Return points sorted by offset (left to right)."""
        return sorted(self.points, key=lambda p: p.offset)


@dataclass
class DesignTemplate:
    """A design template expressed as offset/elevation pairs.

    Elevations are relative to the design centerline elevation.
    """

    points: List[CrossSectionPoint] = field(default_factory=list)


def _interpolate_profile(
    points: List[CrossSectionPoint], offsets: List[float]
) -> List[float]:
    """Linearly interpolate a profile at the given offsets.

    Points outside the profile range are extrapolated using the nearest
    edge segment.
    """
    sorted_pts = sorted(points, key=lambda p: p.offset)
    elevations: List[float] = []
    for x in offsets:
        # Find bracketing segment
        if x <= sorted_pts[0].offset:
            # Clamp to first point elevation (or extrapolate with first segment)
            if len(sorted_pts) >= 2:
                p0, p1 = sorted_pts[0], sorted_pts[1]
                if p1.offset != p0.offset:
                    t = (x - p0.offset) / (p1.offset - p0.offset)
                    elevations.append(p0.elevation + t * (p1.elevation - p0.elevation))
                else:
                    elevations.append(p0.elevation)
            else:
                elevations.append(sorted_pts[0].elevation)
        elif x >= sorted_pts[-1].offset:
            if len(sorted_pts) >= 2:
                p0, p1 = sorted_pts[-2], sorted_pts[-1]
                if p1.offset != p0.offset:
                    t = (x - p0.offset) / (p1.offset - p0.offset)
                    elevations.append(p0.elevation + t * (p1.elevation - p0.elevation))
                else:
                    elevations.append(p1.elevation)
            else:
                elevations.append(sorted_pts[-1].elevation)
        else:
            # Find the bracketing pair
            for i in range(len(sorted_pts) - 1):
                if sorted_pts[i].offset <= x <= sorted_pts[i + 1].offset:
                    p0, p1 = sorted_pts[i], sorted_pts[i + 1]
                    if p1.offset != p0.offset:
                        t = (x - p0.offset) / (p1.offset - p0.offset)
                        elevations.append(
                            p0.elevation + t * (p1.elevation - p0.elevation)
                        )
                    else:
                        elevations.append(p0.elevation)
                    break
    return elevations


def interpolate_surface(
    sections: List[CrossSection], station: float, offset: float
) -> float:
    """Interpolate ground elevation at an arbitrary station/offset.

    Performs bilinear interpolation: first interpolates each bracketing
    section's profile at the given offset, then linearly interpolates
    between the two results along the station axis.

    Args:
        sections: At least 2 cross-sections with measured ground points.
        station: Station value along the alignment.
        offset: Perpendicular offset from centerline.

    Returns:
        Interpolated ground elevation.

    Raises:
        ValueError: If fewer than 2 sections are provided.
    """
    if len(sections) < 2:
        raise ValueError("interpolate_surface requires at least 2 sections")

    sorted_secs = sorted(sections, key=lambda s: s.station)

    # Clamp station to section range
    if station <= sorted_secs[0].station:
        return _interpolate_profile(sorted_secs[0].sorted_points, [offset])[0]
    if station >= sorted_secs[-1].station:
        return _interpolate_profile(sorted_secs[-1].sorted_points, [offset])[0]

    # Find bracketing sections
    for i in range(len(sorted_secs) - 1):
        if sorted_secs[i].station <= station <= sorted_secs[i + 1].station:
            s0 = sorted_secs[i]
            s1 = sorted_secs[i + 1]
            break

    elev0 = _interpolate_profile(s0.sorted_points, [offset])[0]
    elev1 = _interpolate_profile(s1.sorted_points, [offset])[0]

    # Linear interpolation along station axis
    dsta = s1.station - s0.station
    if dsta == 0:
        return elev0
    t = (station - s0.station) / dsta
    return elev0 + t * (elev1 - elev0)


def section_area(
    ground: CrossSection,
    template: DesignTemplate,
    design_cl_elevation: float,
) -> Tuple[float, float]:
    """Compute cut and fill areas between ground and design profiles.

    Args:
        ground: The ground cross-section.
        template: The design template (elevations relative to design CL).
        design_cl_elevation: The design centerline elevation at this station.

    Returns:
        (cut_area, fill_area) where cut is ground above design and fill is
        ground below design.
    """
    # Build the common set of offsets from both profiles
    ground_sorted = ground.sorted_points
    design_pts = sorted(template.points, key=lambda p: p.offset)

    offset_set: set[float] = set()
    for p in ground_sorted:
        offset_set.add(p.offset)
    for p in design_pts:
        offset_set.add(p.offset)

    # Restrict to the overlap range of both profiles
    ground_min = ground_sorted[0].offset
    ground_max = ground_sorted[-1].offset
    design_min = design_pts[0].offset
    design_max = design_pts[-1].offset
    common_min = max(ground_min, design_min)
    common_max = min(ground_max, design_max)

    offsets = sorted(x for x in offset_set if common_min <= x <= common_max)

    if len(offsets) < 2:
        return (0.0, 0.0)

    # Interpolate both profiles at common offsets
    ground_elevs = _interpolate_profile(ground_sorted, offsets)
    design_elevs_relative = _interpolate_profile(design_pts, offsets)
    # Convert design relative elevations to absolute
    design_elevs = [e + design_cl_elevation for e in design_elevs_relative]

    # Compute differences (ground - design): positive = cut, negative = fill
    diffs = [g - d for g, d in zip(ground_elevs, design_elevs)]

    # Trapezoidal integration, separating cut and fill
    cut_area = 0.0
    fill_area = 0.0

    for i in range(len(offsets) - 1):
        dx = offsets[i + 1] - offsets[i]
        d0 = diffs[i]
        d1 = diffs[i + 1]

        if d0 >= 0 and d1 >= 0:
            # Entire segment is cut
            cut_area += (d0 + d1) / 2.0 * dx
        elif d0 <= 0 and d1 <= 0:
            # Entire segment is fill
            fill_area += (abs(d0) + abs(d1)) / 2.0 * dx
        else:
            # Segment crosses zero — split at the crossing point
            # Find the crossing fraction
            t = d0 / (d0 - d1)
            dx_cross = dx * t

            if d0 > 0:
                # Cut then fill
                cut_area += abs(d0) / 2.0 * dx_cross
                fill_area += abs(d1) / 2.0 * (dx - dx_cross)
            else:
                # Fill then cut
                fill_area += abs(d0) / 2.0 * dx_cross
                cut_area += abs(d1) / 2.0 * (dx - dx_cross)

    return (cut_area, fill_area)


def average_end_area(
    cut_area1: float,
    fill_area1: float,
    cut_area2: float,
    fill_area2: float,
    distance: float,
) -> Tuple[float, float]:
    """Compute earthwork volume by average-end-area method.

    Volume = ((A1 + A2) / 2) * distance

    Args:
        cut_area1: Cut area at station 1.
        fill_area1: Fill area at station 1.
        cut_area2: Cut area at station 2.
        fill_area2: Fill area at station 2.
        distance: Distance between stations.

    Returns:
        (cut_volume, fill_volume).
    """
    cut_volume = ((cut_area1 + cut_area2) / 2.0) * distance
    fill_volume = ((fill_area1 + fill_area2) / 2.0) * distance
    return (cut_volume, fill_volume)


def prismoidal_volume(
    cut_area1: float,
    fill_area1: float,
    cut_area_mid: float,
    fill_area_mid: float,
    cut_area2: float,
    fill_area2: float,
    distance: float,
) -> Tuple[float, float]:
    """Compute earthwork volume using the prismoidal formula.

    V = (distance / 6) * (A1 + 4 * Am + A2)

    Args:
        cut_area1: Cut area at station 1.
        fill_area1: Fill area at station 1.
        cut_area_mid: Cut area at midpoint.
        fill_area_mid: Fill area at midpoint.
        cut_area2: Cut area at station 2.
        fill_area2: Fill area at station 2.
        distance: Distance between stations.

    Returns:
        (cut_volume, fill_volume).
    """
    cut_vol = (distance / 6.0) * (cut_area1 + 4.0 * cut_area_mid + cut_area2)
    fill_vol = (distance / 6.0) * (fill_area1 + 4.0 * fill_area_mid + fill_area2)
    return (cut_vol, fill_vol)


def compute_earthwork(
    sections: List[CrossSection],
    template: DesignTemplate,
    design_elevations: List[float],
) -> List[dict]:
    """Compute earthwork volumes along a series of cross-sections.

    Uses the average-end-area method between consecutive sections.

    Args:
        sections: List of ground cross-sections (ordered by station).
        template: The design template to apply at each section.
        design_elevations: Design centerline elevation at each section
            (must be same length as sections).

    Returns:
        List of dicts with keys: station_from, station_to, cut_volume,
        fill_volume, cumulative_cut, cumulative_fill.
    """
    if len(sections) != len(design_elevations):
        raise ValueError(
            "sections and design_elevations must have the same length"
        )

    if len(sections) < 2:
        return []

    # Compute areas at each section
    areas: List[Tuple[float, float]] = []
    for sec, des_elev in zip(sections, design_elevations):
        areas.append(section_area(sec, template, des_elev))

    results: List[dict] = []
    cumulative_cut = 0.0
    cumulative_fill = 0.0

    for i in range(len(sections) - 1):
        distance = sections[i + 1].station - sections[i].station
        cut_vol, fill_vol = average_end_area(
            areas[i][0], areas[i][1], areas[i + 1][0], areas[i + 1][1], distance
        )
        cumulative_cut += cut_vol
        cumulative_fill += fill_vol
        results.append(
            {
                "station_from": sections[i].station,
                "station_to": sections[i + 1].station,
                "cut_volume": cut_vol,
                "fill_volume": fill_vol,
                "cumulative_cut": cumulative_cut,
                "cumulative_fill": cumulative_fill,
            }
        )

    return results


def mass_haul(earthwork: List[dict]) -> List[Tuple[float, float]]:
    """Compute mass haul ordinates from earthwork results.

    At each station, ordinate = cumulative (cut - fill).

    Args:
        earthwork: Output from compute_earthwork().

    Returns:
        List of (station, ordinate) tuples starting from the first station.
    """
    if not earthwork:
        return []

    result: List[Tuple[float, float]] = []
    # Starting station has zero ordinate
    result.append((earthwork[0]["station_from"], 0.0))

    ordinate = 0.0
    for segment in earthwork:
        ordinate += segment["cut_volume"] - segment["fill_volume"]
        result.append((segment["station_to"], ordinate))

    return result
