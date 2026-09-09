"""HTML report generation for cogokit commands.

Each report function produces a self-contained HTML string with inline CSS,
SVG graphics, and monospace number formatting.  Reports are designed for
screen viewing and print (@media print).
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

from cogokit.cogo.inverse import InverseResult, inverse
from cogokit.core import Angle, Point
from cogokit.solvers.horizontal_curve import CurveElements

# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    max-width: 800px; margin: 0 auto; padding: 24px;
    color: #1a2332; background: #fff; line-height: 1.5;
}
h1 { font-size: 1.5rem; margin-bottom: 4px; color: #1a2332; }
h2 { font-size: 1.15rem; margin: 20px 0 8px; color: #1a2332;
     border-bottom: 2px solid #e0e0e0; padding-bottom: 4px; }
.subtitle { color: #666; font-size: 0.85rem; margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
th { background: #2c3e50; color: #fff; text-align: left;
     padding: 8px 10px; font-weight: 600; font-size: 0.85rem; }
td { padding: 6px 10px; font-size: 0.85rem; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f8f9fa; }
tr:nth-child(odd)  td { background: #fff; }
.mono { font-family: "SF Mono", "Fira Code", "Consolas", monospace; }
.right { text-align: right; }
.center { text-align: center; }
.summary-box { background: #f0f4f8; border-left: 4px solid #2c3e50;
               padding: 12px 16px; margin: 12px 0; border-radius: 0 4px 4px 0; }
.summary-box dt { font-weight: 600; display: inline; }
.summary-box dd { display: inline; margin-left: 4px; }
.summary-box dl { margin: 0; }
.summary-box .row { margin: 4px 0; }
.pass { color: #27ae60; font-weight: 700; }
.fail { color: #e74c3c; font-weight: 700; }
.bold { font-weight: 700; }
svg { display: block; margin: 12px auto; }
footer { margin-top: 24px; padding-top: 8px;
         border-top: 1px solid #e0e0e0; font-size: 0.75rem; color: #999; }
@media print {
    body { padding: 0; }
    .no-print { display: none; }
    th { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    tr:nth-child(even) td {
        -webkit-print-color-adjust: exact; print-color-adjust: exact;
    }
}
"""


# ---------------------------------------------------------------------------
# HTML document wrapper
# ---------------------------------------------------------------------------

