"""Point primitive for coordinate geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Point:
    """A survey point with coordinates and metadata.

    Supports both 2D (northing, easting) and 3D (with elevation) points.
    """

    number: int
    northing: float
    easting: float
    elevation: float = 0.0
    description: str = ""

    @property
    def has_elevation(self) -> bool:
        """True if this point has a meaningful elevation."""
        return self.elevation != 0.0

    def distance_to(self, other: Point) -> float:
        """Compute 2D horizontal distance to another point."""
        dn = other.northing - self.northing
        de = other.easting - self.easting
        return math.hypot(dn, de)

    def distance_3d(self, other: Point) -> float:
        """Compute 3D slope distance to another point."""
        dn = other.northing - self.northing
        de = other.easting - self.easting
        dz = other.elevation - self.elevation
        return math.sqrt(dn * dn + de * de + dz * dz)

    def azimuth_to(self, other: Point) -> float:
        """Compute azimuth (in radians, from north clockwise) to another point."""
        dn = other.northing - self.northing
        de = other.easting - self.easting
        az = math.atan2(de, dn)
        if az < 0:
            az += 2 * math.pi
        return az

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (
            self.number == other.number
            and math.isclose(self.northing, other.northing, abs_tol=1e-9)
            and math.isclose(self.easting, other.easting, abs_tol=1e-9)
            and math.isclose(self.elevation, other.elevation, abs_tol=1e-9)
            and self.description == other.description
        )

    def __hash__(self) -> int:
        return hash(self.number)

    def __repr__(self) -> str:
        return (
            f"Point({self.number}, N={self.northing:.4f}, "
            f"E={self.easting:.4f}, Z={self.elevation:.4f}, '{self.description}')"
        )
