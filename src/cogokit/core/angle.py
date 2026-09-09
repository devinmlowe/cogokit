"""Angle handling with DMS, decimal-degree, radian, and bearing support."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class BearingQuadrant(Enum):
    NE = "NE"
    NW = "NW"
    SE = "SE"
    SW = "SW"


@dataclass(frozen=True)
class Angle:
    """An angle stored internally as decimal degrees.

    Supports conversion to/from DMS (degrees-minutes-seconds), radians,
    and surveyor bearings. Arithmetic operations return new Angle instances.
    """

    _degrees: float

    # --- Constructors ---

    @classmethod
    def from_degrees(cls, degrees: float) -> Angle:
        return cls(_degrees=degrees)

    @classmethod
    def from_radians(cls, radians: float) -> Angle:
        return cls(_degrees=math.degrees(radians))

    @classmethod
    def from_dms(cls, degrees: int, minutes: int, seconds: float) -> Angle:
        """Create from explicit DMS components."""
        sign = -1 if degrees < 0 else 1
        dd = abs(degrees) + minutes / 60.0 + seconds / 3600.0
        return cls(_degrees=sign * dd)

    @classmethod
    def from_hp_notation(cls, hp: float) -> Angle:
        """Create from HP-calculator packed DMS (e.g. 123.4530 = 123d45'30\").

        In this format, the integer part is degrees, the first two decimal
        digits are minutes, and the remaining digits are seconds.
        """
        sign = -1 if hp < 0 else 1
        hp = abs(hp)
        degrees = int(hp)
        fractional = hp - degrees
        minutes_raw = fractional * 100
        minutes = int(round(minutes_raw, 10))
        seconds = (minutes_raw - minutes) * 100
        dd = degrees + minutes / 60.0 + seconds / 3600.0
        return cls(_degrees=sign * dd)

    @classmethod
    def from_bearing(cls, quadrant: BearingQuadrant, degrees: float) -> Angle:
        """Create an azimuth from a surveyor bearing (e.g. N45d30'E)."""
        if quadrant == BearingQuadrant.NE:
            az = degrees
        elif quadrant == BearingQuadrant.SE:
            az = 180.0 - degrees
        elif quadrant == BearingQuadrant.SW:
            az = 180.0 + degrees
        else:  # NW
            az = 360.0 - degrees
        return cls(_degrees=az)

    @classmethod
    def from_azimuth(cls, radians: float) -> Angle:
        """Create an Angle from radians, normalized to [0, 360) degrees."""
        degrees = math.degrees(radians) % 360
        return cls(_degrees=degrees)

    # --- Properties ---

    @property
    def degrees(self) -> float:
        return self._degrees

    @property
    def radians(self) -> float:
        return math.radians(self._degrees)

    @property
    def dms(self) -> Tuple[int, int, float]:
        """Return (degrees, minutes, seconds) tuple."""
        sign = -1 if self._degrees < 0 else 1
        dd = abs(self._degrees)
        d = int(dd)
        m_raw = (dd - d) * 60
        m = int(m_raw)
        s = (m_raw - m) * 60
        # Avoid 60-second rollover from floating point
        if s >= 59.9999999:
            s = 0.0
            m += 1
        if m >= 60:
            m = 0
            d += 1
        return (sign * d, m, s)

    @property
    def hp_notation(self) -> float:
        """Return HP-calculator packed DMS (e.g. 45d30'20\" -> 45.3020)."""
        d, m, s = self.dms
        sign = -1 if d < 0 else 1
        return sign * (abs(d) + m / 100.0 + s / 10000.0)

    # --- Formatting ---

    def to_dms_string(self, precision: int = 2) -> str:
        """Format as 'DDdMM'SS.ss\"'."""
        d, m, s = self.dms
        sign = "-" if d < 0 else ""
        return f"{sign}{abs(d)}\u00b0{m:02d}'{s:0{precision + 3}.{precision}f}\""

    def to_bearing_string(self, precision: int = 0) -> str:
        """Format as surveyor bearing (e.g. 'N 45d30'00\" E')."""
        az = self._degrees % 360
        if az <= 90:
            prefix, suffix = "N", "E"
            angle = az
        elif az <= 180:
            prefix, suffix = "S", "E"
            angle = 180 - az
        elif az <= 270:
            prefix, suffix = "S", "W"
            angle = az - 180
        else:
            prefix, suffix = "N", "W"
            angle = 360 - az
        bearing_angle = Angle.from_degrees(angle)
        return f"{prefix} {bearing_angle.to_dms_string(precision)} {suffix}"

    # --- Normalization ---

    def normalize(self, lower: float = 0.0, upper: float = 360.0) -> Angle:
        """Normalize angle to [lower, upper) range."""
        span = upper - lower
        d = self._degrees
        while d < lower:
            d += span
        while d >= upper:
            d -= span
        return Angle(_degrees=d)

    # --- Arithmetic ---

    def __add__(self, other: Angle) -> Angle:
        if not isinstance(other, Angle):
            return NotImplemented
        return Angle(_degrees=self._degrees + other._degrees)

    def __sub__(self, other: Angle) -> Angle:
        if not isinstance(other, Angle):
            return NotImplemented
        return Angle(_degrees=self._degrees - other._degrees)

    def __neg__(self) -> Angle:
        return Angle(_degrees=-self._degrees)

    def __mul__(self, scalar: float) -> Angle:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Angle(_degrees=self._degrees * scalar)

    def __rmul__(self, scalar: float) -> Angle:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Angle:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Angle(_degrees=self._degrees / scalar)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Angle):
            return NotImplemented
        return math.isclose(self._degrees, other._degrees, abs_tol=1e-9)

    def __lt__(self, other: Angle) -> bool:
        if not isinstance(other, Angle):
            return NotImplemented
        return self._degrees < other._degrees

    def __le__(self, other: Angle) -> bool:
        if not isinstance(other, Angle):
            return NotImplemented
        return self._degrees <= other._degrees or self == other

    def __float__(self) -> float:
        """Return the angle in radians for float() conversion."""
        return self.radians

    def __repr__(self) -> str:
        return f"Angle({self.to_dms_string()})"