def _html_wrap(title: str, body: str) -> str:
    """Wrap *body* HTML in a full document with inline CSS."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>{_esc(title)}</title>\n"
        f"<style>\n{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"<h1>{_esc(title)}</h1>\n"
        f"<p class=\"subtitle\">Generated {timestamp} by cogokit</p>\n"
        f"{body}\n"
        f"<footer>cogokit &mdash; {_esc(timestamp)}</footer>\n"
        "</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def write_report(html: str, report_path: Path, command_name: str) -> Path:
    """Write an HTML report to disk.

    Parameters:
        html: Complete HTML string.
        report_path: Target path.  If it is a directory the file is
            auto-named ``{command}_{YYYYMMDD_HHMMSS}.html``.  If it is
            a file path the report is written directly.
        command_name: Short command name used for auto-naming.

    Returns:
        The actual ``Path`` the report was written to.
    """
    report_path = Path(report_path)
    if report_path.is_dir():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_path / f"{command_name}_{stamp}.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt(value: float, decimals: int = 4) -> str:
    """Format a float with fixed decimals, wrapped in a mono span."""
    return f'<span class="mono">{value:,.{decimals}f}</span>'


def _fmt_raw(value: float, decimals: int = 4) -> str:
    """Format a float with fixed decimals, no span."""
    return f"{value:,.{decimals}f}"


def _angle_dms(radians: float) -> str:
    """Format radians as a DMS string."""
    return Angle.from_radians(radians).to_dms_string(precision=2)


def _angle_bearing(radians: float) -> str:
    """Format radians as a surveyor bearing string."""
    return Angle.from_radians(radians).to_bearing_string(precision=0)


def _pt_label(pt: Point) -> str:
    """Short label for a point: number or '?'."""
    return str(pt.number) if pt.number is not None else "?"


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def _survey_to_svg(
    points_ne: list[tuple[float, float]],
    width: int = 400,
    height: int = 300,
    padding: int = 40,
) -> tuple[list[tuple[float, float]], int, int, int]:
    """Transform survey (northing, easting) coordinates to SVG pixel space.

    Survey convention: N is up, E is right.
    SVG convention:   Y increases downward.

    Returns:
        (pixel_coords, width, height, padding) where each pixel coord
        is (svg_x, svg_y).
    """
    if not points_ne:
        return [], width, height, padding

    northings = [n for n, _ in points_ne]
    eastings = [e for _, e in points_ne]
    n_min, n_max = min(northings), max(northings)
    e_min, e_max = min(eastings), max(eastings)

    data_w = e_max - e_min or 1.0
    data_h = n_max - n_min or 1.0

    draw_w = width - 2 * padding
    draw_h = height - 2 * padding

    scale = min(draw_w / data_w, draw_h / data_h)

    pixels = []
    for n, e in points_ne:
        sx = padding + (e - e_min) * scale
        sy = padding + (n_max - n) * scale  # N-up -> Y-down
        pixels.append((sx, sy))

    return pixels, width, height, padding


def _svg_line(x1: float, y1: float, x2: float, y2: float,
              stroke: str = "#2c3e50", stroke_width: float = 2) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" '
        f'x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}" />'
    )


def _svg_circle(cx: float, cy: float, r: float = 4,
                fill: str = "#e74c3c") -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" />'


def _svg_text(x: float, y: float, text: str,
              font_size: int = 11, anchor: str = "middle",
              fill: str = "#1a2332") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" '
        f'text-anchor="{anchor}" fill="{fill}" '
        f'font-family="sans-serif">{_esc(text)}</text>'
    )


def _svg_polygon_elem(points: list[tuple[float, float]],
                       fill: str = "rgba(44,62,80,0.1)",
                       stroke: str = "#2c3e50",
                       stroke_width: float = 2) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polygon points="{pts}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}" />'
    )


def _svg_arc_path(cx: float, cy: float, r: float,
                  start_angle: float, end_angle: float,
                  stroke: str = "#2c3e50",
                  stroke_width: float = 2) -> str:
    """SVG arc from start_angle to end_angle (in radians, 0 = right, CCW).

    Uses the SVG arc command.  Angles are math convention (from +X axis, CCW).
    """
    # Convert to SVG coords (CW from +X axis)
    x1 = cx + r * math.cos(start_angle)
    y1 = cy - r * math.sin(start_angle)
    x2 = cx + r * math.cos(end_angle)
    y2 = cy - r * math.sin(end_angle)

    sweep = end_angle - start_angle
    large_arc = 1 if abs(sweep) > math.pi else 0
    # SVG sweep-flag: 0 = CCW in SVG coords (which is CW in math coords)
    sweep_flag = 0 if sweep > 0 else 1

    return (
        f'<path d="M {x1:.1f} {y1:.1f} '
        f'A {r:.1f} {r:.1f} 0 {large_arc} {sweep_flag} '
        f'{x2:.1f} {y2:.1f}" '
        f'fill="none" stroke="{stroke}" stroke-width="{stroke_width}" />'
    )


def _svg_arrow_head(x1: float, y1: float, x2: float, y2: float,
                     size: float = 10, fill: str = "#2c3e50") -> str:
    """Small arrowhead at (x2, y2) pointing from (x1, y1)."""
    angle = math.atan2(y2 - y1, x2 - x1)
    a1 = angle + math.radians(150)
    a2 = angle - math.radians(150)
    px1 = x2 + size * math.cos(a1)
    py1 = y2 + size * math.sin(a1)
    px2 = x2 + size * math.cos(a2)
    py2 = y2 + size * math.sin(a2)
    return (
        f'<polygon points="{x2:.1f},{y2:.1f} '
        f'{px1:.1f},{py1:.1f} {px2:.1f},{py2:.1f}" fill="{fill}" />'
    )


def _build_svg(inner: str, width: int = 400, height: int = 300) -> str:
    """Wrap SVG inner elements in an <svg> tag."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<rect width="{width}" height="{height}" fill="#fafbfc" rx="4" />\n'
        f"{inner}\n</svg>"
    )


