"""PROJ4 string parser.

Parses PROJ4-format projection definition strings into ProjectionDef
dataclasses for use with the projection and CRS modules.

Supports: Transverse Mercator (+proj=tmerc), Lambert Conformal Conic
(+proj=lcc), and Hotine Oblique Mercator (+proj=omerc).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from cogokit.geodetic.ellipsoid import Ellipsoid, GRS80, WGS84


_ELLIPSOID_MAP: dict[str, Ellipsoid] = {
    "GRS80": GRS80,
    "WGS84": WGS84,
}

_DATUM_ELLIPSOID_MAP: dict[str, Ellipsoid] = {
    "NAD83": GRS80,
    "WGS84": WGS84,
}

_SUPPORTED_PROJECTIONS = {"tmerc", "lcc", "omerc"}


@dataclass
class ProjectionDef:
    """Parsed projection definition from a PROJ4 string.

    Angles are stored in radians. Linear values are in metres (as given
    in the PROJ4 string — the ``units`` field records the declared unit
    for coordinate I/O purposes).

    Attributes:
        proj_type: Projection type (``"tmerc"``, ``"lcc"``, ``"omerc"``).
        lat_0: Latitude of origin in radians.
        lon_0: Central meridian / longitude of origin in radians.
        k_0: Scale factor on central meridian (1.0 for LCC).
        x_0: False easting (in the units of the PROJ4 string).
        y_0: False northing (in the units of the PROJ4 string).
        lat_1: First standard parallel in radians (LCC only).
        lat_2: Second standard parallel in radians (LCC only).
        lonc: Longitude of centre in radians (OMerc only).
        alpha: Azimuth of initial line in radians (OMerc only).
        gamma: Rectified grid angle in radians (OMerc only).
        no_uoff: No U offset flag (OMerc only).
        ellipsoid: Reference ellipsoid.
        units: Coordinate unit string (``"m"``, ``"us-ft"``, ``"ft"``).
    """

    proj_type: str
    lat_0: float = 0.0
    lon_0: float = 0.0
    k_0: float = 1.0
    x_0: float = 0.0
    y_0: float = 0.0
    lat_1: float | None = None
    lat_2: float | None = None
    lonc: float | None = None
    alpha: float | None = None
    gamma: float | None = None
    no_uoff: bool = False
    ellipsoid: Any = field(default_factory=lambda: GRS80)
    units: str = "m"


def _tokenize(proj4_str: str) -> dict[str, str | bool]:
    """Parse a PROJ4 string into a dict of key-value pairs.

    Handles both ``+key=value`` tokens and bare ``+flag`` tokens (like
    ``+no_uoff``, ``+no_defs``).
    """
    params: dict[str, str | bool] = {}
    for token in proj4_str.split():
        token = token.lstrip("+")
        if "=" in token:
            key, value = token.split("=", 1)
            params[key] = value
        else:
            params[token] = True
    return params


def parse_proj4(proj4_str: str) -> ProjectionDef:
    """Parse a PROJ4 string into a :class:`ProjectionDef`.

    Parameters:
        proj4_str: A PROJ4-format string (e.g.
            ``"+proj=tmerc +lat_0=38.83 +lon_0=-74.5 +k=0.9999 ..."``).

    Returns:
        A populated ProjectionDef dataclass.

    Raises:
        ValueError: If the string is missing ``+proj`` or uses an
            unsupported projection type.
    """
    params = _tokenize(proj4_str)

    proj = params.get("proj")
    if proj is None or proj is True:
        raise ValueError("PROJ4 string must contain +proj=<type>")
    if proj not in _SUPPORTED_PROJECTIONS:
        raise ValueError(
            f"Unsupported projection type: {proj!r}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_PROJECTIONS))}"
        )

    # Resolve ellipsoid
    ellipsoid = GRS80  # default for NAD83
    ellps = params.get("ellps")
    if ellps and ellps is not True:
        ellipsoid = _ELLIPSOID_MAP.get(ellps.upper(), GRS80)
    datum = params.get("datum")
    if datum and datum is not True:
        ellipsoid = _DATUM_ELLIPSOID_MAP.get(datum.upper(), ellipsoid)

    def _deg(key: str, default: float = 0.0) -> float:
        """Get a parameter in degrees and convert to radians."""
        val = params.get(key, default)
        if val is True:
            return math.radians(default)
        return math.radians(float(val))

    def _float(key: str, default: float = 0.0) -> float:
        val = params.get(key, default)
        if val is True:
            return default
        return float(val)

    units = "m"
    units_val = params.get("units")
    if units_val and units_val is not True:
        units = units_val

    pdef = ProjectionDef(
        proj_type=str(proj),
        lat_0=_deg("lat_0"),
        lon_0=_deg("lon_0") if "lon_0" in params else 0.0,
        k_0=_float("k", 1.0),
        x_0=_float("x_0"),
        y_0=_float("y_0"),
        ellipsoid=ellipsoid,
        units=units,
    )

    if proj == "lcc":
        pdef.lat_1 = _deg("lat_1")
        pdef.lat_2 = _deg("lat_2")

    if proj == "omerc":
        pdef.lonc = _deg("lonc")
        pdef.alpha = _deg("alpha")
        pdef.gamma = _deg("gamma")
        pdef.no_uoff = params.get("no_uoff", False) is True
        pdef.k_0 = _float("k", 1.0)

    return pdef
