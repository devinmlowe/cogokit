"""Tests for HTML report generation (cogokit.io.reports)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cogokit.cogo.inverse import InverseResult, inverse
from cogokit.core import Angle, Point
from cogokit.core.job import Job
from cogokit.io.reports import (
    report_area,
    report_convert,
    report_curve,
    report_export,
    report_inverse,
    report_traverse,
    report_traverse_run,
    report_zones,
    write_report,
)
from cogokit.solvers.horizontal_curve import CurveElements, solve_curve
from cogokit.surveying.workflow import TraverseWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_html_doc(html: str, expected_title: str) -> None:
    """Assert the HTML is a valid document with correct title."""
    assert html.startswith("<!DOCTYPE html>")
    assert f"<title>{expected_title}</title>" in html
    assert "</html>" in html


def _make_traverse_result():
    """Build a TraverseResult for testing using a simple square traverse."""
    start = Point(northing=1000.0, easting=5000.0, elevation=100.0, number=1)
    wf = TraverseWorkflow(start_point=start, start_azimuth=270.0000)
    # Perfect square: 4 legs of 100 ft at right angles
    wf.add_leg(occupied=1, backsight=0, foresight=2, angle_dms=90.0000, distance=100.0)
    wf.add_leg(occupied=2, backsight=1, foresight=3, angle_dms=90.0000, distance=100.0)
    wf.add_leg(occupied=3, backsight=2, foresight=4, angle_dms=90.0000, distance=100.0)
    wf.add_leg(occupied=4, backsight=3, foresight=1, angle_dms=90.0000, distance=100.0)
    return wf.run(), start


# ---------------------------------------------------------------------------
# Report: inverse
# ---------------------------------------------------------------------------

class TestReportInverse:
    def test_produces_valid_html(self):
        p1 = Point(northing=0.0, easting=0.0, number=1)
        p2 = Point(northing=300.0, easting=400.0, number=2)
        result = inverse(p1, p2)
        html = report_inverse(p1, p2, result)
        _assert_html_doc(html, "Inverse Report")

    def test_contains_key_values(self):
        p1 = Point(northing=0.0, easting=0.0, number=1)
        p2 = Point(northing=300.0, easting=400.0, number=2)
        result = inverse(p1, p2)
        html = report_inverse(p1, p2, result)
        assert "500.0000" in html  # horizontal distance
        assert "Bearing" in html
        assert "Horizontal Distance" in html

    def test_has_svg(self):
        p1 = Point(northing=0.0, easting=0.0, number=1)
        p2 = Point(northing=300.0, easting=400.0, number=2)
        result = inverse(p1, p2)
        html = report_inverse(p1, p2, result)
        assert "<svg" in html


# ---------------------------------------------------------------------------
# Report: traverse (single shot)
# ---------------------------------------------------------------------------

class TestReportTraverse:
    def test_produces_valid_html(self):
        origin = Point(northing=1000.0, easting=2000.0, number=1)
        az_rad = math.radians(45.0)
        distance = 100.0
        from cogokit.cogo.traverse import traverse
        result_pt = traverse(origin, az_rad, distance, 0.0)
        html = report_traverse(origin, az_rad, distance, result_pt)
        _assert_html_doc(html, "Traverse Report")

    def test_contains_key_values(self):
        origin = Point(northing=1000.0, easting=2000.0, number=1)
        az_rad = math.radians(90.0)
        distance = 100.0
        from cogokit.cogo.traverse import traverse
        result_pt = traverse(origin, az_rad, distance, 0.0)
        html = report_traverse(origin, az_rad, distance, result_pt)
        assert "Distance" in html
        assert "Azimuth" in html
        assert "1,000.0000" in html or "1000.0000" in html

    def test_has_svg(self):
        origin = Point(northing=1000.0, easting=2000.0, number=1)
        az_rad = math.radians(45.0)
        distance = 100.0
        from cogokit.cogo.traverse import traverse
        result_pt = traverse(origin, az_rad, distance, 0.0)
        html = report_traverse(origin, az_rad, distance, result_pt)
        assert "<svg" in html


# ---------------------------------------------------------------------------
# Report: area
# ---------------------------------------------------------------------------

class TestReportArea:
    def test_produces_valid_html(self):
        pts = [
            Point(northing=0, easting=0, number=1),
            Point(northing=100, easting=0, number=2),
            Point(northing=100, easting=100, number=3),
            Point(northing=0, easting=100, number=4),
        ]
        html = report_area(pts, 10000.0, 400.0)
        _assert_html_doc(html, "Area Report")

    def test_contains_key_values(self):
        pts = [
            Point(northing=0, easting=0, number=1),
            Point(northing=100, easting=0, number=2),
            Point(northing=100, easting=100, number=3),
            Point(northing=0, easting=100, number=4),
        ]
        html = report_area(pts, 10000.0, 400.0)
        assert "10,000.00" in html or "10000.00" in html
        assert "400.00" in html
        assert "acres" in html

    def test_has_svg(self):
        pts = [
            Point(northing=0, easting=0, number=1),
            Point(northing=100, easting=0, number=2),
            Point(northing=100, easting=100, number=3),
            Point(northing=0, easting=100, number=4),
        ]
        html = report_area(pts, 10000.0, 400.0)
        assert "<svg" in html


# ---------------------------------------------------------------------------
# Report: curve
# ---------------------------------------------------------------------------

class TestReportCurve:
    def test_produces_valid_html(self):
        c = solve_curve(R=500.0, delta=math.radians(30.0))
        html = report_curve({"R": 500.0, "delta": math.radians(30.0)}, c)
        _assert_html_doc(html, "Horizontal Curve Report")

    def test_contains_key_values(self):
        c = solve_curve(R=500.0, delta=math.radians(30.0))
        html = report_curve({"R": 500.0, "delta": math.radians(30.0)}, c)
        assert "500.0000" in html
        assert "Radius" in html
        assert "Tangent" in html
        assert "Arc Length" in html or "L (" in html

    def test_has_svg(self):
        c = solve_curve(R=500.0, delta=math.radians(30.0))
        html = report_curve({"R": 500.0, "delta": math.radians(30.0)}, c)
        assert "<svg" in html


# ---------------------------------------------------------------------------
# Report: zones
# ---------------------------------------------------------------------------

class TestReportZones:
    def test_produces_valid_html(self):
        from cogokit.geodetic.state_plane import list_zones
        zone_list = list_zones(state="CA")
        html = report_zones(zone_list, state_filter="CA")
        _assert_html_doc(html, "State Plane Zones (CA)")

    def test_contains_key_values(self):
        from cogokit.geodetic.state_plane import list_zones
        zone_list = list_zones(state="CA")
        html = report_zones(zone_list, state_filter="CA")
        assert "CA" in html
        assert "California" in html
        assert "Zones found" in html

    def test_no_filter(self):
        from cogokit.geodetic.state_plane import list_zones
        zone_list = list_zones()
        html = report_zones(zone_list)
        _assert_html_doc(html, "State Plane Zones")
        assert "Zones found" in html

    def test_single_zone_in_list(self):
        from cogokit.geodetic.state_plane import get_zone
        zone = get_zone(26945)
        html = report_zones([zone], state_filter="CA")
        _assert_html_doc(html, "State Plane Zones (CA)")
        assert "26945" in html


# ---------------------------------------------------------------------------
# Report: convert
# ---------------------------------------------------------------------------

class TestReportConvert:
    def test_produces_valid_html(self):
        orig = [Point(northing=1000, easting=2000, number=1)]
        xform = [Point(northing=1001, easting=2001, number=1)]
        html = report_convert("utm:17:N", "geodetic:wgs84", orig, xform)
        _assert_html_doc(html, "Coordinate Conversion Report")

    def test_contains_key_values(self):
        orig = [Point(northing=1000, easting=2000, number=1)]
        xform = [Point(northing=1001, easting=2001, number=1)]
        html = report_convert("utm:17:N", "geodetic:wgs84", orig, xform)
        assert "utm:17:N" in html
        assert "geodetic:wgs84" in html
        assert "Source CRS" in html
        assert "Target CRS" in html
        assert "Points converted" in html


# ---------------------------------------------------------------------------
# Report: export
# ---------------------------------------------------------------------------

class TestReportExport:
    def test_produces_valid_html(self):
        html = report_export("TestJob", 5, "DXF", "/tmp/out.dxf")
        _assert_html_doc(html, "Export Report")

    def test_contains_key_values(self):
        html = report_export("TestJob", 5, "DXF", "/tmp/out.dxf")
        assert "TestJob" in html
        assert "DXF" in html
        assert "5" in html
        assert "/tmp/out.dxf" in html
        assert "Points exported" in html


# ---------------------------------------------------------------------------
# Report: traverse-run
# ---------------------------------------------------------------------------

class TestReportTraverseRun:
    def test_produces_valid_html(self):
        result, start = _make_traverse_result()
        obs = [
            "1,0,2,90.0000,100.0",
            "2,1,3,90.0000,100.0",
            "3,2,4,90.0000,100.0",
            "4,3,1,90.0000,100.0",
        ]
        az_rad = Angle.from_hp_notation(270.0000).radians
        html = report_traverse_run(result, obs, start, az_rad)
        _assert_html_doc(html, "Traverse Run Report")

    def test_contains_key_values(self):
        result, start = _make_traverse_result()
        obs = [
            "1,0,2,90.0000,100.0",
            "2,1,3,90.0000,100.0",
            "3,2,4,90.0000,100.0",
            "4,3,1,90.0000,100.0",
        ]
        az_rad = Angle.from_hp_notation(270.0000).radians
        html = report_traverse_run(result, obs, start, az_rad)
        assert "Angular Misclosure" in html
        assert "Linear Misclosure" in html
        assert "Precision Ratio" in html
        assert "Adjusted Coordinates" in html

    def test_has_svg(self):
        result, start = _make_traverse_result()
        obs = [
            "1,0,2,90.0000,100.0",
            "2,1,3,90.0000,100.0",
            "3,2,4,90.0000,100.0",
            "4,3,1,90.0000,100.0",
        ]
        az_rad = Angle.from_hp_notation(270.0000).radians
        html = report_traverse_run(result, obs, start, az_rad)
        assert "<svg" in html

    def test_observations_listed(self):
        result, start = _make_traverse_result()
        obs = [
            "1,0,2,90.0000,100.0",
            "2,1,3,90.0000,100.0",
            "3,2,4,90.0000,100.0",
            "4,3,1,90.0000,100.0",
        ]
        az_rad = Angle.from_hp_notation(270.0000).radians
        html = report_traverse_run(result, obs, start, az_rad)
        assert "Observations" in html
        assert "1,0,2,90.0000,100.0" in html


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_auto_naming_in_directory(self, tmp_path):
        html = "<html>test</html>"
        out = write_report(html, tmp_path, "inverse")
        assert out.exists()
        assert out.suffix == ".html"
        assert "inverse_" in out.name
        assert out.read_text() == html

    def test_explicit_path(self, tmp_path):
        target = tmp_path / "my_report.html"
        html = "<html>test</html>"
        out = write_report(html, target, "area")
        assert out == target
        assert target.exists()
        assert target.read_text() == html

    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "report.html"
        html = "<html>test</html>"
        out = write_report(html, target, "curve")
        assert out == target
        assert target.exists()

    def test_auto_name_contains_timestamp(self, tmp_path):
        html = "<html>test</html>"
        out = write_report(html, tmp_path, "zones")
        # Name should be zones_YYYYMMDD_HHMMSS.html
        stem = out.stem  # e.g. "zones_20260216_143000"
        assert stem.startswith("zones_")
        assert len(stem) > len("zones_")