# ---------------------------------------------------------------------------
# Report 1 — Inverse
# ---------------------------------------------------------------------------

def report_inverse(p1: Point, p2: Point, result: InverseResult) -> str:
    """Generate an HTML report for an inverse calculation.

    Parameters:
        p1: Starting point.
        p2: Ending point.
        result: InverseResult from ``cogo.inverse.inverse()``.

    Returns:
        Complete HTML document string.
    """
    bearing = _angle_bearing(result.azimuth)
    azimuth_dms = _angle_dms(result.azimuth)

    # Points table
    points_table = (
        "<h2>Points</h2>\n"
        "<table>\n"
        "<tr><th>Point</th><th class=\"right\">Northing</th>"
        "<th class=\"right\">Easting</th><th class=\"right\">Elevation</th></tr>\n"
        f"<tr><td>{_esc(_pt_label(p1))}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p1.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p1.easting)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p1.elevation)}</td></tr>\n"
        f"<tr><td>{_esc(_pt_label(p2))}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p2.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p2.easting)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(p2.elevation)}</td></tr>\n"
        "</table>\n"
    )

    # Results
    results_html = (
        "<h2>Inverse Results</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Azimuth:</dt> <dd class="mono">{_esc(azimuth_dms)}</dd></div>\n'
        f'<div class="row"><dt>Bearing:</dt> <dd class="mono">{_esc(bearing)}</dd></div>\n'
        f'<div class="row"><dt>Horizontal Distance:</dt> <dd class="mono">'
        f'{_fmt_raw(result.horizontal_distance)}</dd></div>\n'
        f'<div class="row"><dt>Vertical Distance:</dt> <dd class="mono">'
        f'{_fmt_raw(result.vertical_distance)}</dd></div>\n'
        f'<div class="row"><dt>Slope Distance:</dt> <dd class="mono">'
        f'{_fmt_raw(result.slope_distance)}</dd></div>\n'
        f'<div class="row"><dt>Grade:</dt> <dd class="mono">'
        f'{_fmt_raw(result.grade, 2)}%</dd></div>\n'
        "</div>\n"
    )

    # SVG
    pts_ne = [(p1.northing, p1.easting), (p2.northing, p2.easting)]
    pixels, w, h, pad = _survey_to_svg(pts_ne)
    svg_parts: list[str] = []
    if len(pixels) == 2:
        (x1, y1), (x2, y2) = pixels
        svg_parts.append(_svg_line(x1, y1, x2, y2))
        svg_parts.append(_svg_circle(x1, y1, fill="#2c3e50"))
        svg_parts.append(_svg_circle(x2, y2, fill="#e74c3c"))
        svg_parts.append(_svg_text(x1, y1 - 10, _pt_label(p1)))
        svg_parts.append(_svg_text(x2, y2 - 10, _pt_label(p2)))
    svg_html = "<h2>Diagram</h2>\n" + _build_svg("\n".join(svg_parts), w, h)

    body = points_table + results_html + svg_html
    return _html_wrap("Inverse Report", body)


# ---------------------------------------------------------------------------
# Report 2 — Traverse (single shot)
# ---------------------------------------------------------------------------

