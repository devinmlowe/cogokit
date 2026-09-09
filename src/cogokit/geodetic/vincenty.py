"""Vincenty direct and inverse geodesic solutions on the ellipsoid."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogokit.core import Angle
from cogokit.geodetic.ellipsoid import Ellipsoid, WGS84

_MAX_ITERATIONS = 200
_CONVERGENCE = 1e-12


@dataclass
class InverseResult:
    """Result of a Vincenty inverse computation."""

    distance: float  # geodesic distance in metres
    azimuth_forward: float  # forward azimuth in radians (0..2pi)
    azimuth_reverse: float  # reverse azimuth in radians (0..2pi)


@dataclass
class DirectResult:
    """Result of a Vincenty direct computation."""

    lat: float  # destination latitude in radians
    lon: float  # destination longitude in radians
    azimuth_reverse: float  # reverse azimuth in radians (0..2pi)


def _normalise_az(az: float) -> float:
    """Normalise an azimuth to [0, 2*pi)."""
    az %= 2.0 * math.pi
    if az < 0:
        az += 2.0 * math.pi
    return az


def vincenty_inverse(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    ellipsoid: Ellipsoid = WGS84,
) -> InverseResult:
    """Compute geodesic distance and azimuths between two points (Vincenty inverse).

    Parameters:
        lat1, lon1: Start point in radians.
        lat2, lon2: End point in radians.
        ellipsoid: Reference ellipsoid (default WGS84).

    Returns:
        InverseResult with distance (m), forward azimuth, reverse azimuth.

    Raises:
        ValueError: If the solution does not converge (near-antipodal points).
    """
    a = ellipsoid.a
    f = ellipsoid.f
    b = ellipsoid.b

    # Reduced latitudes
    U1 = math.atan((1.0 - f) * math.tan(lat1))
    U2 = math.atan((1.0 - f) * math.tan(lat2))
    sin_U1, cos_U1 = math.sin(U1), math.cos(U1)
    sin_U2, cos_U2 = math.sin(U2), math.cos(U2)

    L = lon2 - lon1
    lam = L  # initial lambda = difference in longitude

    for _ in range(_MAX_ITERATIONS):
        sin_lam = math.sin(lam)
        cos_lam = math.cos(lam)

        sin_sigma = math.sqrt(
            (cos_U2 * sin_lam) ** 2 + (cos_U1 * sin_U2 - sin_U1 * cos_U2 * cos_lam) ** 2
        )

        if sin_sigma < 1e-15:
            # Coincident points
            return InverseResult(0.0, 0.0, 0.0)

        cos_sigma = sin_U1 * sin_U2 + cos_U1 * cos_U2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)

        sin_alpha = cos_U1 * cos_U2 * sin_lam / sin_sigma
        cos2_alpha = 1.0 - sin_alpha * sin_alpha

        if cos2_alpha > 1e-15:
            cos_2sigma_m = cos_sigma - 2.0 * sin_U1 * sin_U2 / cos2_alpha
        else:
            cos_2sigma_m = 0.0  # equatorial line

        C = f / 16.0 * cos2_alpha * (4.0 + f * (4.0 - 3.0 * cos2_alpha))

        lam_prev = lam
        lam = L + (1.0 - C) * f * sin_alpha * (
            sigma + C * sin_sigma * (cos_2sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2))
        )

        if abs(lam - lam_prev) < _CONVERGENCE:
            break
    else:
        raise ValueError(
            "Vincenty inverse did not converge — points may be nearly antipodal "
            f"(lat1={math.degrees(lat1):.6f}, lon1={math.degrees(lon1):.6f}, "
            f"lat2={math.degrees(lat2):.6f}, lon2={math.degrees(lon2):.6f})"
        )

    u2 = cos2_alpha * (a * a - b * b) / (b * b)
    A_coeff = 1.0 + u2 / 16384.0 * (4096.0 + u2 * (-768.0 + u2 * (320.0 - 175.0 * u2)))
    B_coeff = u2 / 1024.0 * (256.0 + u2 * (-128.0 + u2 * (74.0 - 47.0 * u2)))

    delta_sigma = B_coeff * sin_sigma * (
        cos_2sigma_m
        + B_coeff
        / 4.0
        * (
            cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2)
            - B_coeff
            / 6.0
            * cos_2sigma_m
            * (-3.0 + 4.0 * sin_sigma**2)
            * (-3.0 + 4.0 * cos_2sigma_m**2)
        )
    )

    s = b * A_coeff * (sigma - delta_sigma)

    az_fwd = math.atan2(cos_U2 * sin_lam, cos_U1 * sin_U2 - sin_U1 * cos_U2 * cos_lam)
    # Reverse azimuth: direction at P2 back toward P1
    az_rev = math.atan2(cos_U1 * sin_lam, -sin_U1 * cos_U2 + cos_U1 * sin_U2 * cos_lam) + math.pi

    return InverseResult(s, _normalise_az(az_fwd), _normalise_az(az_rev))


def vincenty_direct(
    lat1: float,
    lon1: float,
    azimuth: float,
    distance: float,
    ellipsoid: Ellipsoid = WGS84,
) -> DirectResult:
    """Compute destination point given start, azimuth, and distance (Vincenty direct).

    Parameters:
        lat1, lon1: Start point in radians.
        azimuth: Forward azimuth in radians.
        distance: Geodesic distance in metres.
        ellipsoid: Reference ellipsoid (default WGS84).

    Returns:
        DirectResult with destination lat/lon (radians) and reverse azimuth.
    """
    a = ellipsoid.a
    f = ellipsoid.f
    b = ellipsoid.b

    sin_az = math.sin(azimuth)
    cos_az = math.cos(azimuth)

    U1 = math.atan((1.0 - f) * math.tan(lat1))
    sin_U1, cos_U1 = math.sin(U1), math.cos(U1)

    sigma1 = math.atan2(math.tan(U1), cos_az)
    sin_alpha = cos_U1 * sin_az
    cos2_alpha = 1.0 - sin_alpha * sin_alpha

    u2 = cos2_alpha * (a * a - b * b) / (b * b)
    A_coeff = 1.0 + u2 / 16384.0 * (4096.0 + u2 * (-768.0 + u2 * (320.0 - 175.0 * u2)))
    B_coeff = u2 / 1024.0 * (256.0 + u2 * (-128.0 + u2 * (74.0 - 47.0 * u2)))

    sigma = distance / (b * A_coeff)

    for _ in range(_MAX_ITERATIONS):
        cos_2sigma_m = math.cos(2.0 * sigma1 + sigma)
        sin_sigma = math.sin(sigma)
        cos_sigma = math.cos(sigma)

        delta_sigma = B_coeff * sin_sigma * (
            cos_2sigma_m
            + B_coeff
            / 4.0
            * (
                cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2)
                - B_coeff
                / 6.0
                * cos_2sigma_m
                * (-3.0 + 4.0 * sin_sigma**2)
                * (-3.0 + 4.0 * cos_2sigma_m**2)
            )
        )

        sigma_prev = sigma
        sigma = distance / (b * A_coeff) + delta_sigma

        if abs(sigma - sigma_prev) < _CONVERGENCE:
            break

    sin_sigma = math.sin(sigma)
    cos_sigma = math.cos(sigma)
    cos_2sigma_m = math.cos(2.0 * sigma1 + sigma)

    lat2 = math.atan2(
        sin_U1 * cos_sigma + cos_U1 * sin_sigma * cos_az,
        (1.0 - f) * math.sqrt(sin_alpha**2 + (sin_U1 * sin_sigma - cos_U1 * cos_sigma * cos_az) ** 2),
    )

    lam = math.atan2(
        sin_sigma * sin_az,
        cos_U1 * cos_sigma - sin_U1 * sin_sigma * cos_az,
    )

    C = f / 16.0 * cos2_alpha * (4.0 + f * (4.0 - 3.0 * cos2_alpha))

    L = lam - (1.0 - C) * f * sin_alpha * (
        sigma + C * sin_sigma * (cos_2sigma_m + C * cos_sigma * (-1.0 + 2.0 * cos_2sigma_m**2))
    )

    lon2 = lon1 + L

    # Reverse azimuth: direction at P2 back toward P1
    az_rev = math.atan2(sin_alpha, -sin_U1 * sin_sigma + cos_U1 * cos_sigma * cos_az) + math.pi

    return DirectResult(lat2, lon2, _normalise_az(az_rev))


def vincenty_inverse_from_angles(
    lat1: Angle,
    lon1: Angle,
    lat2: Angle,
    lon2: Angle,
    ellipsoid: Ellipsoid = WGS84,
) -> InverseResult:
    """Convenience wrapper for vincenty_inverse that accepts Angle objects.

    Parameters:
        lat1, lon1: Start point as Angle objects.
        lat2, lon2: End point as Angle objects.
        ellipsoid: Reference ellipsoid (default WGS84).

    Returns:
        InverseResult with distance (m), forward azimuth, reverse azimuth.
    """
    return vincenty_inverse(
        lat1.radians, lon1.radians,
        lat2.radians, lon2.radians,
        ellipsoid,
    )
