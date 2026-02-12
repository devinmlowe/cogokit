"""Tests for the Coordinate Reference System (CRS) layer."""

import math

import pytest

from cogopro.core import Job, Point
from cogopro.core.crs import CRS, transform_job, transform_point
from cogopro.geodetic.ellipsoid import GRS80, WGS84
from cogopro.geodetic.projections import geodetic_to_utm, utm_to_geodetic


class TestCRSCreation:
    """Test CRS factory methods and basic properties."""

    def test_geodetic_default(self):
        crs = CRS.geodetic()
        assert crs.kind == "geodetic"
        assert crs.ellipsoid is WGS84
        assert crs.zone is None
        assert crs.hemisphere is None

    def test_geodetic_custom_ellipsoid(self):
        crs = CRS.geodetic(ellipsoid=GRS80)
        assert crs.kind == "geodetic"
        assert crs.ellipsoid is GRS80

    def test_utm_default(self):
        crs = CRS.utm(zone=17)
        assert crs.kind == "utm"
        assert crs.zone == 17
        assert crs.hemisphere == "N"
        assert crs.ellipsoid is WGS84

    def test_utm_southern(self):
        crs = CRS.utm(zone=56, hemisphere="S")
        assert crs.kind == "utm"
        assert crs.zone == 56
        assert crs.hemisphere == "S"

    def test_utm_custom_ellipsoid(self):
        crs = CRS.utm(zone=17, ellipsoid=GRS80)
        assert crs.ellipsoid is GRS80


class TestCRSEquality:
    """Test CRS equality and identity."""

    def test_geodetic_equal(self):
        assert CRS.geodetic() == CRS.geodetic()

    def test_geodetic_different_ellipsoid(self):
        assert CRS.geodetic(ellipsoid=WGS84) != CRS.geodetic(ellipsoid=GRS80)

    def test_utm_equal(self):
        assert CRS.utm(zone=17) == CRS.utm(zone=17)

    def test_utm_different_zone(self):
        assert CRS.utm(zone=17) != CRS.utm(zone=18)

    def test_utm_different_hemisphere(self):
        assert CRS.utm(zone=17, hemisphere="N") != CRS.utm(zone=17, hemisphere="S")

    def test_geodetic_not_equal_utm(self):
        assert CRS.geodetic() != CRS.utm(zone=17)


class TestCRSConstants:
    """Test predefined CRS constants."""

    def test_wgs84_geo(self):
        from cogopro.core.crs import WGS84_GEO

        assert WGS84_GEO.kind == "geodetic"
        assert WGS84_GEO.ellipsoid is WGS84

    def test_nad83_geo(self):
        from cogopro.core.crs import NAD83_GEO

        assert NAD83_GEO.kind == "geodetic"
        assert NAD83_GEO.ellipsoid is GRS80


