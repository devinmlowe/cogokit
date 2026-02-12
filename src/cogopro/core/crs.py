"""Coordinate Reference System (CRS) abstraction layer.

Provides a lightweight CRS type for tracking datum/projection on Jobs and
transforming points between geodetic (lat/lon) and UTM grid coordinate systems.

The actual projection math is delegated to :mod:`cogopro.geodetic.projections`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cogopro.core.job import Job
    from cogopro.geodetic.ellipsoid import Ellipsoid

from cogopro.core.point import Point


def _wgs84() -> Ellipsoid:
    from cogopro.geodetic.ellipsoid import WGS84
    return WGS84


def _grs80() -> Ellipsoid:
    from cogopro.geodetic.ellipsoid import GRS80
    return GRS80


@dataclass(frozen=True)
class CRS:
    """A coordinate reference system — either geodetic (lat/lon) or UTM (grid).

    Use the factory class methods :meth:`geodetic` and :meth:`utm` to create
    instances rather than calling the constructor directly.

    Attributes:
        kind: ``"geodetic"`` or ``"utm"``.
        ellipsoid: Reference ellipsoid.
        zone: UTM zone number (only for UTM CRS, ``None`` for geodetic).
        hemisphere: ``"N"`` or ``"S"`` (only for UTM CRS, ``None`` for geodetic).
    """

    kind: str
    ellipsoid: Any = field(default=None)
    zone: int | None = None
    hemisphere: str | None = None

    def __post_init__(self) -> None:
        if self.ellipsoid is None:
            object.__setattr__(self, "ellipsoid", _wgs84())

    # ---- Factory methods ----

    @classmethod
    def geodetic(cls, ellipsoid: Ellipsoid | None = None) -> CRS:
        """Create a geodetic (latitude/longitude) CRS.

        Points in a geodetic CRS store northing = latitude (radians) and
        easting = longitude (radians).
        """
        return cls(kind="geodetic", ellipsoid=ellipsoid or _wgs84())

    @classmethod
    def utm(
        cls, zone: int, hemisphere: str = "N", ellipsoid: Ellipsoid | None = None
    ) -> CRS:
        """Create a UTM (Universal Transverse Mercator) CRS.

        Points in a UTM CRS store northing and easting in metres.
        """
        return cls(kind="utm", zone=zone, hemisphere=hemisphere,
                   ellipsoid=ellipsoid or _wgs84())


# ---- Predefined constants (lazy via property pattern) ----

WGS84_GEO: CRS
NAD83_GEO: CRS


def __getattr__(name: str) -> CRS:
    if name == "WGS84_GEO":
        return CRS.geodetic(ellipsoid=_wgs84())
    if name == "NAD83_GEO":
        return CRS.geodetic(ellipsoid=_grs80())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---- Transformation functions ----

def transform_point(point: Point, from_crs: CRS, to_crs: CRS) -> Point:
    """Transform a single point between coordinate reference systems.

    Parameters:
        point: The source point.
        from_crs: The CRS the point is currently in.
        to_crs: The target CRS.

    Returns:
        A new :class:`Point` with transformed coordinates.  Elevation, point
        number, and description are preserved.
    """
    from cogopro.geodetic.projections import geodetic_to_utm, utm_to_geodetic

    if from_crs == to_crs:
        return Point(
            northing=point.northing,
            easting=point.easting,
            elevation=point.elevation,
            number=point.number,
            description=point.description,
        )

    # Route: convert source to geodetic first, then to target
    if from_crs.kind == "geodetic":
        lat, lon = point.northing, point.easting
    elif from_crs.kind == "utm":
        inv = utm_to_geodetic(
            point.easting, point.northing,
            zone=from_crs.zone,
            hemisphere=from_crs.hemisphere,
            ellipsoid=from_crs.ellipsoid,
        )
        lat, lon = inv.lat, inv.lon
    else:
        raise ValueError(f"Unsupported source CRS kind: {from_crs.kind!r}")

    # Convert from geodetic to target
    if to_crs.kind == "geodetic":
        new_northing, new_easting = lat, lon
    elif to_crs.kind == "utm":
        fwd = geodetic_to_utm(lat, lon, zone=to_crs.zone, ellipsoid=to_crs.ellipsoid)
        new_northing, new_easting = fwd.northing, fwd.easting
    else:
        raise ValueError(f"Unsupported target CRS kind: {to_crs.kind!r}")

    return Point(
        northing=new_northing,
        easting=new_easting,
        elevation=point.elevation,
        number=point.number,
        description=point.description,
    )


def transform_job(job: Job, to_crs: CRS, *, from_crs: CRS | None = None) -> Job:
    """Transform all points in a job to a new coordinate reference system.

    Parameters:
        job: The source job.
        to_crs: The target CRS.
        from_crs: Explicit source CRS.  If ``None``, uses ``job.crs``.

    Returns:
        A new :class:`Job` with transformed points and updated ``crs``.

    Raises:
        ValueError: If no source CRS is available (job.crs is None and
            from_crs not provided).
    """
    from cogopro.core.job import Job as JobClass

    source_crs = from_crs if from_crs is not None else job.crs
    if source_crs is None:
        raise ValueError(
            "No source CRS available. Set job.crs or provide from_crs parameter."
        )

    new_job = JobClass(
        name=job.name,
        description=job.description,
        linear_unit=job.linear_unit,
        angular_unit=job.angular_unit,
    )
    new_job.crs = to_crs

    for pt in job.points():
        new_job.add_point(transform_point(pt, source_crs, to_crs))

    return new_job
