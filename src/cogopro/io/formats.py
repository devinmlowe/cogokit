"""Export stubs for DXF and KML formats."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from ..core.job import Job


def export_dxf(job: Job, destination: Union[str, Path]) -> None:
    """Export job points as a minimal DXF file (POINT entities)."""
    path = Path(destination)
    lines = [
        "0", "SECTION",
        "2", "ENTITIES",
    ]
    for p in job.points():
        lines.extend([
            "0", "POINT",
            "8", "POINTS",  # layer
            "10", f"{p.easting:.4f}",   # X = Easting
            "20", f"{p.northing:.4f}",  # Y = Northing
            "30", f"{p.elevation:.4f}", # Z = Elevation
        ])
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    path.write_text("\n".join(lines) + "\n")


def export_kml(job: Job, destination: Union[str, Path]) -> None:
    """Export job points as a KML file.

    Note: This is a stub that writes local coordinates as-is. Real usage
    would require coordinate transformation to WGS84 lat/lon.
    """
    path = Path(destination)
    placemarks = []
    for p in job.points():
        placemarks.append(
            f"  <Placemark>\n"
            f"    <name>{p.number}</name>\n"
            f"    <description>{p.description}</description>\n"
            f"    <Point>\n"
            f"      <coordinates>{p.easting:.6f},{p.northing:.6f},{p.elevation:.2f}</coordinates>\n"
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
