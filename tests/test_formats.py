"""Tests for DXF and KML export formats."""

import math
import re
from pathlib import Path

from cogokit.core.crs import CRS
from cogokit.core.job import Job
from cogokit.core.point import Point
from cogokit.io.formats import export_dxf, export_dxf_lines, export_dxf_polyline, export_kml


def _make_job():
    """Create a small test job with 3 points."""
    job = Job(name="test")
    job.add_point(Point(northing=100.0, easting=200.0, elevation=10.0, number=1, description="A"))
    job.add_point(Point(northing=300.0, easting=400.0, elevation=20.0, number=2, description="B"))
    job.add_point(Point(northing=500.0, easting=600.0, elevation=30.0, number=3, description="C"))
    return job


def _make_points():
    """Create a list of 3 points (no job)."""
    return [
        Point(northing=100.0, easting=200.0, elevation=10.0, number=1, description="A"),
        Point(northing=300.0, easting=400.0, elevation=20.0, number=2, description="B"),
        Point(northing=500.0, easting=600.0, elevation=30.0, number=3, description="C"),
    ]


# --- export_dxf tests ---


class TestExportDxfPoints:
    """Existing POINT entity behavior."""

    def test_point_entities_written(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        assert text.count("\n0\nPOINT\n") == 3

    def test_point_layer_is_points(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "POINT":
                # group code 8 (layer) follows the entity type
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "POINTS"

    def test_dxf_structure(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        assert text.startswith("0\nSECTION\n2\nENTITIES\n")
        assert text.strip().endswith("0\nEOF")


class TestExportDxfLabels:
    """TEXT entities as point labels."""

    def test_labels_on_by_default(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        assert "\n0\nTEXT\n" in text
        assert text.count("\n0\nTEXT\n") == 3

    def test_labels_off(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out, labels=False)
        text = out.read_text()
        assert "\n0\nTEXT\n" not in text

    def test_text_layer_is_labels(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "TEXT":
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "LABELS"

    def test_text_content_is_point_number(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        lines = text.split("\n")
        text_numbers = []
        for i, line in enumerate(lines):
            if line == "TEXT":
                # group code 1 is text string
                for j in range(i + 1, len(lines) - 1):
                    if lines[j] == "1":
                        text_numbers.append(lines[j + 1])
                        break
        assert text_numbers == ["1", "2", "3"]

    def test_text_height_is_one(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "TEXT":
                for j in range(i + 1, len(lines) - 1):
                    if lines[j] == "40":
                        assert lines[j + 1] == "1.0"
                        break

    def test_text_coordinates_match_point(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.dxf"
        export_dxf(job, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "TEXT":
                # find X coordinate (group 10)
                for j in range(i + 1, len(lines) - 1):
                    if lines[j] == "10":
                        x_val = float(lines[j + 1])
                        assert x_val in [200.0, 400.0, 600.0]
                        break


# --- export_dxf_lines tests ---


class TestExportDxfLines:
    """LINE entities connecting sequential points."""

    def test_line_count(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out)
        text = out.read_text()
        # 3 points → 2 lines
        assert text.count("\n0\nLINE\n") == 2

    def test_line_layer_default(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "LINE":
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "LINES"

    def test_line_layer_custom(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out, layer="BOUNDARY")
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "LINE":
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "BOUNDARY"

    def test_line_connects_sequential_points(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out)
        text = out.read_text()
        lines = text.split("\n")
        line_entities = []
        for i, line in enumerate(lines):
            if line == "LINE":
                coords = {}
                for j in range(i + 1, len(lines) - 1):
                    if lines[j] == "0":
                        break
                    if lines[j] in ("10", "20", "30", "11", "21", "31"):
                        coords[lines[j]] = float(lines[j + 1])
                line_entities.append(coords)
        # First LINE: point1 → point2
        assert line_entities[0]["10"] == 200.0  # X1 = easting of point 1
        assert line_entities[0]["20"] == 100.0  # Y1 = northing of point 1 (note: in existing code Y=northing)
        assert line_entities[0]["11"] == 400.0  # X2 = easting of point 2
        assert line_entities[0]["21"] == 300.0  # Y2 = northing of point 2

    def test_accepts_job(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(job, out)
        text = out.read_text()
        assert text.count("\n0\nLINE\n") == 2

    def test_dxf_structure(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out)
        text = out.read_text()
        assert text.startswith("0\nSECTION\n2\nENTITIES\n")
        assert text.strip().endswith("0\nEOF")

    def test_single_point_no_lines(self, tmp_path: Path):
        points = [_make_points()[0]]
        out = tmp_path / "lines.dxf"
        export_dxf_lines(points, out)
        text = out.read_text()
        assert "\n0\nLINE\n" not in text


# --- export_dxf_polyline tests ---


class TestExportDxfPolyline:
    """LWPOLYLINE entity."""

    def test_lwpolyline_entity_written(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out)
        text = out.read_text()
        assert "\n0\nLWPOLYLINE\n" in text or text.startswith("0\nLWPOLYLINE\n")

    def test_polyline_layer_default(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "LWPOLYLINE":
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "POLYLINE"

    def test_polyline_layer_custom(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out, layer="TRAVERSE")
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "LWPOLYLINE":
                layer_idx = lines.index("8", i + 1)
                assert lines[layer_idx + 1] == "TRAVERSE"

    def test_vertex_count(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "90":
                assert lines[i + 1] == "3"
                break

    def test_open_polyline(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out, closed=False)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "70":
                assert lines[i + 1] == "0"
                break

    def test_closed_polyline(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out, closed=True)
        text = out.read_text()
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line == "70":
                assert lines[i + 1] == "1"
                break

    def test_vertex_coordinates(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out)
        text = out.read_text()
        lines = text.split("\n")
        # Find LWPOLYLINE entity, then collect vertex X coords (group 10)
        # Iterate as code/value pairs (step 2) to avoid confusing
        # a value of "0" (closed flag) with a group code "0".
        x_coords = []
        in_lwpoly = False
        i = 0
        while i < len(lines) - 1:
            code, value = lines[i], lines[i + 1]
            if code == "0" and value == "LWPOLYLINE":
                in_lwpoly = True
            elif in_lwpoly and code == "0":
                break  # next entity
            elif in_lwpoly and code == "10":
                x_coords.append(float(value))
            i += 2
        assert x_coords == [200.0, 400.0, 600.0]

    def test_accepts_job(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(job, out)
        text = out.read_text()
        assert "LWPOLYLINE" in text

    def test_dxf_polyline_structure(self, tmp_path: Path):
        points = _make_points()
        out = tmp_path / "poly.dxf"
        export_dxf_polyline(points, out)
        text = out.read_text()
        assert text.startswith("0\nSECTION\n2\nENTITIES\n")
        assert text.strip().endswith("0\nEOF")


# --- export_kml tests ---


def _extract_kml_coordinates(kml_text: str) -> list[tuple[float, float, float]]:
    """Extract all coordinate triples from KML text."""
    coords = []
    for match in re.finditer(r"<coordinates>(.*?)</coordinates>", kml_text):
        parts = match.group(1).strip().split(",")
        lon, lat, elev = float(parts[0]), float(parts[1]), float(parts[2])
        coords.append((lon, lat, elev))
    return coords


class TestExportKml:
    """KML export with CRS-aware coordinate transformation."""

    def test_kml_structure(self, tmp_path: Path):
        """KML should have valid XML structure."""
        job = _make_job()
        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()
        assert '<?xml version="1.0"' in text
        assert "<kml" in text
        assert "<Document>" in text
        assert "</Document>" in text
        assert "</kml>" in text

    def test_kml_placemarks(self, tmp_path: Path):
        """Each point should produce a Placemark."""
        job = _make_job()
        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()
        assert text.count("<Placemark>") == 3

    def test_kml_no_crs_backward_compat(self, tmp_path: Path):
        """Without CRS, coordinates should be written as-is (lon=easting, lat=northing)."""
        job = Job(name="No CRS")
        # Assume coords are already lat/lon degrees: northing=lat, easting=lon
        job.add_point(Point(northing=43.6532, easting=-79.3832, elevation=76.0, number=1))
        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()

        coords = _extract_kml_coordinates(text)
        assert len(coords) == 1
        lon, lat, elev = coords[0]
        # KML order: lon, lat, elev
        assert math.isclose(lon, -79.3832, abs_tol=0.0001)
        assert math.isclose(lat, 43.6532, abs_tol=0.0001)
        assert math.isclose(elev, 76.0, abs_tol=0.01)

    def test_kml_coordinate_order_is_lon_lat_elev(self, tmp_path: Path):
        """KML coordinates must be longitude,latitude,elevation."""
        job = Job(name="Order test")
        job.add_point(Point(northing=45.0, easting=-75.0, elevation=100.0, number=1))
        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()

        match = re.search(r"<coordinates>(.*?)</coordinates>", text)
        assert match is not None
        parts = match.group(1).strip().split(",")
        assert len(parts) == 3
        # First value should be easting/longitude (-75.0)
        assert float(parts[0]) == -75.0
        # Second value should be northing/latitude (45.0)
        assert float(parts[1]) == 45.0

    def test_kml_utm_job_transforms_to_latlon(self, tmp_path: Path):
        """UTM coordinates should be transformed to WGS84 lat/lon degrees."""
        from cogokit.geodetic.projections import geodetic_to_utm

        # Known: Toronto is ~43.65N, ~79.38W -> UTM Zone 17N
        lat_rad = math.radians(43.6532)
        lon_rad = math.radians(-79.3832)
        utm_result = geodetic_to_utm(lat_rad, lon_rad, zone=17)

        job = Job(name="UTM Job")
        job.crs = CRS.utm(zone=17)
        job.add_point(Point(
            northing=utm_result.northing,
            easting=utm_result.easting,
            elevation=76.0,
            number=1,
            description="Toronto",
        ))

        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()

        coords = _extract_kml_coordinates(text)
        assert len(coords) == 1
        lon, lat, elev = coords[0]
        # Should be close to Toronto's lat/lon in degrees
        assert math.isclose(lat, 43.6532, abs_tol=0.001)
        assert math.isclose(lon, -79.3832, abs_tol=0.001)
        assert math.isclose(elev, 76.0, abs_tol=0.01)

    def test_kml_geodetic_crs_converts_radians_to_degrees(self, tmp_path: Path):
        """Geodetic CRS points (radians) should be converted to degrees for KML."""
        job = Job(name="Geodetic Job")
        job.crs = CRS.geodetic()
        job.add_point(Point(
            northing=math.radians(43.6532),  # lat in radians
            easting=math.radians(-79.3832),  # lon in radians
            elevation=76.0,
            number=1,
        ))

        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()

        coords = _extract_kml_coordinates(text)
        assert len(coords) == 1
        lon, lat, elev = coords[0]
        assert math.isclose(lat, 43.6532, abs_tol=0.0001)
        assert math.isclose(lon, -79.3832, abs_tol=0.0001)

    def test_kml_crs_parameter_overrides_job_crs(self, tmp_path: Path):
        """The crs parameter should override job.crs."""
        from cogokit.geodetic.projections import geodetic_to_utm

        lat_rad = math.radians(43.6532)
        lon_rad = math.radians(-79.3832)
        utm_result = geodetic_to_utm(lat_rad, lon_rad, zone=17)

        job = Job(name="Override test")
        # Job has no CRS set, but we pass one explicitly
        job.add_point(Point(
            northing=utm_result.northing,
            easting=utm_result.easting,
            elevation=0.0,
            number=1,
        ))

        out = tmp_path / "test.kml"
        export_kml(job, out, crs=CRS.utm(zone=17))
        text = out.read_text()

        coords = _extract_kml_coordinates(text)
        assert len(coords) == 1
        lon, lat, _ = coords[0]
        assert math.isclose(lat, 43.6532, abs_tol=0.001)
        assert math.isclose(lon, -79.3832, abs_tol=0.001)

    def test_kml_multiple_utm_points(self, tmp_path: Path):
        """Multiple UTM points should all be transformed correctly."""
        from cogokit.geodetic.projections import geodetic_to_utm

        locations = [
            (43.6532, -79.3832, "Toronto"),
            (43.6500, -79.3800, "Nearby"),
        ]

        job = Job(name="Multi-point")
        job.crs = CRS.utm(zone=17)

        for i, (lat_deg, lon_deg, desc) in enumerate(locations, start=1):
            utm = geodetic_to_utm(math.radians(lat_deg), math.radians(lon_deg), zone=17)
            job.add_point(Point(
                northing=utm.northing, easting=utm.easting,
                elevation=0.0, number=i, description=desc,
            ))

        out = tmp_path / "test.kml"
        export_kml(job, out)
        text = out.read_text()

        coords = _extract_kml_coordinates(text)
        assert len(coords) == 2
        for (lon, lat, _), (expected_lat, expected_lon, _) in zip(coords, locations):
            assert math.isclose(lat, expected_lat, abs_tol=0.001)
            assert math.isclose(lon, expected_lon, abs_tol=0.001)

    def test_kml_no_todo_comment(self, tmp_path: Path):
        """The TODO comment should be removed from the export_kml function."""
        import inspect
        from cogokit.io.formats import export_kml as fn
        source = inspect.getsource(fn)
        assert "TODO" not in source
