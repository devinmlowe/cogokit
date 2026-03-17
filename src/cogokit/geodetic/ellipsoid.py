"""Reference ellipsoid definitions and derived geodetic parameters."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Ellipsoid:
    """A reference ellipsoid defined by semi-major axis and inverse flattening.

    Attributes:
        name: Human-readable name of the ellipsoid.
        a: Semi-major axis in metres.
        inv_f: Inverse flattening (1/f).  Use 0.0 for a sphere.
    """

    name: str
    a: float
    inv_f: float

    # --- derived scalar properties ---

    @property
    def f(self) -> float:
        """Flattening."""
        return 1.0 / self.inv_f if self.inv_f else 0.0

    @property
    def b(self) -> float:
        """Semi-minor axis."""
        return self.a * (1.0 - self.f)

    @property
    def e2(self) -> float:
        """First eccentricity squared (e^2)."""
        f = self.f
        return 2.0 * f - f * f

    @property
    def ep2(self) -> float:
        """Second eccentricity squared (e'^2)."""
        return self.e2 / (1.0 - self.e2)

    @property
    def e(self) -> float:
        """First eccentricity."""
        return math.sqrt(self.e2)

    @property
    def ep(self) -> float:
        """Second eccentricity."""
        return math.sqrt(self.ep2)

    # --- radius of curvature functions ---

    def N(self, lat: float) -> float:
        """Radius of curvature in the prime vertical (N) at geodetic latitude *lat* (radians)."""
        sin_lat = math.sin(lat)
        return self.a / math.sqrt(1.0 - self.e2 * sin_lat * sin_lat)

    def M(self, lat: float) -> float:
        """Radius of curvature in the meridian (M) at geodetic latitude *lat* (radians)."""
        sin_lat = math.sin(lat)
        denom = 1.0 - self.e2 * sin_lat * sin_lat
        return self.a * (1.0 - self.e2) / (denom * math.sqrt(denom))

    def R(self, lat: float) -> float:
        """Mean radius of curvature (geometric mean of M and N)."""
        return math.sqrt(self.M(lat) * self.N(lat))


# ---- Standard ellipsoid definitions ----

WGS84 = Ellipsoid("WGS 84", 6378137.0, 298.257223563)
GRS80 = Ellipsoid("GRS 80", 6378137.0, 298.257222101)
CLARKE_1866 = Ellipsoid("Clarke 1866", 6378206.4, 294.9786982)
INTERNATIONAL_1924 = Ellipsoid("International 1924", 6378388.0, 297.0)
BESSEL_1841 = Ellipsoid("Bessel 1841", 6377397.155, 299.1528128)
AIRY_1830 = Ellipsoid("Airy 1830", 6377563.396, 299.3249646)
AUSTRALIAN_NATIONAL = Ellipsoid("Australian National", 6378160.0, 298.25)
KRASSOVSKY_1940 = Ellipsoid("Krassovsky 1940", 6378245.0, 298.3)
EVEREST_1830 = Ellipsoid("Everest 1830", 6377276.345, 300.8017)

# NAD83 uses the GRS80 ellipsoid
NAD83 = GRS80