def report_traverse(
    origin: Point,
    azimuth: float,
    distance: float,
    result: Point,
) -> str:
    """Generate an HTML report for a single traverse (forward) calculation.

    Parameters:
        origin: Starting point.
        azimuth: Direction in radians.
        distance: Horizontal distance.
        result: Computed end point.

    Returns:
        Complete HTML document string.
    """
    azimuth_dms = _angle_dms(azimuth)
    bearing = _angle_bearing(azimuth)

    params_html = (
        "<h2>Input Parameters</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Azimuth:</dt> <dd class="mono">{_esc(azimuth_dms)}</dd></div>\n'
        f'<div class="row"><dt>Bearing:</dt> <dd class="mono">{_esc(bearing)}</dd></div>\n'
        f'<div class="row"><dt>Distance:</dt> <dd class="mono">'
        f'{_fmt_raw(distance)}</dd></div>\n'
        "</div>\n"
    )

    coords_table = (
        "<h2>Coordinates</h2>\n"
        "<table>\n"
        "<tr><th>Point</th><th>Role</th><th class=\"right\">Northing</th>"
        "<th class=\"right\">Easting</th><th class=\"right\">Elevation</th></tr>\n"
        f"<tr><td>{_esc(_pt_label(origin))}</td><td>Origin</td>"
        f"<td class=\"right mono\">{_fmt_raw(origin.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(origin.easting)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(origin.elevation)}</td></tr>\n"
        f"<tr><td>{_esc(_pt_label(result))}</td><td>Computed</td>"
        f"<td class=\"right mono\">{_fmt_raw(result.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(result.easting)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(result.elevation)}</td></tr>\n"
        "</table>\n"
    )

    # SVG with arrow
    pts_ne = [(origin.northing, origin.easting), (result.northing, result.easting)]
    pixels, w, h, pad = _survey_to_svg(pts_ne)
    svg_parts: list[str] = []
    if len(pixels) == 2:
        (x1, y1), (x2, y2) = pixels
        svg_parts.append(_svg_line(x1, y1, x2, y2))
        svg_parts.append(_svg_arrow_head(x1, y1, x2, y2))
        svg_parts.append(_svg_circle(x1, y1, fill="#2c3e50"))
        svg_parts.append(_svg_circle(x2, y2, fill="#e74c3c"))
        svg_parts.append(_svg_text(x1, y1 - 10, _pt_label(origin)))
        svg_parts.append(_svg_text(x2, y2 - 10, _pt_label(result)))
    svg_html = "<h2>Diagram</h2>\n" + _build_svg("\n".join(svg_parts), w, h)

    body = params_html + coords_table + svg_html
    return _html_wrap("Traverse Report", body)


# ---------------------------------------------------------------------------
# Report 3 — Area
# ---------------------------------------------------------------------------

def report_area(
    points: list[Point],
    area: float,
    perimeter: float,
) -> str:
    """Generate an HTML report for a polygon area calculation.

    Parameters:
        points: Ordered polygon vertices.
        area: Computed area in square units.
        perimeter: Computed perimeter in linear units.

    Returns:
        Complete HTML document string.
    """
    # Point table
    rows: list[str] = []
    for pt in points:
        rows.append(
            f"<tr><td>{_esc(_pt_label(pt))}</td>"
            f"<td class=\"right mono\">{_fmt_raw(pt.northing)}</td>"
            f"<td class=\"right mono\">{_fmt_raw(pt.easting)}</td></tr>"
        )
    pt_table = (
        "<h2>Polygon Vertices</h2>\n<table>\n"
        "<tr><th>Point</th><th class=\"right\">Northing</th>"
        "<th class=\"right\">Easting</th></tr>\n"
        + "\n".join(rows) + "\n</table>\n"
    )

    # Leg table (inverse between consecutive + closing leg)
    leg_rows: list[str] = []
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        p_from = points[i]
        p_to = points[j]
        inv = inverse(p_from, p_to)
        leg_rows.append(
            f"<tr><td>{_esc(_pt_label(p_from))} &rarr; {_esc(_pt_label(p_to))}</td>"
            f"<td class=\"mono\">{_esc(_angle_bearing(inv.azimuth))}</td>"
            f"<td class=\"right mono\">{_fmt_raw(inv.horizontal_distance)}</td></tr>"
        )
    leg_table = (
        "<h2>Boundary Legs</h2>\n<table>\n"
        "<tr><th>Leg</th><th>Bearing</th><th class=\"right\">Distance</th></tr>\n"
        + "\n".join(leg_rows) + "\n</table>\n"
    )

    # Summary
    acres = area / 43560.0
    summary = (
        "<h2>Area &amp; Perimeter</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Area:</dt> <dd class="mono">'
        f'{_fmt_raw(area, 2)} sq ft</dd></div>\n'
        f'<div class="row"><dt>Area:</dt> <dd class="mono">'
        f'{_fmt_raw(acres, 4)} acres</dd></div>\n'
        f'<div class="row"><dt>Perimeter:</dt> <dd class="mono">'
        f'{_fmt_raw(perimeter, 2)} ft</dd></div>\n'
        "</div>\n"
    )

    # SVG polygon
    pts_ne = [(pt.northing, pt.easting) for pt in points]
    pixels, w, h, pad = _survey_to_svg(pts_ne)
    svg_parts: list[str] = []
    if pixels:
        svg_parts.append(_svg_polygon_elem(pixels))
        for i, (px, py) in enumerate(pixels):
            svg_parts.append(_svg_circle(px, py, r=4, fill="#2c3e50"))
            svg_parts.append(_svg_text(px, py - 10, _pt_label(points[i])))
    svg_html = "<h2>Diagram</h2>\n" + _build_svg("\n".join(svg_parts), w, h)

    body = pt_table + leg_table + summary + svg_html
    return _html_wrap("Area Report", body)


