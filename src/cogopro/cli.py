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
from cogopro.surveying.workflow import TraverseWorkflow

app = typer.Typer(help="COGO+ Pro — coordinate geometry and surveying toolkit")
config_app = typer.Typer(help="Manage application configuration")
app.add_typer(config_app, name="config")


@config_app.command("list")
def config_list() -> None:
    """Show all configuration values."""
    from cogopro.config import get_config

    cfg = get_config()
    d = cfg.to_dict()
    for section, values in d.items():
        typer.echo(f"[{section}]")
        if isinstance(values, dict):
            for k, v in values.items():
                typer.echo(f"  {k} = {v}")
        typer.echo()


@config_app.command("get")
def config_get(key: str = typer.Argument(..., help="Dotted key, e.g. units.linear")) -> None:
    """Get a single configuration value."""
    from cogopro.config import get_config

    cfg = get_config()
    try:
        value = cfg.get(key)
        typer.echo(value)
    except KeyError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dotted key, e.g. units.linear"),
    value: str = typer.Argument(..., help="Value to set"),
    global_: bool = typer.Option(False, "--global", help="Write to global config instead of project-local"),
) -> None:
    """Set a configuration value."""
    from cogopro.config import get_config, save_config

    cfg = get_config()
    try:
        cfg.set(key, value)
    except KeyError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    path = save_config(cfg, global_=global_)
    typer.echo(f"{key} = {value}")
    typer.echo(f"Saved to {path}")


@config_app.command("reset")
def config_reset(
    global_: bool = typer.Option(False, "--global", help="Reset global config instead of project-local"),
) -> None:
    """Delete the configuration file (revert to defaults)."""
    from pathlib import Path

    from cogopro.config.loader import GLOBAL_CONFIG_PATH, PROJECT_CONFIG_PATH

    path = GLOBAL_CONFIG_PATH if global_ else PROJECT_CONFIG_PATH
    if path.is_file():
        path.unlink()
        typer.echo(f"Removed {path}")
    else:
        typer.echo(f"No config file at {path}")


@config_app.command("path")
def config_path() -> None:
    """Show resolved configuration file paths and status."""
    from cogopro.config.loader import GLOBAL_CONFIG_PATH, PROJECT_CONFIG_PATH

    for label, p in [("Global", GLOBAL_CONFIG_PATH), ("Project", PROJECT_CONFIG_PATH)]:
        exists = "exists" if p.is_file() else "not found"
        typer.echo(f"{label:>8}: {p}  ({exists})")


@app.command()
def tui() -> None:
    """Launch the interactive terminal user interface."""
    try:
        from cogopro.tui import run
    except ImportError:
        typer.echo(
            "The TUI requires the 'textual' package.\n"
            "Install it with: pip install cogopro[tui]",
            err=True,
        )
        raise typer.Exit(code=1)
    run()


