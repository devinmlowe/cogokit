"""3D alignment definition: horizontal geometry, vertical profile, and combined."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cogokit.core.point import Point
from cogokit.solvers.vertical_curve import elevation_at as vc_elevation_at


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


@dataclass
class Spiral(AlignmentElement):
    """Clothoid spiral transition element.

    Attributes:
        radius: Radius at the circular-curve end of the spiral.
        direction: ``'L'`` for left, ``'R'`` for right.
        start_azimuth: Forward azimuth at the start of the spiral in radians.
        start_point: Coordinate at the start of the spiral.
        entry: True if curvature increases (tangent-to-curve),
            False if curvature decreases (curve-to-tangent).
    """

    radius: float = 0.0
    direction: str = "R"
    start_azimuth: float = 0.0
    start_point: Point = field(
        default_factory=lambda: Point(northing=0.0, easting=0.0)
    )
    entry: bool = True

    def point_at(self, station: float) -> Point:
        d = station - self.start_station
        x_local, y_local = self._local_coords(d)
        sign = 1.0 if self.direction == "R" else -1.0
        y_right = sign * y_local

        az = self.start_azimuth
        n = self.start_point.northing + x_local * math.cos(az) - y_right * math.sin(az)
        e = self.start_point.easting + x_local * math.sin(az) + y_right * math.cos(az)
        return Point(northing=n, easting=e)

    @property
    def end_azimuth(self) -> float:
        """Azimuth at the end of the spiral."""
        sign = 1.0 if self.direction == "R" else -1.0
        theta_s = self.length / (2.0 * self.radius)
        return self.start_azimuth + sign * theta_s

    def azimuth_at(self, station: float) -> float:
        """Azimuth at a given station along the spiral."""
        d = station - self.start_station
        sign = 1.0 if self.direction == "R" else -1.0
        if self.entry:
            theta = d * d / (2.0 * self.radius * self.length)
        else:
            theta = d / self.radius - d * d / (2.0 * self.radius * self.length)
        return self.start_azimuth + sign * theta

    def _local_coords(self, d: float) -> tuple[float, float]:
        """Local (along-tangent, perpendicular) coords at distance *d*."""
        if self.entry:
            return self._entry_coords(d)
        return self._exit_coords(d)

    def _entry_coords(self, d: float) -> tuple[float, float]:
        """Series expansion for entry spiral (curvature 0 -> 1/R)."""
        theta = d * d / (2.0 * self.radius * self.length)
        t2 = theta * theta
        x = d * (1 - t2 / 10 + t2 * t2 / 216 - t2 * t2 * t2 / 9360)
        y = d * (
            theta / 3
            - t2 * theta / 42
            + t2 * t2 * theta / 1320
            - t2 * t2 * t2 * theta / 75600
        )
        return x, y

    def _exit_coords(self, d: float) -> tuple[float, float]:
        """Analytical exit spiral coords via entry spiral integral substitution."""
        theta_s = self.length / (2.0 * self.radius)
        x_s, y_s = self._entry_coords(self.length)
        x_r, y_r = self._entry_coords(self.length - d)
        dx = x_s - x_r
        dy = y_s - y_r
        cos_ts = math.cos(theta_s)
        sin_ts = math.sin(theta_s)
        x = cos_ts * dx + sin_ts * dy
        y = sin_ts * dx - cos_ts * dy
        return x, y


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
        if isinstance(elem, Spiral):
            return HorizontalAlignment._project_spiral(elem, point)
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
    def _project_spiral(
        elem: Spiral, point: Point
    ) -> tuple[float, float]:
        """Project onto spiral via coarse search + Newton refinement."""
        best_s = elem.start_station
        best_d = float("inf")
        for i in range(9):
            s = elem.start_station + elem.length * i / 8
            pt = elem.point_at(s)
            d = math.hypot(
                point.northing - pt.northing, point.easting - pt.easting,
            )
            if d < best_d:
                best_d = d
                best_s = s

        s = best_s
        for _ in range(20):
            pt = elem.point_at(s)
            az = elem.azimuth_at(s)
            dn = point.northing - pt.northing
            de = point.easting - pt.easting
            along = dn * math.cos(az) + de * math.sin(az)
            s += along
            s = max(elem.start_station, min(elem.end_station, s))
            if abs(along) < 1e-10:
                break

        pt = elem.point_at(s)
        az = elem.azimuth_at(s)
        dn = point.northing - pt.northing
        de = point.easting - pt.easting
        offset = -dn * math.sin(az) + de * math.cos(az)
        return s, offset

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
        if isinstance(elem, Spiral):
            sta, offset = HorizontalAlignment._project_spiral(elem, point)
            return offset
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