# ---------------------------------------------------------------------------
# Report 4 — Horizontal Curve
# ---------------------------------------------------------------------------

def report_curve(
    input_params: dict[str, Any],
    elements: CurveElements,
) -> str:
    """Generate an HTML report for a horizontal curve solution.

    Parameters:
        input_params: Dict of the two input parameters (e.g. ``{"R": 500, "delta": 0.5}``).
            Keys are element names; values are floats.  Angle values (delta, D)
            are assumed radians / degrees respectively.
        elements: Solved CurveElements.

    Returns:
        Complete HTML document string.
    """
    # Input section
    input_rows: list[str] = []
    for k, v in input_params.items():
        display_val = _angle_dms(v) if k == "delta" else _fmt_raw(v)
        input_rows.append(
            f'<tr><td class="bold">{_esc(k)}</td>'
            f'<td class="right mono">{_esc(str(display_val))}</td></tr>'
        )
    input_html = (
        "<h2>Input Parameters</h2>\n<table>\n"
        "<tr><th>Parameter</th><th class=\"right\">Value</th></tr>\n"
        + "\n".join(input_rows) + "\n</table>\n"
    )

    # All 8 elements
    delta_dms = _angle_dms(elements.delta)
    elem_data = [
        ("R (Radius)", f"{_fmt_raw(elements.R)}"),
        ("Delta (Central Angle)", f"{_esc(delta_dms)}"),
        ("T (Tangent Length)", f"{_fmt_raw(elements.T)}"),
        ("L (Arc Length)", f"{_fmt_raw(elements.L)}"),
        ("C (Long Chord)", f"{_fmt_raw(elements.C)}"),
        ("E (External Distance)", f"{_fmt_raw(elements.E)}"),
        ("M (Middle Ordinate)", f"{_fmt_raw(elements.M)}"),
        ("D (Degree of Curve)", f"{_fmt_raw(elements.D, 6)}"),
    ]
    elem_rows = "\n".join(
        f'<tr><td>{_esc(name)}</td><td class="right mono">{val}</td></tr>'
        for name, val in elem_data
    )
    elem_html = (
        "<h2>Curve Elements</h2>\n<table>\n"
        "<tr><th>Element</th><th class=\"right\">Value</th></tr>\n"
        + elem_rows + "\n</table>\n"
    )

    # SVG curve arc
    svg_w, svg_h = 400, 300
    cx, cy = svg_w / 2, svg_h - 40
    svg_r = min(svg_w, svg_h) * 0.35

    half_delta = elements.delta / 2
    # Arc from (pi/2 + half_delta) to (pi/2 - half_delta) — centered on top
    start_a = math.pi / 2 + half_delta
    end_a = math.pi / 2 - half_delta

    svg_parts: list[str] = []
    svg_parts.append(_svg_arc_path(cx, cy, svg_r, end_a, start_a,
                                    stroke="#2c3e50", stroke_width=3))

    # PC and PT markers
    pc_x = cx + svg_r * math.cos(start_a)
    pc_y = cy - svg_r * math.sin(start_a)
    pt_x = cx + svg_r * math.cos(end_a)
    pt_y = cy - svg_r * math.sin(end_a)
    svg_parts.append(_svg_circle(pc_x, pc_y, r=5, fill="#2c3e50"))
    svg_parts.append(_svg_circle(pt_x, pt_y, r=5, fill="#e74c3c"))
    svg_parts.append(_svg_text(pc_x - 15, pc_y - 10, "PC"))
    svg_parts.append(_svg_text(pt_x + 15, pt_y - 10, "PT"))

    # Tangent lines from PI
    pi_x = cx
    pi_y = cy - svg_r / math.cos(half_delta)
    svg_parts.append(_svg_line(pi_x, pi_y, pc_x, pc_y,
                                stroke="#999", stroke_width=1))
    svg_parts.append(_svg_line(pi_x, pi_y, pt_x, pt_y,
                                stroke="#999", stroke_width=1))
    svg_parts.append(_svg_circle(pi_x, pi_y, r=4, fill="#f39c12"))
    svg_parts.append(_svg_text(pi_x, pi_y - 10, "PI", fill="#f39c12"))

    # Radius line to center
    svg_parts.append(_svg_line(cx, cy, pc_x, pc_y,
                                stroke="#ddd", stroke_width=1))
    svg_parts.append(_svg_text(cx + 5, cy + 14, "O", font_size=10, fill="#999"))

    svg_html = "<h2>Diagram</h2>\n" + _build_svg("\n".join(svg_parts), svg_w, svg_h)

    body = input_html + elem_html + svg_html
    return _html_wrap("Horizontal Curve Report", body)


