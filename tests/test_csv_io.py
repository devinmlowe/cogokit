"""Tests for CSV import/export."""

import io
import math
from pathlib import Path

from cogokit.core.job import Job
from cogokit.core.point import Point
from cogokit.io.csv_io import read_csv, write_csv


def _make_job():
    """Create a small test job with 3 points."""
    job = Job(name="TestCSV")
    job.add_point(Point(northing=1000.0, easting=2000.0, elevation=100.0, number=1, description="BM1"))
    job.add_point(Point(northing=1100.0, easting=2100.0, elevation=101.0, number=2, description="IP"))
    job.add_point(Point(northing=1200.0, easting=2200.0, elevation=102.0, number=3, description="EP"))
    return job


# --- write_csv tests ---


class TestWriteCSV:
    def test_write_header(self):
        job = _make_job()
        buf = io.StringIO()
        write_csv(job, buf)
        buf.seek(0)
        header = buf.readline().strip()
        assert header == "number,northing,easting,elevation,description"

    def test_write_data_rows(self):
        job = _make_job()
        buf = io.StringIO()
        write_csv(job, buf)
        buf.seek(0)
        lines = buf.readlines()
        # 1 header + 3 data rows
        assert len(lines) == 4

    def test_write_custom_columns(self):
        job = _make_job()
        buf = io.StringIO()
        write_csv(job, buf, columns=["number", "easting", "northing"])
        buf.seek(0)
        header = buf.readline().strip()
        assert header == "number,easting,northing"
        first_row = buf.readline().strip()
        parts = first_row.split(",")
        assert parts[0] == "1"
        assert math.isclose(float(parts[1]), 2000.0)
        assert math.isclose(float(parts[2]), 1000.0)

    def test_write_precision(self):
        job = Job(name="prec")
        job.add_point(Point(northing=1000.12345, easting=2000.6789, elevation=50.0, number=1))
        buf = io.StringIO()
        write_csv(job, buf, precision=2)
        buf.seek(0)
        buf.readline()  # skip header
        row = buf.readline().strip()
        parts = row.split(",")
        assert parts[1] == "1000.12"
        assert parts[2] == "2000.68"

    def test_write_to_file(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "test.csv"
        write_csv(job, out)
        text = out.read_text()
        assert text.startswith("number,")
        assert "BM1" in text


# --- read_csv tests ---


class TestReadCSV:
    def test_read_with_header(self):
        data = "number,northing,easting,elevation,description\n1,1000.0,2000.0,100.0,BM1\n"
        job = read_csv(io.StringIO(data))
        assert job.point_count == 1
        p = job.get_point(1)
        assert p is not None
        assert math.isclose(p.northing, 1000.0)
        assert p.description == "BM1"

    def test_read_explicit_columns(self):
        data = "1,1000.0,2000.0,100.0,BM1\n2,1100.0,2100.0,101.0,IP\n"
        job = read_csv(
            io.StringIO(data),
            columns=["number", "northing", "easting", "elevation", "description"],
            has_header=False,
        )
        assert job.point_count == 2
        p2 = job.get_point(2)
        assert p2 is not None
        assert math.isclose(p2.easting, 2100.0)
        assert p2.description == "IP"

    def test_read_reordered_columns(self):
        data = "easting,northing,number,elevation\n2000.0,1000.0,1,100.0\n"
        job = read_csv(io.StringIO(data))
        p = job.get_point(1)
        assert p is not None
        assert math.isclose(p.northing, 1000.0)
        assert math.isclose(p.easting, 2000.0)

    def test_read_header_aliases(self):
        """Common aliases like 'N', 'E', 'pt' should be recognized."""
        data = "pt,N,E,elev,desc\n1,1000.0,2000.0,100.0,BM1\n"
        job = read_csv(io.StringIO(data))
        p = job.get_point(1)
        assert p is not None
        assert math.isclose(p.northing, 1000.0)
        assert math.isclose(p.easting, 2000.0)
        assert math.isclose(p.elevation, 100.0)
        assert p.description == "BM1"

    def test_read_case_insensitive_headers(self):
        data = "Number,Northing,Easting,Elevation,Description\n1,500.0,600.0,50.0,CP\n"
        job = read_csv(io.StringIO(data))
        assert job.point_count == 1
        p = job.get_point(1)
        assert p is not None
        assert math.isclose(p.northing, 500.0)

    def test_read_missing_elevation(self):
        data = "number,northing,easting\n1,1000.0,2000.0\n"
        job = read_csv(io.StringIO(data))
        p = job.get_point(1)
        assert p is not None
        assert math.isclose(p.elevation, 0.0)

    def test_read_missing_description(self):
        data = "number,northing,easting,elevation\n1,1000.0,2000.0,100.0\n"
        job = read_csv(io.StringIO(data))
        p = job.get_point(1)
        assert p is not None
        assert p.description == ""

    def test_read_from_file(self, tmp_path: Path):
        csv_file = tmp_path / "points.csv"
        csv_file.write_text("number,northing,easting,elevation\n1,1000.0,2000.0,100.0\n")
        job = read_csv(csv_file)
        assert job.point_count == 1
        assert job.name == "points"


# --- Round-trip tests ---


class TestCSVRoundTrip:
    def test_round_trip_file(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "round.csv"
        write_csv(job, out)
        job2 = read_csv(out)
        assert job2.point_count == 3
        for p_orig in job.points():
            p_new = job2.get_point(p_orig.number)
            assert p_new is not None
            assert math.isclose(p_orig.northing, p_new.northing, abs_tol=0.001)
            assert math.isclose(p_orig.easting, p_new.easting, abs_tol=0.001)
            assert math.isclose(p_orig.elevation, p_new.elevation, abs_tol=0.001)
            assert p_orig.description == p_new.description

    def test_round_trip_stringio(self):
        job = _make_job()
        buf = io.StringIO()
        write_csv(job, buf)
        buf.seek(0)
        job2 = read_csv(buf)
        assert job2.point_count == job.point_count

    def test_round_trip_custom_columns(self, tmp_path: Path):
        job = _make_job()
        out = tmp_path / "custom.csv"
        write_csv(job, out, columns=["number", "easting", "northing", "elevation"])
        job2 = read_csv(out)
        assert job2.point_count == 3
        p1_orig = job.get_point(1)
        p1_new = job2.get_point(1)
        assert p1_new is not None
        assert math.isclose(p1_orig.northing, p1_new.northing, abs_tol=0.001)
        assert math.isclose(p1_orig.easting, p1_new.easting, abs_tol=0.001)
