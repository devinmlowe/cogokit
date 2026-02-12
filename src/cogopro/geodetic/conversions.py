"""High-level coordinate conversion interface for grid <-> geodetic."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogopro.core import Point
from cogopro.geodetic.ellipsoid import Ellipsoid, WGS84
from cogopro.geodetic.projections import (
    TMInverseResult,
    TMResult,
    UTMResult,
    geodetic_to_utm,
    tm_forward,
    tm_inverse,
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