# ---------------------------------------------------------------------------
# Report 5 — Zones
# ---------------------------------------------------------------------------

def report_zones(
    zones: list[Any],
    state_filter: str | None = None,
) -> str:
    """Generate an HTML report listing State Plane zones.

    Parameters:
        zones: List of StatePlaneZone objects (or any object with ``epsg``,
            ``name``, ``state``, ``zone`` attributes).
        state_filter: If provided, the state abbreviation used to filter.

    Returns:
        Complete HTML document string.
    """
    title_suffix = f" ({state_filter.upper()})" if state_filter else ""
    title = f"State Plane Zones{title_suffix}"

    count_html = (
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Zones found:</dt> '
        f'<dd class="mono">{len(zones)}</dd></div>\n'
        "</div>\n"
    )

    rows: list[str] = []
    for z in zones:
        rows.append(
            f"<tr><td class=\"mono\">{z.epsg}</td>"
            f"<td>{_esc(z.state)}</td>"
            f"<td>{_esc(z.zone)}</td>"
            f"<td>{_esc(z.name)}</td></tr>"
        )
    table = (
        "<h2>Zone Listing</h2>\n<table>\n"
        "<tr><th>EPSG</th><th>State</th><th>Zone</th><th>Name</th></tr>\n"
        + "\n".join(rows) + "\n</table>\n"
    )

    body = count_html + table
    return _html_wrap(title, body)


# ---------------------------------------------------------------------------
# Report 6 — Coordinate Conversion
# ---------------------------------------------------------------------------

def report_convert(
    source_crs_str: str,
    target_crs_str: str,
    original_points: list[Point],
    transformed_points: list[Point],
) -> str:
    """Generate an HTML report for a coordinate conversion.

    Parameters:
        source_crs_str: Human-readable source CRS description.
        target_crs_str: Human-readable target CRS description.
        original_points: Points before conversion.
        transformed_points: Points after conversion.

    Returns:
        Complete HTML document string.
    """
    crs_html = (
        "<h2>Coordinate Reference Systems</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Source CRS:</dt> '
        f'<dd>{_esc(source_crs_str)}</dd></div>\n'
        f'<div class="row"><dt>Target CRS:</dt> '
        f'<dd>{_esc(target_crs_str)}</dd></div>\n'
        f'<div class="row"><dt>Points converted:</dt> '
        f'<dd class="mono">{len(original_points)}</dd></div>\n'
        "</div>\n"
    )

    # Before / After table
    rows: list[str] = []
    for orig, xform in zip(original_points, transformed_points):
        label = _pt_label(orig)
        rows.append(
            f"<tr><td>{_esc(label)}</td>"
            f"<td class=\"right mono\">{_fmt_raw(orig.northing)}</td>"
            f"<td class=\"right mono\">{_fmt_raw(orig.easting)}</td>"
            f"<td class=\"right mono\">{_fmt_raw(xform.northing)}</td>"
            f"<td class=\"right mono\">{_fmt_raw(xform.easting)}</td></tr>"
        )
    table = (
        "<h2>Point Coordinates</h2>\n<table>\n"
        "<tr><th>Pt</th>"
        "<th class=\"right\">Source N</th><th class=\"right\">Source E</th>"
        "<th class=\"right\">Target N</th><th class=\"right\">Target E</th></tr>\n"
        + "\n".join(rows) + "\n</table>\n"
    )

    body = crs_html + table
    return _html_wrap("Coordinate Conversion Report", body)


