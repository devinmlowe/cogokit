"""Tests for ASCII I/O: read/write delimited point files."""

import io
import math
from pathlib import Path

from cogokit.core import Job, Point
from cogokit.io import Delimiter, read_points, write_points

SAMPLE_DIR = Path(__file__).parent.parent / "original" / "ASCII"


class TestReadSampleFiles:
    def test_read_area(self):
        job = read_points(SAMPLE_DIR / "AREA.txt")
        assert job.name == "AREA"
        assert job.point_count == 6
        p10 = job.get_point(10)
        assert p10 is not None
        assert math.isclose(p10.northing, 3000.0)
        assert math.isclose(p10.easting, 3000.0)
        assert p10.description == "CORNER"

    def test_read_compass1(self):
        job = read_points(SAMPLE_DIR / "COMPASS1.txt")
        assert job.name == "COMPASS1"
        assert job.point_count == 7
        p20 = job.get_point(20)
        assert p20 is not None
        assert math.isclose(p20.northing, 3102.894, abs_tol=0.001)
        assert p20.description == "CN"

    def test_read_compass2(self):
        job = read_points(SAMPLE_DIR / "COMPASS2.txt")
        assert job.point_count == 6

    def test_read_helmerts(self):
        job = read_points(SAMPLE_DIR / "HELMERTS.txt")
        assert job.point_count == 11
        p50 = job.get_point(50)
        assert p50 is not None
        assert math.isclose(p50.elevation, 100.0)

    def test_read_regress(self):
        job = read_points(SAMPLE_DIR / "REGRESS.txt")
        assert job.point_count == 6


class TestReadFromStringIO:
    def test_space_delimited(self):
        data = "1 100.0 200.0 10.0 STAKE\n2 300.0 400.0 20.0 HUB\n"
        job = read_points(io.StringIO(data))
        assert job.point_count == 2
        p = job.get_point(1)
        assert p is not None
        assert p.description == "STAKE"

    def test_comma_delimited(self):
        data = "1,100.0,200.0,10.0,IP\n2,300.0,400.0,20.0,EP\n"
        job = read_points(io.StringIO(data))
        assert job.point_count == 2

    def test_tab_delimited(self):
        data = "1\t100.0\t200.0\t10.0\tCP\n"
        job = read_points(io.StringIO(data))
        assert job.point_count == 1

    def test_skip_comments_and_blanks(self):
        data = "# header\n\n1 100.0 200.0 10.0\n"
        job = read_points(io.StringIO(data))
        assert job.point_count == 1

    def test_no_description(self):
        data = "1 100.0 200.0 10.0\n"
        job = read_points(io.StringIO(data))
        p = job.get_point(1)
        assert p is not None
        assert p.description == ""


class TestWritePoints:
    def test_round_trip_space(self):
        job = Job(name="test")
        job.add_point(Point(northing=100.0, easting=200.0, elevation=10.0, number=1, description="A"))
        job.add_point(Point(northing=300.0, easting=400.0, elevation=20.0, number=2, description="B"))

        buf = io.StringIO()
        write_points(job, buf)
        buf.seek(0)
        job2 = read_points(buf)
        assert job2.point_count == 2
        assert job2.get_point(1) == job.get_point(1)
        assert job2.get_point(2) == job.get_point(2)

    def test_round_trip_csv(self):
        job = Job(name="test")
        job.add_point(Point(northing=555.5, easting=666.6, elevation=77.7, number=5, description="MARK"))

        buf = io.StringIO()
        write_points(job, buf, delimiter=Delimiter.COMMA)
        buf.seek(0)
        job2 = read_points(buf)
        assert job2.get_point(5) == job.get_point(5)

    def test_round_trip_sample_file(self):
        """Read a sample file, write it, read it back, verify point data matches."""
        original = read_points(SAMPLE_DIR / "AREA.txt")
        buf = io.StringIO()
        write_points(original, buf)
        buf.seek(0)
        reloaded = read_points(buf)
        assert reloaded.point_count == original.point_count
        for p_orig in original:
            p_new = reloaded.get_point(p_orig.number)
            assert p_new is not None
            assert math.isclose(p_orig.northing, p_new.northing, abs_tol=0.001)
            assert math.isclose(p_orig.easting, p_new.easting, abs_tol=0.001)
            assert p_orig.description == p_new.description
