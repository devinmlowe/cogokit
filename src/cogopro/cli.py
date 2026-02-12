"""COGO+ Pro command-line interface."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional

import typer

from cogopro.cogo.area import polygon_area, polygon_perimeter
from cogopro.cogo.inverse import inverse
from cogopro.cogo.traverse import traverse as _traverse
from cogopro.core import Angle, Point
from cogopro.io import export_dxf, export_kml, read_points
from cogopro.solvers.horizontal_curve import solve_curve

app = typer.Typer(help="COGO+ Pro — coordinate geometry and surveying toolkit")


@app.command("inverse")
def inverse_cmd(
    n1: float = typer.Argument(..., help="Northing of point 1"),
    e1: float = typer.Argument(..., help="Easting of point 1"),
    n2: float = typer.Argument(..., help="Northing of point 2"),
    e2: float = typer.Argument(..., help="Easting of point 2"),
    z1: float = typer.Argument(0.0, help="Elevation of point 1"),
    z2: float = typer.Argument(0.0, help="Elevation of point 2"),
) -> None:
    """Compute azimuth, distance, and grade between two points."""
    p1 = Point(northing=n1, easting=e1, elevation=z1)
    p2 = Point(northing=n2, easting=e2, elevation=z2)
    result = inverse(p1, p2)
    bearing = Angle.from_radians(result.azimuth).to_bearing_string()
    typer.echo(f"Bearing:       {bearing}")
    typer.echo(f"Horiz. Dist:   {result.horizontal_distance:.4f}")
    typer.echo(f"Slope Dist:    {result.slope_distance:.4f}")
    typer.echo(f"Vert. Dist:    {result.vertical_distance:.4f}")
    typer.echo(f"Grade:         {result.grade:.4f}%")


@app.command("traverse")
def traverse_cmd(
    n: float = typer.Argument(..., help="Northing of origin"),
    e: float = typer.Argument(..., help="Easting of origin"),
    azimuth: float = typer.Argument(..., help="Azimuth in degrees"),
    distance: float = typer.Argument(..., help="Horizontal distance"),
    elevation: float = typer.Option(0.0, help="Elevation of new point"),
) -> None:
    """Compute a new point from origin, azimuth, and distance."""
    origin = Point(northing=n, easting=e)
    az_rad = math.radians(azimuth)
    pt = _traverse(origin, az_rad, distance, elevation)
    typer.echo(f"N: {pt.northing:.4f}")
    typer.echo(f"E: {pt.easting:.4f}")
    typer.echo(f"Z: {pt.elevation:.4f}")


@app.command()
def area(
    points_file: Path = typer.Argument(..., help="Path to points file"),
) -> None:
    """Compute polygon area and perimeter from a points file."""
    if not points_file.exists():
        typer.echo(f"Error: file not found: {points_file}", err=True)
        raise typer.Exit(code=1)
    job = read_points(points_file)
    pts = job.points()
    if len(pts) < 3:
        typer.echo("Error: need at least 3 points", err=True)
        raise typer.Exit(code=1)
    a = polygon_area(pts)
    p = polygon_perimeter(pts)
    typer.echo(f"Area:      {a:.4f}")
    typer.echo(f"Perimeter: {p:.4f}")


@app.command()
def curve(
    radius: Optional[float] = typer.Option(None, help="Radius"),
    delta: Optional[float] = typer.Option(None, help="Central angle in degrees"),
    tangent: Optional[float] = typer.Option(None, help="Tangent length"),
    length: Optional[float] = typer.Option(None, help="Arc length"),
    chord: Optional[float] = typer.Option(None, help="Long chord length"),
    external: Optional[float] = typer.Option(None, help="External distance"),
    mid_ordinate: Optional[float] = typer.Option(None, "--mid-ordinate", help="Middle ordinate"),
    degree: Optional[float] = typer.Option(None, help="Degree of curve"),
) -> None:
    """Solve a horizontal curve from any two elements."""
    kwargs: dict[str, float] = {}
    if radius is not None:
        kwargs["R"] = radius
    if delta is not None:
        kwargs["delta"] = math.radians(delta)
    if tangent is not None:
        kwargs["T"] = tangent
    if length is not None:
        kwargs["L"] = length
    if chord is not None:
        kwargs["C"] = chord
    if external is not None:
        kwargs["E"] = external
    if mid_ordinate is not None:
        kwargs["M"] = mid_ordinate
    if degree is not None:
        kwargs["D"] = degree

    if len(kwargs) != 2:
        typer.echo(f"Error: provide exactly 2 curve elements (got {len(kwargs)})", err=True)
        raise typer.Exit(code=1)

    try:
        c = solve_curve(**kwargs)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    delta_str = Angle.from_radians(c.delta).to_dms_string()
    typer.echo(f"Radius:    {c.R:.4f}")
    typer.echo(f"Delta:     {delta_str}")
    typer.echo(f"Tangent:   {c.T:.4f}")
    typer.echo(f"Length:    {c.L:.4f}")
    typer.echo(f"Chord:     {c.C:.4f}")
    typer.echo(f"External:  {c.E:.4f}")
    typer.echo(f"Mid-Ord:   {c.M:.4f}")
    typer.echo(f"Degree:    {c.D:.4f}")


def _parse_crs(crs_str: str):
    """Parse a CRS string like 'utm:17:N:wgs84' or 'geodetic:wgs84'.

    Returns a CRS object, or None if the CRS module is not available.
    """
    try:
        from cogopro.core.crs import CRS
        from cogopro.geodetic.ellipsoid import CLARKE_1866, GRS80, NAD83, WGS84
    except ImportError:
        return None

    ellipsoid_map = {
        "wgs84": WGS84,
        "grs80": GRS80,
        "nad83": NAD83,
        "clarke1866": CLARKE_1866,
    }
    parts = crs_str.lower().split(":")
    kind = parts[0]

    if kind == "geodetic":
        ellipsoid = ellipsoid_map.get(parts[1], WGS84) if len(parts) > 1 else WGS84
        return CRS.geodetic(ellipsoid=ellipsoid)
    elif kind == "utm":
        if len(parts) < 3:
            return None
        zone = int(parts[1])
        hemisphere = parts[2].upper()
        ellipsoid = ellipsoid_map.get(parts[3], WGS84) if len(parts) > 3 else WGS84
        return CRS.utm(zone, hemisphere, ellipsoid=ellipsoid)
    return None


@app.command()
def convert(
    points_file: Path = typer.Argument(..., help="Path to points file"),
    from_crs: str = typer.Option(..., "--from-crs", help="Source CRS (e.g. utm:17:N)"),
    to_crs: str = typer.Option(..., "--to-crs", help="Target CRS (e.g. geodetic:wgs84)"),
    output: Optional[Path] = typer.Option(None, help="Output file (default: stdout)"),
) -> None:
    """Transform coordinates between CRS types."""
    if not points_file.exists():
        typer.echo(f"Error: file not found: {points_file}", err=True)
        raise typer.Exit(code=1)

    src = _parse_crs(from_crs)
    dst = _parse_crs(to_crs)
    if src is None or dst is None:
        typer.echo("Error: CRS module not available or invalid CRS string", err=True)
        raise typer.Exit(code=1)

    try:
        from cogopro.core.crs import transform_job
    except ImportError:
        typer.echo("Error: CRS module not available", err=True)
        raise typer.Exit(code=1)

    job = read_points(points_file)
    transformed = transform_job(job, dst, from_crs=src)

    lines = []
    for p in transformed.points():
        lines.append(f"{p.number} {p.northing:.4f} {p.easting:.4f} {p.elevation:.4f}")

    text = "\n".join(lines) + "\n"
    if output:
        output.write_text(text)
        typer.echo(f"Written to {output}")
    else:
        typer.echo(text, nl=False)


@app.command()
def export(
    points_file: Path = typer.Argument(..., help="Path to points file"),
    fmt: str = typer.Option(..., "--format", help="Export format: dxf or kml"),
    output: Optional[Path] = typer.Option(None, help="Output file"),
) -> None:
    """Export points to DXF or KML format."""
    if not points_file.exists():
        typer.echo(f"Error: file not found: {points_file}", err=True)
        raise typer.Exit(code=1)

    job = read_points(points_file)
    fmt_lower = fmt.lower()

    if fmt_lower not in ("dxf", "kml"):
        typer.echo(f"Error: unsupported format '{fmt}' (use dxf or kml)", err=True)
        raise typer.Exit(code=1)

    out_path = output or Path(points_file.stem + f".{fmt_lower}")

    if fmt_lower == "dxf":
        export_dxf(job, out_path)
    else:
        export_kml(job, out_path)

    typer.echo(f"Exported to {out_path}")