# ---------------------------------------------------------------------------
# Report 7 — Export confirmation
# ---------------------------------------------------------------------------

def report_export(
    job_name: str,
    point_count: int,
    format: str,
    output_path: str,
) -> str:
    """Generate an HTML report confirming a file export.

    Parameters:
        job_name: Name of the job exported.
        point_count: Number of points written.
        format: Export format (e.g. "DXF", "KML", "LandXML").
        output_path: Path of the written file.

    Returns:
        Complete HTML document string.
    """
    body = (
        "<h2>Export Summary</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Job:</dt> <dd>{_esc(job_name)}</dd></div>\n'
        f'<div class="row"><dt>Format:</dt> <dd>{_esc(format)}</dd></div>\n'
        f'<div class="row"><dt>Points exported:</dt> '
        f'<dd class="mono">{point_count}</dd></div>\n'
        f'<div class="row"><dt>Output file:</dt> '
        f'<dd class="mono">{_esc(output_path)}</dd></div>\n'
        "</div>\n"
    )
    return _html_wrap("Export Report", body)


# ---------------------------------------------------------------------------
# Report 8 — Traverse Run (full workflow)
# ---------------------------------------------------------------------------

def report_traverse_run(
    result: Any,
    observations: list[str],
    start_point: Point,
    start_azimuth: float,
) -> str:
    """Generate an HTML report for a full traverse run workflow.

    Parameters:
        result: TraverseResult from ``surveying.workflow.TraverseWorkflow.run()``.
        observations: List of human-readable observation strings
            (e.g. ``["Occ:1 BS:5 FS:2 Angle:90.0000 Dist:100.00"]``).
        start_point: Starting (known) point.
        start_azimuth: Starting azimuth in radians.

    Returns:
        Complete HTML document string.
    """
    # Starting conditions
    start_html = (
        "<h2>Starting Conditions</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Start Point:</dt> '
        f'<dd>{_esc(_pt_label(start_point))} &mdash; '
        f'N: <span class="mono">{_fmt_raw(start_point.northing)}</span>, '
        f'E: <span class="mono">{_fmt_raw(start_point.easting)}</span></dd></div>\n'
        f'<div class="row"><dt>Start Azimuth:</dt> '
        f'<dd class="mono">{_esc(_angle_dms(start_azimuth))}</dd></div>\n'
        "</div>\n"
    )

    # Observation table
    obs_rows = "\n".join(
        f"<tr><td class=\"mono\">{i + 1}</td>"
        f"<td class=\"mono\">{_esc(obs)}</td></tr>"
        for i, obs in enumerate(observations)
    )
    obs_table = (
        "<h2>Observations</h2>\n<table>\n"
        "<tr><th>#</th><th>Observation</th></tr>\n"
        + obs_rows + "\n</table>\n"
    )

    # Angular closure
    ang_misc = result.angular_misclosure
    ang_tol = result.angular_tolerance
    ang_pass = abs(ang_misc.degrees) <= abs(ang_tol.degrees)
    status_class = "pass" if ang_pass else "fail"
    status_text = "PASS" if ang_pass else "FAIL"

    closure_html = (
        "<h2>Angular Closure</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Angular Misclosure:</dt> '
        f'<dd class="mono">{_esc(ang_misc.to_dms_string())}</dd></div>\n'
        f'<div class="row"><dt>Tolerance (10&Prime;&radic;n):</dt> '
        f'<dd class="mono">{_esc(ang_tol.to_dms_string())}</dd></div>\n'
        f'<div class="row"><dt>Status:</dt> '
        f'<dd class="{status_class}">{status_text}</dd></div>\n'
        "</div>\n"
    )

    # Linear closure
    lin_misc = result.linear_misclosure
    precision = result.precision_ratio
    prec_str = f"1:{precision:,.0f}" if precision > 0 else "N/A"

    linear_html = (
        "<h2>Linear Closure</h2>\n"
        '<div class="summary-box">\n'
        f'<div class="row"><dt>Closure North:</dt> '
        f'<dd class="mono">{_fmt_raw(result.closure_north)}</dd></div>\n'
        f'<div class="row"><dt>Closure East:</dt> '
        f'<dd class="mono">{_fmt_raw(result.closure_east)}</dd></div>\n'
        f'<div class="row"><dt>Linear Misclosure:</dt> '
        f'<dd class="mono">{_fmt_raw(lin_misc)}</dd></div>\n'
        f'<div class="row"><dt>Perimeter:</dt> '
        f'<dd class="mono">{_fmt_raw(result.perimeter, 2)}</dd></div>\n'
        f'<div class="row"><dt>Precision Ratio:</dt> '
        f'<dd class="mono bold">{_esc(prec_str)}</dd></div>\n'
        "</div>\n"
    )

    # Raw coordinates
    raw_rows = "\n".join(
        f"<tr><td>{_esc(_pt_label(pt))}</td>"
        f"<td class=\"right mono\">{_fmt_raw(pt.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(pt.easting)}</td></tr>"
        for pt in result.raw_points
    )
    raw_table = (
        "<h2>Raw (Unadjusted) Coordinates</h2>\n<table>\n"
        "<tr><th>Point</th><th class=\"right\">Northing</th>"
        "<th class=\"right\">Easting</th></tr>\n"
        + raw_rows + "\n</table>\n"
    )

    # Adjusted coordinates
    adj_rows = "\n".join(
        f"<tr><td>{_esc(_pt_label(pt))}</td>"
        f"<td class=\"right mono\">{_fmt_raw(pt.northing)}</td>"
        f"<td class=\"right mono\">{_fmt_raw(pt.easting)}</td></tr>"
        for pt in result.adjusted_points
    )
    adj_table = (
        "<h2>Adjusted Coordinates</h2>\n<table>\n"
        "<tr><th>Point</th><th class=\"right\">Northing</th>"
        "<th class=\"right\">Easting</th></tr>\n"
        + adj_rows + "\n</table>\n"
    )

    # SVG traverse polygon
    pts_ne = [(pt.northing, pt.easting) for pt in result.adjusted_points]
    pixels, w, h, pad = _survey_to_svg(pts_ne)
    svg_parts: list[str] = []
    if len(pixels) >= 2:
        # Draw lines between consecutive points
        for i in range(len(pixels) - 1):
            x1, y1 = pixels[i]
            x2, y2 = pixels[i + 1]
            svg_parts.append(_svg_line(x1, y1, x2, y2))
        # Close polygon if 3+ points
        if len(pixels) >= 3:
            x1, y1 = pixels[-1]
            x2, y2 = pixels[0]
            svg_parts.append(_svg_line(x1, y1, x2, y2, stroke="#999"))
        # Point markers and labels
        for i, (px, py) in enumerate(pixels):
            pt = result.adjusted_points[i]
            color = "#2c3e50" if i == 0 else "#e74c3c"
            svg_parts.append(_svg_circle(px, py, r=4, fill=color))
            svg_parts.append(_svg_text(px, py - 10, _pt_label(pt)))
    svg_html = "<h2>Traverse Diagram</h2>\n" + _build_svg("\n".join(svg_parts), w, h)

    body = (
        start_html + obs_table + closure_html + linear_html
        + raw_table + adj_table + svg_html
    )
    return _html_wrap("Traverse Run Report", body)
