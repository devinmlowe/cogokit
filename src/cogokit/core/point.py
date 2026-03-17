"""Point primitive for coordinate geometry."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .angle import Angle


@dataclass
class Point:
    """A survey point with coordinates and metadata.

    Supports both 2D (northing, easting) and 3D (with elevation) points.
    """

    northing: float
    easting: float
    elevation: float = 0.0
    number: int | None = None
    description: str = ""

    @classmethod
    def from_coords(
        cls,
        northing: float,
        easting: float,
        elevation: float = 0.0,
        number: int | None = None,
        description: str = "",
    ) -> Point:
        """Create a Point from coordinate values."""
        return cls(
            northing=northing,
            easting=easting,
            elevation=elevation,
            number=number,
            description=description,
        )

    @property
    def has_elevation(self) -> bool:
        """True if this point has a meaningful elevation."""
        return self.elevation != 0.0

    @property
    def coords_2d(self) -> tuple[float, float]:
        """Return (northing, easting) tuple."""
        return (self.northing, self.easting)

    @property
    def coords_3d(self) -> tuple[float, float, float]:
        """Return (northing, easting, elevation) tuple."""
        return (self.northing, self.easting, self.elevation)

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

    def azimuth_to(self, other: Point) -> Angle:
        """Compute azimuth (from north clockwise) to another point as an Angle."""
        dn = other.northing - self.northing
        de = other.easting - self.easting
        az = math.atan2(de, dn)
        if az < 0:
            az += 2 * math.pi
        return Angle.from_radians(az)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        # When both have numbers, include number in comparison
        if self.number is not None and other.number is not None:
            if self.number != other.number:
                return False
        return (
            math.isclose(self.northing, other.northing, abs_tol=1e-9)
            and math.isclose(self.easting, other.easting, abs_tol=1e-9)
            and math.isclose(self.elevation, other.elevation, abs_tol=1e-9)
            and self.description == other.description
        )

    def __hash__(self) -> int:
        if self.number is not None:
            return hash(self.number)
        return hash((
            round(self.northing, 9),
            round(self.easting, 9),
            round(self.elevation, 9),
        ))

    def __repr__(self) -> str:
        num = self.number if self.number is not None else "?"
        return (
            f"Point({num}, N={self.northing:.4f}, "
            f"E={self.easting:.4f}, Z={self.elevation:.4f}, '{self.description}')"
        )