class TestTransformPoint:
    """Test point transformation between CRS types."""

    def test_same_crs_returns_equivalent(self):
        """Transforming between identical CRS should return equivalent point."""
        crs = CRS.utm(zone=17)
        pt = Point(northing=4834000.0, easting=630000.0, elevation=100.0, number=1)
        result = transform_point(pt, crs, crs)
        assert math.isclose(result.northing, pt.northing, abs_tol=1e-6)
        assert math.isclose(result.easting, pt.easting, abs_tol=1e-6)
        assert math.isclose(result.elevation, pt.elevation)
        assert result.number == pt.number
        assert result.description == pt.description

    def test_geodetic_to_utm(self):
        """Transform a geodetic point (lat/lon radians) to UTM."""
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)
        pt = Point(northing=lat, easting=lon, number=1)

        geo_crs = CRS.geodetic()
        utm_crs = CRS.utm(zone=17)

        result = transform_point(pt, geo_crs, utm_crs)

        # Verify against direct projection call
        expected = geodetic_to_utm(lat, lon, zone=17)
        assert math.isclose(result.easting, expected.easting, abs_tol=0.001)
        assert math.isclose(result.northing, expected.northing, abs_tol=0.001)
        assert result.number == 1

    def test_utm_to_geodetic(self):
        """Transform a UTM point back to geodetic."""
        easting = 630084.0
        northing = 4834626.0
        pt = Point(northing=northing, easting=easting, number=2)

        utm_crs = CRS.utm(zone=17)
        geo_crs = CRS.geodetic()

        result = transform_point(pt, utm_crs, geo_crs)

        # Verify against direct inverse projection call
        expected = utm_to_geodetic(easting, northing, zone=17, hemisphere="N")
        assert math.isclose(result.northing, expected.lat, abs_tol=1e-10)
        assert math.isclose(result.easting, expected.lon, abs_tol=1e-10)

    def test_round_trip_utm_geodetic_utm(self):
        """UTM -> Geodetic -> UTM should preserve coordinates within tolerance."""
        original = Point(northing=4834626.0, easting=630084.0, elevation=76.5, number=10)
        utm_crs = CRS.utm(zone=17)
        geo_crs = CRS.geodetic()

        geo_pt = transform_point(original, utm_crs, geo_crs)
        back = transform_point(geo_pt, geo_crs, utm_crs)

        assert math.isclose(back.northing, original.northing, abs_tol=0.001)
        assert math.isclose(back.easting, original.easting, abs_tol=0.001)
        assert math.isclose(back.elevation, original.elevation)
        assert back.number == original.number

    def test_round_trip_geodetic_utm_geodetic(self):
        """Geodetic -> UTM -> Geodetic should preserve coordinates within tolerance."""
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)
        original = Point(northing=lat, easting=lon, number=5)

        geo_crs = CRS.geodetic()
        utm_crs = CRS.utm(zone=17)

        utm_pt = transform_point(original, geo_crs, utm_crs)
        back = transform_point(utm_pt, utm_crs, geo_crs)

        assert math.isclose(back.northing, original.northing, abs_tol=1e-10)
        assert math.isclose(back.easting, original.easting, abs_tol=1e-10)

    def test_preserves_elevation(self):
        """Elevation should be preserved through transformation."""
        pt = Point(northing=math.radians(45.0), easting=math.radians(-75.0),
                   elevation=150.0, number=1)
        geo_crs = CRS.geodetic()
        utm_crs = CRS.utm(zone=18)

        result = transform_point(pt, geo_crs, utm_crs)
        assert math.isclose(result.elevation, 150.0)

    def test_preserves_metadata(self):
        """Point number and description should be preserved."""
        pt = Point(northing=math.radians(45.0), easting=math.radians(-75.0),
                   number=42, description="benchmark")
        geo_crs = CRS.geodetic()
        utm_crs = CRS.utm(zone=18)

        result = transform_point(pt, geo_crs, utm_crs)
        assert result.number == 42
        assert result.description == "benchmark"

    def test_utm_to_utm_different_zones(self):
        """Transforming between UTM zones should route through geodetic."""
        pt = Point(northing=4834626.0, easting=630084.0, number=1)
        crs_17 = CRS.utm(zone=17)
        crs_18 = CRS.utm(zone=18)

        result = transform_point(pt, crs_17, crs_18)

        # Round-trip back to zone 17 (cross-zone has slightly higher numerical noise)
        back = transform_point(result, crs_18, crs_17)
        assert math.isclose(back.northing, pt.northing, abs_tol=0.01)
        assert math.isclose(back.easting, pt.easting, abs_tol=0.01)

    def test_southern_hemisphere(self):
        """Transform geodetic to UTM in the southern hemisphere."""
        lat = math.radians(-33.8568)  # Sydney
        lon = math.radians(151.2153)
        pt = Point(northing=lat, easting=lon, number=1)

        geo_crs = CRS.geodetic()
        utm_crs = CRS.utm(zone=56, hemisphere="S")

        result = transform_point(pt, geo_crs, utm_crs)

        expected = geodetic_to_utm(lat, lon, zone=56)
        assert math.isclose(result.easting, expected.easting, abs_tol=0.001)
        assert math.isclose(result.northing, expected.northing, abs_tol=0.001)


