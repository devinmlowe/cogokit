"""Transverse Mercator projection and UTM coordinate conversions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogopro.geodetic.ellipsoid import Ellipsoid, WGS84


@dataclass
class TMResult:
    """Result of a Transverse Mercator forward projection."""

    easting: float
    northing: float
    convergence: float  # grid convergence in radians
    scale: float  # point scale factor


@dataclass
class TMInverseResult:
    """Result of a Transverse Mercator inverse projection."""

    lat: float  # geodetic latitude in radians
    lon: float  # geodetic longitude in radians
    convergence: float  # grid convergence in radians
    scale: float  # point scale factor


@dataclass
class UTMResult:
    """Result of a geodetic-to-UTM conversion."""

    easting: float
    northing: float
    zone: int
    hemisphere: str  # "N" or "S"
    convergence: float
    scale: float


def _meridian_arc(lat: float, e2: float, a: float) -> float:
    """Compute the meridian arc distance from equator to *lat* using a series expansion."""
    n = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
    n2 = n * n
    n3 = n2 * n
    n4 = n3 * n

    A0 = 1.0 + n2 / 4.0 + n4 / 64.0
    A2 = 3.0 / 2.0 * (n - n3 / 8.0)
    A4 = 15.0 / 16.0 * (n2 - n4 / 4.0)
    A6 = 35.0 / 48.0 * n3
    A8 = 315.0 / 512.0 * n4

    return (
        a / (1.0 + n) * (
            A0 * lat
            - A2 * math.sin(2.0 * lat)
            + A4 * math.sin(4.0 * lat)
            - A6 * math.sin(6.0 * lat)
            + A8 * math.sin(8.0 * lat)
        )
    )


def _footpoint_latitude(northing: float, e2: float, a: float) -> float:
    """Compute the footpoint latitude from northing using iterative inversion of meridian arc."""
    n = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
    n2 = n * n
    n3 = n2 * n
    n4 = n3 * n

    # Inverse series (Karney / Helmert)
    B2 = 3.0 / 2.0 * n - 27.0 / 32.0 * n3
    B4 = 21.0 / 16.0 * n2 - 55.0 / 32.0 * n4
    B6 = 151.0 / 96.0 * n3
    B8 = 1097.0 / 512.0 * n4

    A0 = 1.0 + n2 / 4.0 + n4 / 64.0
    mu = northing / (a / (1.0 + n) * A0)

    return (
        mu
        + B2 * math.sin(2.0 * mu)
        + B4 * math.sin(4.0 * mu)
        + B6 * math.sin(6.0 * mu)
        + B8 * math.sin(8.0 * mu)
    )


def tm_forward(
    lat: float,
    lon: float,
    lon0: float,
    k0: float = 1.0,
    false_easting: float = 0.0,
    false_northing: float = 0.0,
    ellipsoid: Ellipsoid = WGS84,
) -> TMResult:
    """Transverse Mercator forward projection (Redfearn's formulae).

    Parameters:
        lat: Geodetic latitude in radians.
        lon: Geodetic longitude in radians.
        lon0: Central meridian in radians.
        k0: Scale factor on central meridian (default 1.0).
        false_easting: False easting in metres.
        false_northing: False northing in metres.
        ellipsoid: Reference ellipsoid.

    Returns:
        TMResult with easting, northing, convergence, and scale factor.
    """
    a = ellipsoid.a
    e2 = ellipsoid.e2
    ep2 = ellipsoid.ep2

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    tan_lat = math.tan(lat)

    N = ellipsoid.N(lat)
    T = tan_lat * tan_lat
    C = ep2 * cos_lat * cos_lat
    dl = lon - lon0

    # Meridian arc
    M = _meridian_arc(lat, e2, a)

    # Powers of dl * cos(lat)
    p = dl * cos_lat
    p2 = p * p
    p4 = p2 * p2

    # Easting (Redfearn's series to 6th order)
    E = k0 * N * (
        p
        + p * p2 / 6.0 * (1.0 - T + C)
        + p * p4 / 120.0 * (5.0 - 18.0 * T + T * T + 72.0 * C - 58.0 * ep2)
    ) + false_easting

    # Northing
    Nval = k0 * (
        M
        + N * tan_lat * (
            p2 / 2.0
            + p4 / 24.0 * (5.0 - T + 9.0 * C + 4.0 * C * C)
            + p2 * p4 / 720.0 * (61.0 - 58.0 * T + T * T + 600.0 * C - 330.0 * ep2)
        )
    ) + false_northing

    # Grid convergence (series)
    conv = (
        tan_lat * p * (
            1.0
            + p2 / 3.0 * (1.0 - T + C)
            + p4 / 15.0 * (2.0 - 5.0 * T + T * T + 3.0 * C + 4.0 * C * C)
        )
    )

    # Point scale factor
    scale = k0 * (
        1.0
        + p2 / 2.0 * (1.0 + C)
        + p4 / 24.0 * (5.0 - 4.0 * T + 42.0 * C + 13.0 * C * C - 28.0 * ep2)
    )

    return TMResult(E, Nval, conv, scale)


def tm_inverse(
    easting: float,
    northing: float,
    lon0: float,
    k0: float = 1.0,
    false_easting: float = 0.0,
    false_northing: float = 0.0,
    ellipsoid: Ellipsoid = WGS84,
) -> TMInverseResult:
    """Transverse Mercator inverse projection (Redfearn's formulae).

    Parameters:
        easting: Grid easting in metres.
        northing: Grid northing in metres.
        lon0: Central meridian in radians.
        k0: Scale factor on central meridian.
        false_easting: False easting in metres.
        false_northing: False northing in metres.
        ellipsoid: Reference ellipsoid.

    Returns:
        TMInverseResult with lat, lon (radians), convergence, and scale.
    """
    a = ellipsoid.a
    e2 = ellipsoid.e2
    ep2 = ellipsoid.ep2

    x = (easting - false_easting) / k0
    y = (northing - false_northing) / k0

    # Footpoint latitude
    lat_fp = _footpoint_latitude(y, e2, a)

    sin_fp = math.sin(lat_fp)
    cos_fp = math.cos(lat_fp)
    tan_fp = math.tan(lat_fp)

    N_fp = ellipsoid.N(lat_fp)
    M_fp = ellipsoid.M(lat_fp)
    T_fp = tan_fp * tan_fp
    C_fp = ep2 * cos_fp * cos_fp
    D = x / N_fp
    D2 = D * D
    D4 = D2 * D2

    # Latitude
    lat = lat_fp - (N_fp * tan_fp / M_fp) * (
        D2 / 2.0
        - D4 / 24.0 * (5.0 + 3.0 * T_fp + 10.0 * C_fp - 4.0 * C_fp * C_fp - 9.0 * ep2)
        + D2 * D4 / 720.0 * (61.0 + 90.0 * T_fp + 298.0 * C_fp + 45.0 * T_fp * T_fp
                               - 252.0 * ep2 - 3.0 * C_fp * C_fp)
    )

    # Longitude
    lon = lon0 + (
        D
        - D * D2 / 6.0 * (1.0 + 2.0 * T_fp + C_fp)
        + D * D4 / 120.0 * (5.0 - 2.0 * C_fp + 28.0 * T_fp - 3.0 * C_fp * C_fp
                             + 8.0 * ep2 + 24.0 * T_fp * T_fp)
    ) / cos_fp

    # Grid convergence
    conv = tan_fp * (
        D
        - D * D2 / 3.0 * (1.0 + T_fp - C_fp - 2.0 * C_fp * C_fp)
        + D * D4 / 15.0 * (2.0 + 5.0 * T_fp + 3.0 * T_fp * T_fp)
    )

    # Point scale factor
    scale = k0 * (
        1.0
        + D2 / 2.0 * (1.0 + C_fp)
        + D4 / 24.0 * (5.0 - 4.0 * T_fp + 42.0 * C_fp + 13.0 * C_fp * C_fp - 28.0 * ep2)
    )

    return TMInverseResult(lat, lon, conv, scale)


# ---- UTM Convenience Functions ----

def utm_zone(lon_deg: float) -> int:
    """Compute the UTM zone number for a given longitude in degrees."""
    return int((lon_deg + 180.0) / 6.0) + 1


def utm_central_meridian(zone: int) -> float:
    """Central meridian (in radians) for a UTM zone."""
    return math.radians(zone * 6 - 183)


def geodetic_to_utm(
    lat: float,
    lon: float,
    zone: int | None = None,
    ellipsoid: Ellipsoid = WGS84,
) -> UTMResult:
    """Convert geodetic coordinates (radians) to UTM.

    Parameters:
        lat: Geodetic latitude in radians.
        lon: Geodetic longitude in radians.
        zone: UTM zone (auto-detected from longitude if None).
        ellipsoid: Reference ellipsoid.

    Returns:
        UTMResult with easting, northing, zone, hemisphere, convergence, scale.
    """
    lat_deg = math.degrees(lat)
    lon_deg = math.degrees(lon)

    if zone is None:
        zone = utm_zone(lon_deg)

    lon0 = utm_central_meridian(zone)
    hemisphere = "N" if lat >= 0 else "S"
    false_northing = 0.0 if lat >= 0 else 10_000_000.0

    result = tm_forward(
        lat, lon,
        lon0=lon0,
        k0=0.9996,
        false_easting=500_000.0,
        false_northing=false_northing,
        ellipsoid=ellipsoid,
    )

    return UTMResult(
        easting=result.easting,
        northing=result.northing,
        zone=zone,
        hemisphere=hemisphere,
        convergence=result.convergence,
        scale=result.scale,
    )


def utm_to_geodetic(
    easting: float,
    northing: float,
    zone: int,
    hemisphere: str = "N",
    ellipsoid: Ellipsoid = WGS84,
) -> TMInverseResult:
    """Convert UTM coordinates to geodetic (radians).

    Parameters:
        easting: UTM easting in metres.
        northing: UTM northing in metres.
        zone: UTM zone number.
        hemisphere: "N" or "S".
        ellipsoid: Reference ellipsoid.

    Returns:
        TMInverseResult with lat, lon (radians), convergence, scale.
    """
    lon0 = utm_central_meridian(zone)
    false_northing = 0.0 if hemisphere.upper() == "N" else 10_000_000.0

    return tm_inverse(
        easting, northing,
        lon0=lon0,
        k0=0.9996,
        false_easting=500_000.0,
        false_northing=false_northing,
        ellipsoid=ellipsoid,
    )
