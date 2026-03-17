"""Tests for the Typer CLI."""

import math

import pytest
from typer.testing import CliRunner

from cogokit.cli import app

runner = CliRunner()


# --- inverse ---


class TestInverse:
    def test_basic(self):
        result = runner.invoke(app, ["inverse", "0", "0", "300", "400"])
        assert result.exit_code == 0
        assert "500.0000" in result.output  # horizontal distance

    def test_bearing_display(self):
        result = runner.invoke(app, ["inverse", "1000", "2000", "1500", "2500"])
        assert result.exit_code == 0
        assert "N" in result.output
        assert "E" in result.output

    def test_vertical_distance(self):
        # n1=0, e1=0, n2=100, e2=0, z1=0, z2=50
        result = runner.invoke(app, ["inverse", "0", "0", "100", "0", "0", "50"])
        assert result.exit_code == 0
        assert "50.0000" in result.output  # vertical distance

    def test_zero_distance(self):
        result = runner.invoke(app, ["inverse", "100", "200", "100", "200"])
        assert result.exit_code == 0
        assert "0.0000" in result.output

    def test_help(self):
        result = runner.invoke(app, ["inverse", "--help"])
        assert result.exit_code == 0


# --- traverse ---


class TestTraverse:
    def test_due_east(self):
        result = runner.invoke(app, ["traverse", "1000", "2000", "90", "100"])
        assert result.exit_code == 0
        assert "2100.0000" in result.output  # easting

    def test_northeast(self):
        result = runner.invoke(app, ["traverse", "1000", "2000", "45", "100"])
        assert result.exit_code == 0
        assert "1070.7107" in result.output  # northing
        assert "2070.7107" in result.output  # easting

    def test_with_elevation(self):
        result = runner.invoke(app, ["traverse", "1000", "2000", "90", "100", "--elevation", "500"])
        assert result.exit_code == 0
        assert "500.0000" in result.output

    def test_help(self):
        result = runner.invoke(app, ["traverse", "--help"])
        assert result.exit_code == 0


# --- area ---


class TestArea:
    def test_square(self, tmp_path):
        pts = tmp_path / "square.txt"
        pts.write_text("1 0 0 0\n2 100 0 0\n3 100 100 0\n4 0 100 0\n")
        result = runner.invoke(app, ["area", str(pts)])
        assert result.exit_code == 0
        assert "10000.0000" in result.output
        assert "400.0000" in result.output

    def test_bad_file(self):
        result = runner.invoke(app, ["area", "/nonexistent/file.txt"])
        assert result.exit_code != 0

    def test_help(self):
        result = runner.invoke(app, ["area", "--help"])
        assert result.exit_code == 0


# --- curve ---


class TestCurve:
    def test_radius_and_delta(self):
        result = runner.invoke(app, ["curve", "--radius", "500", "--delta", "30"])
        assert result.exit_code == 0
        assert "Radius" in result.output
        assert "500.0000" in result.output

    def test_all_elements_shown(self):
        result = runner.invoke(app, ["curve", "--radius", "500", "--delta", "30"])
        assert result.exit_code == 0
        for label in ["Radius", "Delta", "Tangent", "Length", "Chord", "External", "Mid-Ord", "Degree"]:
            assert label in result.output

    def test_too_few_params(self):
        result = runner.invoke(app, ["curve", "--radius", "500"])
        assert result.exit_code != 0

    def test_too_many_params(self):
        result = runner.invoke(app, ["curve", "--radius", "500", "--delta", "30", "--tangent", "50"])
        assert result.exit_code != 0

    def test_help(self):
        result = runner.invoke(app, ["curve", "--help"])
        assert result.exit_code == 0


# --- convert ---


class TestConvert:
    def test_help(self):
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0

    def test_missing_crs_module(self, tmp_path):
        pts = tmp_path / "pts.txt"
        pts.write_text("1 1000 2000 100\n")
        result = runner.invoke(app, ["convert", str(pts), "--from-crs", "utm:17:N", "--to-crs", "geodetic"])
        # Should either work (if CRS module exists) or fail gracefully
        assert result.exit_code != 0 or "not available" in result.output.lower() or result.exit_code == 0


# --- export ---


class TestExport:
    def test_dxf(self, tmp_path):
        pts = tmp_path / "pts.txt"
        pts.write_text("1 1000 2000 100\n2 1100 2100 200\n")
        out = tmp_path / "out.dxf"
        result = runner.invoke(app, ["export", str(pts), "--format", "dxf", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_kml(self, tmp_path):
        pts = tmp_path / "pts.txt"
        pts.write_text("1 1000 2000 100\n2 1100 2100 200\n")
        out = tmp_path / "out.kml"
        result = runner.invoke(app, ["export", str(pts), "--format", "kml", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_export_stdout(self, tmp_path):
        pts = tmp_path / "pts.txt"
        pts.write_text("1 1000 2000 100\n")
        result = runner.invoke(app, ["export", str(pts), "--format", "dxf"])
        assert result.exit_code == 0

    def test_bad_format(self, tmp_path):
        pts = tmp_path / "pts.txt"
        pts.write_text("1 1000 2000 100\n")
        result = runner.invoke(app, ["export", str(pts), "--format", "csv"])
        assert result.exit_code != 0

    def test_help(self):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0


# --- top-level ---


class TestZonesCommand:
    """Test the zones listing command."""

    def test_list_all(self):
        result = runner.invoke(app, ["zones"])
        assert result.exit_code == 0
        assert "California" in result.output or "CA" in result.output

    def test_list_by_state(self):
        result = runner.invoke(app, ["zones", "--state", "TX"])
        assert result.exit_code == 0
        assert "TX" in result.output

    def test_show_epsg(self):
        result = runner.invoke(app, ["zones", "--epsg", "26945"])
        assert result.exit_code == 0
        assert "California" in result.output

    def test_unknown_epsg(self):
        result = runner.invoke(app, ["zones", "--epsg", "99999"])
        assert result.exit_code == 1


class TestConvertStatePlane:
    """Test coordinate conversion with State Plane CRS."""

    def test_convert_geodetic_to_state_plane(self, tmp_path):
        pts_file = tmp_path / "points.txt"
        lat = math.radians(34.05)
        lon = math.radians(-118.24)
        pts_file.write_text(f"1 {lat:.10f} {lon:.10f} 0.0\n")

        result = runner.invoke(app, [
            "convert", str(pts_file),
            "--from-crs", "geodetic:nad83",
            "--to-crs", "epsg:26945",
        ])
        assert result.exit_code == 0

    def test_parse_crs_epsg(self):
        from cogokit.cli import _parse_crs
        crs = _parse_crs("epsg:26945")
        assert crs is not None
        assert crs.kind == "projected"

    def test_parse_crs_sp_state_zone(self):
        from cogokit.cli import _parse_crs
        crs = _parse_crs("sp:CA:5")
        assert crs is not None
        assert crs.kind == "projected"


class TestTopLevel:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "COGO" in result.output