class TestTransformJob:
    """Test job-level coordinate transformation."""

    def test_transform_job_geodetic_to_utm(self):
        """Transform an entire job from geodetic to UTM."""
        job = Job(name="Test Survey")
        job.crs = CRS.geodetic()

        lat1 = math.radians(43.6532)
        lon1 = math.radians(-79.3832)
        lat2 = math.radians(43.6500)
        lon2 = math.radians(-79.3800)

        job.add_point(Point(northing=lat1, easting=lon1, number=1, description="A"))
        job.add_point(Point(northing=lat2, easting=lon2, number=2, description="B"))

        utm_crs = CRS.utm(zone=17)
        new_job = transform_job(job, utm_crs)

        assert new_job.crs == utm_crs
        assert new_job.name == "Test Survey"
        assert new_job.point_count == 2

        # Verify each point was transformed
        p1 = new_job.get_point(1)
        p2 = new_job.get_point(2)
        assert p1 is not None
        assert p2 is not None

        # Should be in UTM range
        assert 100_000 < p1.easting < 900_000
        assert 0 < p1.northing < 10_000_000
        assert p1.description == "A"
        assert p2.description == "B"

    def test_transform_job_preserves_metadata(self):
        """Job metadata (name, description, units) should be preserved."""
        from cogopro.core.units import AngularUnit, LinearUnit

        job = Job(name="My Survey", description="Test job",
                  linear_unit=LinearUnit.METER, angular_unit=AngularUnit.DMS)
        job.crs = CRS.geodetic()
        job.add_point(Point(northing=math.radians(45.0), easting=math.radians(-75.0), number=1))

        new_job = transform_job(job, CRS.utm(zone=18))

        assert new_job.name == "My Survey"
        assert new_job.description == "Test job"
        assert new_job.linear_unit == LinearUnit.METER
        assert new_job.angular_unit == AngularUnit.DMS

    def test_transform_job_uses_job_crs(self):
        """transform_job should use the job's CRS as source when not specified."""
        job = Job(name="UTM Job")
        job.crs = CRS.utm(zone=17)
        job.add_point(Point(northing=4834626.0, easting=630084.0, number=1))

        geo_job = transform_job(job, CRS.geodetic())

        pt = geo_job.get_point(1)
        assert pt is not None
        # Should be in radians range for lat/lon
        assert -math.pi / 2 <= pt.northing <= math.pi / 2
        assert -math.pi <= pt.easting <= math.pi

    def test_transform_job_no_crs_raises(self):
        """transform_job should raise ValueError if job has no CRS and none provided."""
        job = Job(name="No CRS")
        job.add_point(Point(northing=100.0, easting=200.0, number=1))

        with pytest.raises(ValueError, match="source CRS"):
            transform_job(job, CRS.utm(zone=17))

    def test_transform_job_explicit_source_crs(self):
        """transform_job should accept explicit from_crs that overrides job.crs."""
        job = Job(name="Override")
        job.crs = CRS.utm(zone=17)  # Will be overridden
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)
        job.add_point(Point(northing=lat, easting=lon, number=1))

        # Override with geodetic
        new_job = transform_job(job, CRS.utm(zone=17), from_crs=CRS.geodetic())
        pt = new_job.get_point(1)
        assert pt is not None
        assert 100_000 < pt.easting < 900_000

    def test_transform_empty_job(self):
        """Transforming an empty job should produce an empty job with new CRS."""
        job = Job(name="Empty")
        job.crs = CRS.geodetic()

        new_job = transform_job(job, CRS.utm(zone=17))

        assert new_job.point_count == 0
        assert new_job.crs == CRS.utm(zone=17)


class TestJobCRSField:
    """Test that the Job dataclass has a crs field."""

    def test_default_crs_is_none(self):
        job = Job()
        assert job.crs is None

    def test_crs_can_be_set(self):
        job = Job()
        job.crs = CRS.geodetic()
        assert job.crs == CRS.geodetic()
