"""High-level coordinate conversion interface for grid <-> geodetic."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogokit.core import Point
from cogokit.geodetic.ellipsoid import Ellipsoid, WGS84
from cogokit.geodetic.projections import (
    geodetic_to_utm,
    utm_to_geodetic,
)


@dataclass
class GridCoordinate:
    """Grid (projected) coordinate with metadata."""

    easting: float
    northing: float
    zone: int | None = None
    hemisphere: str = "N"
    convergence: float = 0.0
    scale: float = 1.0

    def to_point(self, number: int | None = None, description: str = "") -> Point:
        """Convert to a core.Point (northing, easting)."""
        return Point(
            northing=self.northing,
            easting=self.easting,
            number=number,
            description=description,
        )

    @classmethod
    def from_point(
        cls,
        point: Point,
        zone: int | None = None,
        hemisphere: str = "N",
    ) -> GridCoordinate:
        """Create a GridCoordinate from a core.Point."""
        return cls(
            easting=point.easting,
            northing=point.northing,
            zone=zone,
            hemisphere=hemisphere,
        )


@dataclass
class GeodeticCoordinate:
    """Geodetic (geographic) coordinate."""

    lat: float  # radians
    lon: float  # radians

    @property
    def lat_deg(self) -> float:
        return math.degrees(self.lat)

    @property
    def lon_deg(self) -> float:
        return math.degrees(self.lon)

    @classmethod
    def from_degrees(cls, lat_deg: float, lon_deg: float) -> GeodeticCoordinate:
        return cls(math.radians(lat_deg), math.radians(lon_deg))


def geodetic_to_grid(
    coord: GeodeticCoordinate,
    zone: int | None = None,
    ellipsoid: Ellipsoid = WGS84,
) -> GridCoordinate:
    """Convert geodetic coordinate to UTM grid coordinate.

    Parameters:
        coord: Geodetic coordinate (lat/lon in radians).
        zone: UTM zone (auto-detected if None).
        ellipsoid: Reference ellipsoid.

    Returns:
        GridCoordinate with easting, northing, zone, hemisphere, convergence, scale.
    """
    result = geodetic_to_utm(coord.lat, coord.lon, zone=zone, ellipsoid=ellipsoid)
    return GridCoordinate(
        easting=result.easting,
        northing=result.northing,
        zone=result.zone,
        hemisphere=result.hemisphere,
        convergence=result.convergence,
        scale=result.scale,
    )


def grid_to_geodetic(
    coord: GridCoordinate,
    ellipsoid: Ellipsoid = WGS84,
) -> GeodeticCoordinate:
    """Convert UTM grid coordinate to geodetic coordinate.

    Parameters:
        coord: Grid coordinate with easting, northing, zone, hemisphere.
        ellipsoid: Reference ellipsoid.

    Returns:
        GeodeticCoordinate with lat/lon in radians.

    Raises:
        ValueError: If zone is not set on the grid coordinate.
    """
    if coord.zone is None:
        raise ValueError("UTM zone must be set on the grid coordinate.")

    result = utm_to_geodetic(
        coord.easting, coord.northing,
        zone=coord.zone,
        hemisphere=coord.hemisphere,
        ellipsoid=ellipsoid,
    )
    return GeodeticCoordinate(result.lat, result.lon)


def geodetic_to_ecef(
    lat: float,
    lon: float,
    h: float,
    ellipsoid: Ellipsoid = WGS84,
) -> tuple[float, float, float]:
    """Convert geodetic coordinates to ECEF (Earth-Centered, Earth-Fixed).

    Parameters:
        lat: Geodetic latitude in radians.
        lon: Geodetic longitude in radians.
        h: Ellipsoidal height in metres.
        ellipsoid: Reference ellipsoid.

    Returns:
        Tuple (X, Y, Z) in metres.
    """
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    N = ellipsoid.N(lat)

    X = (N + h) * cos_lat * cos_lon
    Y = (N + h) * cos_lat * sin_lon
    Z = (N * (1.0 - ellipsoid.e2) + h) * sin_lat

    return X, Y, Z


def ecef_to_geodetic(
    x: float,
    y: float,
    z: float,
    ellipsoid: Ellipsoid = WGS84,
) -> tuple[float, float, float]:
    """Convert ECEF (X, Y, Z) to geodetic coordinates using Bowring's iterative method.

    Parameters:
        x: ECEF X coordinate in metres.
        y: ECEF Y coordinate in metres.
        z: ECEF Z coordinate in metres.
        ellipsoid: Reference ellipsoid.

    Returns:
        Tuple (lat, lon, h) where lat/lon are in radians and h is in metres.
    """
    a = ellipsoid.a
    b = ellipsoid.b
    e2 = ellipsoid.e2
    ep2 = ellipsoid.ep2

    lon = math.atan2(y, x)

    p = math.hypot(x, y)

    # Initial estimate using Bowring's formula
    theta = math.atan2(z * a, p * b)
    lat = math.atan2(
        z + ep2 * b * math.sin(theta) ** 3,
        p - e2 * a * math.cos(theta) ** 3,
    )

    # Iterate to convergence
    for _ in range(10):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
        lat_new = math.atan2(z + e2 * N * sin_lat, p)
        if abs(lat_new - lat) < 1e-14:
            lat = lat_new
            break
        lat = lat_new

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    N = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)

    if abs(cos_lat) > 1e-10:
        h = p / cos_lat - N
    else:
        h = abs(z) / abs(sin_lat) - N * (1.0 - e2)

    return lat, lon, h


def combined_scale_factor(
    grid_scale: float,
    elevation: float,
    ellipsoid_radius: float = 6_371_000.0,
) -> float:
    """Compute the combined (grid + elevation) scale factor.

    Parameters:
        grid_scale: Grid scale factor at the point (from projection).
        elevation: Elevation above the ellipsoid in metres.
        ellipsoid_radius: Approximate mean radius of the ellipsoid (default ~6371 km).

    Returns:
        Combined scale factor = grid_scale * elevation_factor.
    """
    elevation_factor = ellipsoid_radius / (ellipsoid_radius + elevation)
    return grid_scale * elevation_factor


def ground_to_grid(
    ground_distance: float,
    grid_scale: float,
    elevation: float = 0.0,
    ellipsoid_radius: float = 6_371_000.0,
) -> float:
    """Convert a ground distance to grid distance using the combined scale factor.

    Parameters:
        ground_distance: Distance measured on the ground in metres.
        grid_scale: Grid scale factor at the point.
        elevation: Elevation above the ellipsoid in metres.
        ellipsoid_radius: Approximate mean radius.

    Returns:
        Grid distance in metres.
    """
    csf = combined_scale_factor(grid_scale, elevation, ellipsoid_radius)
    return ground_distance * csf


def grid_to_ground(
    grid_distance: float,
    grid_scale: float,
    elevation: float = 0.0,
    ellipsoid_radius: float = 6_371_000.0,
) -> float:
    """Convert a grid distance to ground distance using the combined scale factor.

    Parameters:
        grid_distance: Grid distance in metres.
        grid_scale: Grid scale factor at the point.
        elevation: Elevation above the ellipsoid in metres.
        ellipsoid_radius: Approximate mean radius.

    Returns:
        Ground distance in metres.
    """
    csf = combined_scale_factor(grid_scale, elevation, ellipsoid_radius)
    return grid_distance / csf