@app.command("inverse")
def inverse_cmd(
    n1: float = typer.Argument(..., help="Northing of point 1"),
    e1: float = typer.Argument(..., help="Easting of point 1"),
    n2: float = typer.Argument(..., help="Northing of point 2"),
    e2: float = typer.Argument(..., help="Easting of point 2"),
    z1: float = typer.Argument(0.0, help="Elevation of point 1"),
    z2: float = typer.Argument(0.0, help="Elevation of point 2"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
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
    if report is not None:
        from cogopro.io.reports import report_inverse, write_report
        html = report_inverse(p1, p2, result)
        out = write_report(html, report, "inverse")
        typer.echo(f"Report: {out}")


@app.command("traverse")
def traverse_cmd(
    n: float = typer.Argument(..., help="Northing of origin"),
    e: float = typer.Argument(..., help="Easting of origin"),
    azimuth: float = typer.Argument(..., help="Azimuth in degrees"),
    distance: float = typer.Argument(..., help="Horizontal distance"),
    elevation: float = typer.Option(0.0, help="Elevation of new point"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
) -> None:
    """Compute a new point from origin, azimuth, and distance."""
    origin = Point(northing=n, easting=e)
    az_rad = math.radians(azimuth)
    pt = _traverse(origin, az_rad, distance, elevation)
    typer.echo(f"N: {pt.northing:.4f}")
    typer.echo(f"E: {pt.easting:.4f}")
    typer.echo(f"Z: {pt.elevation:.4f}")
    if report is not None:
        from cogopro.io.reports import report_traverse, write_report
        html = report_traverse(origin, az_rad, distance, pt)
        out = write_report(html, report, "traverse")
        typer.echo(f"Report: {out}")


@app.command()
def area(
    points_file: Path = typer.Argument(..., help="Path to points file"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
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
    if report is not None:
        from cogopro.io.reports import report_area, write_report
        html = report_area(pts, a, p)
        out = write_report(html, report, "area")
        typer.echo(f"Report: {out}")


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
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
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
    if report is not None:
        from cogopro.io.reports import report_curve, write_report
        html = report_curve(kwargs, c)
        out = write_report(html, report, "curve")
        typer.echo(f"Report: {out}")


@app.command()
def zones(
    state: Optional[str] = typer.Option(None, help="Filter by state abbreviation (e.g. TX)"),
    epsg: Optional[int] = typer.Option(None, help="Show details for a specific EPSG code"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
) -> None:
    """List available State Plane coordinate system zones."""
    from cogopro.geodetic.state_plane import get_zone, list_zones

    if epsg is not None:
        try:
            zone = get_zone(epsg)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"EPSG:  {zone.epsg}")
        typer.echo(f"Name:  {zone.name}")
        typer.echo(f"State: {zone.state}")
        typer.echo(f"Zone:  {zone.zone}")
        typer.echo(f"Type:  {zone.proj_def.proj_type}")
        typer.echo(f"Units: {zone.proj_def.units}")
        if report is not None:
            from cogopro.io.reports import report_zones, write_report
            html = report_zones([zone], state_filter=zone.state)
            out = write_report(html, report, "zones")
            typer.echo(f"Report: {out}")
        return

    zone_list = list_zones(state=state)
    if not zone_list:
        typer.echo("No zones found.")
        return

    for z in zone_list:
        typer.echo(f"  EPSG:{z.epsg:<6}  {z.state}  {z.zone:<20}  {z.proj_def.proj_type}")
    if report is not None:
        from cogopro.io.reports import report_zones, write_report
        html = report_zones(zone_list, state_filter=state)
        out = write_report(html, report, "zones")
        typer.echo(f"Report: {out}")


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
    elif kind == "epsg":
        try:
            return CRS.state_plane(int(parts[1]))
        except (ValueError, IndexError):
            return None
    elif kind == "sp":
        try:
            from cogopro.geodetic.state_plane import find_zone
            state_code = parts[1].upper()
            zone_name = parts[2] if len(parts) > 2 else ""
            zone = find_zone(state_code, zone_name)
            return CRS.state_plane(zone.epsg)
        except (ValueError, IndexError):
            return None
    elif kind == "proj4":
        try:
            proj4_str = crs_str[len("proj4:"):].strip().strip('"').strip("'")
            return CRS.from_proj4(proj4_str)
        except (ValueError, IndexError):
            return None
    return None


@app.command()
def convert(
    points_file: Path = typer.Argument(..., help="Path to points file"),
    from_crs: str = typer.Option(..., "--from-crs", help="Source CRS (e.g. utm:17:N)"),
    to_crs: str = typer.Option(..., "--to-crs", help="Target CRS (e.g. geodetic:wgs84)"),
    output: Optional[Path] = typer.Option(None, help="Output file (default: stdout)"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
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
    if report is not None:
        from cogopro.io.reports import report_convert, write_report
        html = report_convert(from_crs, to_crs, job.points(), transformed.points())
        out = write_report(html, report, "convert")
        typer.echo(f"Report: {out}")


@app.command()
def export(
    points_file: Path = typer.Argument(..., help="Path to points file"),
    fmt: str = typer.Option(..., "--format", help="Export format: dxf or kml"),
    output: Optional[Path] = typer.Option(None, help="Output file"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
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
    if report is not None:
        from cogopro.io.reports import report_export, write_report
        html = report_export(job.name, len(job.points()), fmt_lower.upper(), str(out_path))
        out = write_report(html, report, "export")
        typer.echo(f"Report: {out}")


@app.command("traverse-run")
def traverse_run_cmd(
    observations_file: Path = typer.Argument(..., help="CSV file with traverse observations"),
    start_point: str = typer.Option(..., "--start-point", help="Start point: 'number northing easting [elevation]'"),
    start_azimuth: float = typer.Option(..., "--start-azimuth", help="Starting backsight azimuth (HP notation)"),
    close_to: Optional[int] = typer.Option(None, "--close-to", help="Close to point number (default: start)"),
    report: Optional[Path] = typer.Option(None, "--report", help="Generate HTML report"),
) -> None:
    """Run a complete traverse workflow from an observations file."""
    # Parse start point
    parts = start_point.split()
    if len(parts) < 3:
        typer.echo("Error: --start-point requires 'number northing easting [elevation]'", err=True)
        raise typer.Exit(code=1)

    try:
        sp = Point(
            number=int(parts[0]),
            northing=float(parts[1]),
            easting=float(parts[2]),
            elevation=float(parts[3]) if len(parts) > 3 else 0.0,
        )
    except (ValueError, IndexError):
        typer.echo("Error: invalid --start-point format", err=True)
        raise typer.Exit(code=1)

    if not observations_file.exists():
        typer.echo(f"Error: file not found: {observations_file}", err=True)
        raise typer.Exit(code=1)

    # Read raw observation lines for the report
    raw_obs_lines = []
    for line in observations_file.read_text().strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        raw_obs_lines.append(stripped)

    wf = TraverseWorkflow(
        start_point=sp,
        start_azimuth=start_azimuth,
        close_to_start=(close_to is None or close_to == sp.number),
    )

    for line in raw_obs_lines:
        fields = line.split(",")
        wf.add_leg(
            occupied=int(fields[0]),
            backsight=int(fields[1]),
            foresight=int(fields[2]),
            angle_dms=float(fields[3]),
            distance=float(fields[4]),
            hi=float(fields[5]) if len(fields) > 5 else 0.0,
            ht=float(fields[6]) if len(fields) > 6 else 0.0,
        )

    result = wf.run()

    typer.echo("=== Traverse Workflow Results ===\n")
    typer.echo(f"Angular Misclosure: {result.angular_misclosure.to_dms_string(4)}")
    typer.echo(f"Angular Tolerance:  {result.angular_tolerance.to_dms_string(4)}")
    typer.echo(f"Closure North:      {result.closure_north:.4f}")
    typer.echo(f"Closure East:       {result.closure_east:.4f}")
    typer.echo(f"Linear Misclosure:  {result.linear_misclosure:.4f}")
    typer.echo(f"Perimeter:          {result.perimeter:.4f}")
    if result.precision_ratio == float("inf"):
        typer.echo("Precision Ratio:    Perfect (no misclosure)")
    else:
        typer.echo(f"Precision Ratio:    1:{result.precision_ratio:.0f}")
    typer.echo("\n--- Adjusted Coordinates ---")
    for pt in result.adjusted_job.points():
        typer.echo(
            f"  {pt.number:>5}  N={pt.northing:>12.4f}  E={pt.easting:>12.4f}  Z={pt.elevation:>10.4f}"
        )
    if report is not None:
        from cogopro.core import Angle as _Angle
        from cogopro.io.reports import report_traverse_run, write_report
        start_az_rad = _Angle.from_hp_notation(start_azimuth).radians
        html = report_traverse_run(result, raw_obs_lines, sp, start_az_rad)
        out = write_report(html, report, "traverse-run")
        typer.echo(f"Report: {out}")
