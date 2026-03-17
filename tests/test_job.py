"""Tests for the SQLite-backed Job class."""

import math

import pytest

from cogokit.core.job import Job
from cogokit.core.point import Point
from cogokit.core.units import AngularUnit, LinearUnit


class TestJobBasicOperations:
    """Test all public API methods of Job."""

    def test_add_and_get_point(self):
        job = Job()
        p = Point(northing=100.0, easting=200.0, elevation=10.0, number=1, description="BM")
        job.add_point(p)
        result = job.get_point(1)
        assert result is not None
        assert math.isclose(result.northing, 100.0)
        assert math.isclose(result.easting, 200.0)
        assert math.isclose(result.elevation, 10.0)
        assert result.number == 1
        assert result.description == "BM"

    def test_get_point_not_found(self):
        job = Job()
        assert job.get_point(999) is None

    def test_add_point_replaces_existing(self):
        job = Job()
        job.add_point(Point(northing=100.0, easting=200.0, number=1, description="OLD"))
        job.add_point(Point(northing=300.0, easting=400.0, number=1, description="NEW"))
        p = job.get_point(1)
        assert p.description == "NEW"
        assert math.isclose(p.northing, 300.0)
        assert job.point_count == 1

    def test_remove_point(self):
        job = Job()
        job.add_point(Point(northing=100.0, easting=200.0, number=1))
        removed = job.remove_point(1)
        assert removed is not None
        assert removed.number == 1
        assert job.get_point(1) is None
        assert job.point_count == 0

    def test_remove_point_not_found(self):
        job = Job()
        assert job.remove_point(999) is None

    def test_has_point(self):
        job = Job()
        job.add_point(Point(northing=100.0, easting=200.0, number=5))
        assert job.has_point(5) is True
        assert job.has_point(6) is False

    def test_points_sorted(self):
        job = Job()
        job.add_point(Point(northing=0.0, easting=0.0, number=3))
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        job.add_point(Point(northing=0.0, easting=0.0, number=2))
        nums = [p.number for p in job.points()]
        assert nums == [1, 2, 3]

    def test_point_numbers_sorted(self):
        job = Job()
        job.add_point(Point(northing=0.0, easting=0.0, number=10))
        job.add_point(Point(northing=0.0, easting=0.0, number=5))
        job.add_point(Point(northing=0.0, easting=0.0, number=20))
        assert job.point_numbers() == [5, 10, 20]

    def test_point_count(self):
        job = Job()
        assert job.point_count == 0
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        assert job.point_count == 1
        job.add_point(Point(northing=0.0, easting=0.0, number=2))
        assert job.point_count == 2

    def test_iter(self):
        job = Job()
        job.add_point(Point(northing=0.0, easting=0.0, number=2))
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        nums = [p.number for p in job]
        assert nums == [1, 2]

    def test_len(self):
        job = Job()
        assert len(job) == 0
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        assert len(job) == 1

    def test_contains(self):
        job = Job()
        job.add_point(Point(northing=0.0, easting=0.0, number=7))
        assert 7 in job
        assert 8 not in job

    def test_repr(self):
        job = Job(name="Survey1")
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        assert repr(job) == "Job('Survey1', 1 points)"

    def test_defaults(self):
        job = Job()
        assert job.name == "Untitled"
        assert job.description == ""
        assert job.linear_unit == LinearUnit.FOOT
        assert job.angular_unit == AngularUnit.DMS
        assert job.crs is None
        assert job.point_count == 0


class TestJobSQLiteSpecific:
    """Test SQLite-specific features."""

    def test_in_memory_default(self):
        job = Job()
        job.add_point(Point(northing=100.0, easting=200.0, number=1))
        assert job.point_count == 1

    def test_file_backed(self, tmp_path):
        db = str(tmp_path / "test.db")
        job = Job(db_path=db)
        job.add_point(Point(northing=100.0, easting=200.0, number=1))
        assert job.point_count == 1
        job.close()
        assert (tmp_path / "test.db").exists()

    def test_persistence(self, tmp_path):
        db = str(tmp_path / "persist.db")
        job = Job(name="First", db_path=db)
        job.add_point(Point(northing=100.0, easting=200.0, number=1, description="BM"))
        job.add_point(Point(northing=300.0, easting=400.0, number=2, description="IP"))
        job.close()

        job2 = Job(db_path=db)
        assert job2.point_count == 2
        p = job2.get_point(1)
        assert p is not None
        assert math.isclose(p.northing, 100.0)
        assert p.description == "BM"
        job2.close()

    def test_close_and_reopen(self, tmp_path):
        db = str(tmp_path / "reopen.db")
        job = Job(db_path=db)
        job.add_point(Point(northing=50.0, easting=60.0, number=10))
        job.close()

        job2 = Job(db_path=db)
        assert job2.has_point(10)
        assert job2.get_point(10).number == 10
        job2.close()

    def test_context_manager(self, tmp_path):
        db = str(tmp_path / "ctx.db")
        with Job(db_path=db) as job:
            job.add_point(Point(northing=1.0, easting=2.0, number=1))
            assert job.point_count == 1

        # After context exit, data should persist on disk
        job2 = Job(db_path=db)
        assert job2.point_count == 1
        job2.close()

    def test_add_points_batch(self):
        job = Job()
        pts = [
            Point(northing=float(i), easting=float(i * 10), number=i)
            for i in range(1, 101)
        ]
        job.add_points(pts)
        assert job.point_count == 100
        assert job.get_point(50).number == 50


class TestJobMetadata:
    """Test metadata attributes."""

    def test_metadata_not_persisted(self, tmp_path):
        db = str(tmp_path / "meta.db")
        job = Job(name="Custom", description="My survey", db_path=db)
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        job.close()

        job2 = Job(db_path=db)
        # Metadata is in-memory only; reopening gives defaults
        assert job2.name == "Untitled"
        assert job2.description == ""
        # But points persist
        assert job2.point_count == 1
        job2.close()

    def test_metadata_attributes(self):
        job = Job(
            name="Test",
            description="A test job",
            linear_unit=LinearUnit.METER,
            angular_unit=AngularUnit.RADIANS,
        )
        assert job.name == "Test"
        assert job.description == "A test job"
        assert job.linear_unit == LinearUnit.METER
        assert job.angular_unit == AngularUnit.RADIANS

    def test_crs_settable(self):
        from cogokit.core.crs import CRS
        job = Job()
        assert job.crs is None
        job.crs = CRS.geodetic()
        assert job.crs.kind == "geodetic"

    def test_name_settable_after_construction(self):
        job = Job()
        assert job.name == "Untitled"
        job.name = "NewName"
        assert job.name == "NewName"
