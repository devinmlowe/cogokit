"""3D alignment definition: horizontal geometry, vertical profile, and combined."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cogopro.core.point import Point
from cogopro.solvers.vertical_curve import elevation_at as vc_elevation_at


# ---------------------------------------------------------------------------
# Horizontal alignment elements
# ---------------------------------------------------------------------------

@dataclass
class AlignmentElement:
    """Base for horizontal alignment elements."""

    start_station: float
    length: float

    @property
    def end_station(self) -> float:
        return self.start_station + self.length

    def point_at(self, station: float) -> Point:
        raise NotImplementedError


@dataclass
class Tangent(AlignmentElement):
    """Straight-line alignment element.

    Attributes:
        azimuth: Direction in radians, clockwise from north.
        start_point: Coordinate at start_station.
    """

    azimuth: float = 0.0
    start_point: Point = field(
        default_factory=lambda: Point(northing=0.0, easting=0.0)
    )

    def point_at(self, station: float) -> Point:
        dist = station - self.start_station
        n = self.start_point.northing + dist * math.cos(self.azimuth)
        e = self.start_point.easting + dist * math.sin(self.azimuth)
        return Point(northing=n, easting=e)


@dataclass
class CircularCurve(AlignmentElement):
    """Circular arc alignment element.

    Attributes:
        radius: Curve radius.
        delta: Total central angle in radians.
        direction: ``'L'`` for left, ``'R'`` for right.
        pc_point: Point of Curvature (start of arc).
        center_point: Center of the circular arc.
        start_azimuth: Forward azimuth at the PC in radians.
    """

    radius: float = 0.0
    delta: float = 0.0
    direction: str = "R"
    pc_point: Point = field(
        default_factory=lambda: Point(northing=0.0, easting=0.0)
    )
    center_point: Point = field(
        default_factory=lambda: Point(northing=0.0, easting=0.0)
    )
    start_azimuth: float = 0.0

    def point_at(self, station: float) -> Point:
        arc_dist = station - self.start_station
        sweep = arc_dist / self.radius

        # Radial azimuth from center to PC
        az_to_pc = math.atan2(
            self.pc_point.easting - self.center_point.easting,
            self.pc_point.northing - self.center_point.northing,
        )

        if self.direction == "R":
            az_to_point = az_to_pc + sweep
        else:
            az_to_point = az_to_pc - sweep

        n = self.center_point.northing + self.radius * math.cos(az_to_point)
        e = self.center_point.easting + self.radius * math.sin(az_to_point)
        return Point(northing=n, easting=e)


# ---------------------------------------------------------------------------
# Horizontal alignment
# ---------------------------------------------------------------------------

class HorizontalAlignment:
    """Ordered collection of tangents and curves."""

    def __init__(self, elements: list[AlignmentElement]) -> None:
        self.elements = elements

    @property
    def total_length(self) -> float:
        return sum(e.length for e in self.elements)

    def station_to_point(self, station: float) -> Point:
        for elem in self.elements:
            if elem.start_station <= station <= elem.end_station:
                return elem.point_at(station)
        raise ValueError(f"Station {station} is outside alignment range")

    def point_to_station_offset(self, point: Point) -> tuple[float, float]:
        """Project *point* onto the nearest element.

        Returns ``(station, offset)`` where a positive offset is to the
        **right** of the alignment direction of travel.
        """
        best_station: float | None = None
        best_offset: float = 0.0
        best_dist: float = float("inf")

        for elem in self.elements:
            sta, off = self._project(elem, point)
            clamped = max(elem.start_station, min(elem.end_station, sta))
            pt_on = elem.point_at(clamped)
            dist = math.hypot(
                point.northing - pt_on.northing,
                point.easting - pt_on.easting,
            )
            if dist < best_dist:
                best_dist = dist
                best_station = clamped
                best_offset = self._signed_offset(elem, point)

        assert best_station is not None
        return (best_station, best_offset)

    # -- projection helpers --------------------------------------------------

    @staticmethod
    def _project(elem: AlignmentElement, point: Point) -> tuple[float, float]:
        if isinstance(elem, Tangent):
            return HorizontalAlignment._project_tangent(elem, point)
        if isinstance(elem, CircularCurve):
            return HorizontalAlignment._project_curve(elem, point)
        raise TypeError(f"Unknown element type: {type(elem)}")

    @staticmethod
    def _project_tangent(
        elem: Tangent, point: Point
    ) -> tuple[float, float]:
        dn = point.northing - elem.start_point.northing
        de = point.easting - elem.start_point.easting
        along = dn * math.cos(elem.azimuth) + de * math.sin(elem.azimuth)
        perp = -dn * math.sin(elem.azimuth) + de * math.cos(elem.azimuth)
        return (elem.start_station + along, perp)

    @staticmethod
    def _project_curve(
        elem: CircularCurve, point: Point
    ) -> tuple[float, float]:
        az_to_point = math.atan2(
            point.easting - elem.center_point.easting,
            point.northing - elem.center_point.northing,
        )
        az_to_pc = math.atan2(
            elem.pc_point.easting - elem.center_point.easting,
            elem.pc_point.northing - elem.center_point.northing,
        )

        if elem.direction == "R":
            sweep = (az_to_point - az_to_pc) % (2 * math.pi)
        else:
            sweep = (az_to_pc - az_to_point) % (2 * math.pi)

        station = elem.start_station + sweep * elem.radius
        dist_from_center = math.hypot(
            point.northing - elem.center_point.northing,
            point.easting - elem.center_point.easting,
        )
        if elem.direction == "R":
            offset = elem.radius - dist_from_center
        else:
            offset = dist_from_center - elem.radius

        return (station, offset)

    @staticmethod
    def _signed_offset(elem: AlignmentElement, point: Point) -> float:
        if isinstance(elem, Tangent):
            dn = point.northing - elem.start_point.northing
            de = point.easting - elem.start_point.easting
            return -dn * math.sin(elem.azimuth) + de * math.cos(elem.azimuth)
        if isinstance(elem, CircularCurve):
            dist_from_center = math.hypot(
                point.northing - elem.center_point.northing,
                point.easting - elem.center_point.easting,
            )
            if elem.direction == "R":
                return elem.radius - dist_from_center
            return dist_from_center - elem.radius
        raise TypeError(f"Unknown element type: {type(elem)}")


# ---------------------------------------------------------------------------
# Vertical profile
# ---------------------------------------------------------------------------

@dataclass
class GradeBreak:
    """A station/elevation pair with an optional vertical curve length."""

    station: float
    elevation: float
    curve_length: float = 0.0


class VerticalProfile:
    """Elevation profile defined by tangent grades and parabolic curves."""

    def __init__(self, grade_breaks: list[GradeBreak]) -> None:
        self.grade_breaks = sorted(grade_breaks, key=lambda gb: gb.station)

    def _grades(self) -> list[float]:
        """Decimal grade for each segment between consecutive breaks."""
        breaks = self.grade_breaks
        return [
            (breaks[i + 1].elevation - breaks[i].elevation)
            / (breaks[i + 1].station - breaks[i].station)
            for i in range(len(breaks) - 1)
        ]

    def elevation_at(self, station: float) -> float:
        breaks = self.grade_breaks
        grades = self._grades()

        # Check vertical curves at interior PVIs first
        for i in range(1, len(breaks) - 1):
            L = breaks[i].curve_length
            if L <= 0:
                continue
            pvi_sta = breaks[i].station
            G1 = grades[i - 1]
            G2 = grades[i]
            bvc_sta = pvi_sta - L / 2
            evc_sta = pvi_sta + L / 2
            if bvc_sta <= station <= evc_sta:
                bvc_elev = breaks[i].elevation - G1 * (L / 2)
                x = station - bvc_sta
                return vc_elevation_at(bvc_elev, G1, G2, L, x)

        # Tangent grade segment
        for i in range(len(breaks) - 1):
            if breaks[i].station <= station <= breaks[i + 1].station:
                return breaks[i].elevation + grades[i] * (
                    station - breaks[i].station
                )

        # Extrapolate beyond alignment ends
        if station <= breaks[0].station:
            return breaks[0].elevation + grades[0] * (
                station - breaks[0].station
            )
        return breaks[-1].elevation + grades[-1] * (
            station - breaks[-1].station
        )


# ---------------------------------------------------------------------------
# Combined 3-D alignment
# ---------------------------------------------------------------------------

class Alignment:
    """Horizontal alignment paired with a vertical profile."""

    def __init__(
        self,
        horizontal: HorizontalAlignment,
        vertical: VerticalProfile,
    ) -> None:
        self.horizontal = horizontal
        self.vertical = vertical

    def point_at_station(self, station: float) -> Point:
        pt = self.horizontal.station_to_point(station)
        elev = self.vertical.elevation_at(station)
        return Point(northing=pt.northing, easting=pt.easting, elevation=elev)

    def station_offset(
        self, point: Point
    ) -> tuple[float, float, float]:
        """Return ``(station, offset, design_elevation)``."""
        sta, off = self.horizontal.point_to_station_offset(point)
        design_elev = self.vertical.elevation_at(sta)
        return (sta, off, design_elev)
