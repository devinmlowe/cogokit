"""Export formats for DXF and KML."""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from ..core.job import Job
from ..core.point import Point


def _resolve_points(points: Union[List[Point], Job]) -> List[Point]:
    """Extract a point list from either a Job or a list of Points."""
    if isinstance(points, Job):
        return points.points()
    return list(points)


def _dxf_wrap(entity_lines: list[str]) -> str:
    """Wrap entity lines in SECTION/ENTITIES + EOF."""
    lines = ["0", "SECTION", "2", "ENTITIES"]
    lines.extend(entity_lines)
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines) + "\n"


def export_dxf(
    job: Job,
    destination: Union[str, Path],
    labels: bool = True,
) -> None:
    """Export job points as a minimal DXF file (POINT + optional TEXT entities)."""
    path = Path(destination)
    entities: list[str] = []
    for p in job.points():
        entities.extend([
            "0", "POINT",
            "8", "POINTS",
            "10", f"{p.easting:.4f}",
            "20", f"{p.northing:.4f}",
            "30", f"{p.elevation:.4f}",
        ])
        if labels:
            entities.extend([
                "0", "TEXT",
                "8", "LABELS",
                "10", f"{p.easting:.4f}",
                "20", f"{p.northing:.4f}",
                "30", f"{p.elevation:.4f}",
                "40", "1.0",
                "1", str(p.number),
            ])
    path.write_text(_dxf_wrap(entities))


def export_dxf_lines(
    points: Union[List[Point], Job],
    destination: Union[str, Path],
    layer: str = "LINES",
) -> None:
    """Export LINE entities connecting sequential point pairs."""
    path = Path(destination)
    pts = _resolve_points(points)
    entities: list[str] = []
    for a, b in zip(pts, pts[1:]):
        entities.extend([
            "0", "LINE",
            "8", layer,
            "10", f"{a.easting:.4f}",
            "20", f"{a.northing:.4f}",
            "30", f"{a.elevation:.4f}",
            "11", f"{b.easting:.4f}",
            "21", f"{b.northing:.4f}",
            "31", f"{b.elevation:.4f}",
        ])
    path.write_text(_dxf_wrap(entities))


def export_dxf_polyline(
    points: Union[List[Point], Job],
    destination: Union[str, Path],
    layer: str = "POLYLINE",
    closed: bool = False,
) -> None:
    """Export an LWPOLYLINE entity containing all vertices."""
    path = Path(destination)
    pts = _resolve_points(points)
    entities: list[str] = [
        "0", "LWPOLYLINE",
        "8", layer,
        "90", str(len(pts)),
        "70", str(int(closed)),
    ]
    for p in pts:
        entities.extend([
            "10", f"{p.easting:.4f}",
            "20", f"{p.northing:.4f}",
        ])
    path.write_text(_dxf_wrap(entities))


def export_kml(
    job: Job,
    destination: Union[str, Path],
    crs: "CRS | None" = None,
) -> None:
    """Export job points as a KML file with WGS84 coordinates.

    If the job (or the *crs* override) specifies a coordinate reference system,
    points are transformed to WGS84 geodetic and written as degrees.  If no CRS
    is available, coordinates are written as-is (backward-compatible behaviour
    assuming northing=latitude degrees, easting=longitude degrees).

    KML coordinate order is: ``longitude,latitude,elevation``.

    Parameters:
        job: The job containing points to export.
        destination: Output file path.
        crs: Optional CRS override.  If provided, this is used instead of
            ``job.crs`` as the source coordinate reference system.
    """
    import math

    from ..core.crs import CRS as _CRS
    from ..core.crs import transform_point

    path = Path(destination)
    source_crs = crs if crs is not None else getattr(job, "crs", None)

    placemarks = []
    for p in job.points():
        if source_crs is not None:
            # Transform to WGS84 geodetic (radians), then convert to degrees
            wgs84_geo = _CRS.geodetic()
            geo_pt = transform_point(p, source_crs, wgs84_geo)
            lat_deg = math.degrees(geo_pt.northing)
            lon_deg = math.degrees(geo_pt.easting)
            elev = geo_pt.elevation
        else:
            # No CRS: assume coordinates are already lat/lon in degrees
            lat_deg = p.northing
            lon_deg = p.easting
            elev = p.elevation

        placemarks.append(
            f"  <Placemark>\n"
            f"    <name>{p.number}</name>\n"
            f"    <description>{p.description}</description>\n"
            f"    <Point>\n"
            f"      <coordinates>{lon_deg:.6f},{lat_deg:.6f},{elev:.2f}</coordinates>\n"
            f"    </Point>\n"
            f"  </Placemark>"
        )
    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "<Document>\n"
        f"  <name>{job.name}</name>\n"
        + "\n".join(placemarks) + "\n"
        "</Document>\n"
        "</kml>\n"
    )
    path.write_text(kml)
