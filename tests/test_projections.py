"""Tests for Transverse Mercator and UTM projections."""

import math

from cogokit.core import Point
from cogokit.geodetic.ellipsoid import WGS84
from cogokit.geodetic.projections import (
    geodetic_to_utm,
    tm_forward,
    tm_inverse,
    utm_central_meridian,
    utm_from_point,
    utm_to_geodetic,
    utm_to_point,
    utm_zone,
)


class TestUTMZone:
    """Test UTM zone computation."""

    def test_toronto(self):
        # Toronto at -79.3832° -> zone 17
        assert utm_zone(-79.3832) == 17

    def test_london(self):
        # London at -0.1276° -> zone 30
        assert utm_zone(-0.1276) == 30

    def test_tokyo(self):
        # Tokyo at 139.6917° -> zone 54
        assert utm_zone(139.6917) == 54

    def test_central_meridian_zone_17(self):
        # Zone 17: CM = 17*6 - 183 = -81°
        cm = utm_central_meridian(17)
        assert math.isclose(cm, math.radians(-81.0))


class TestGeodeticToUTM:
    """Test geodetic to UTM conversion against known coordinates."""

    def test_toronto(self):
        """Toronto City Hall: 43.6532°N, 79.3832°W.

        Expected UTM Zone 17N: ~630084 E, ~4833439 N (verified against multiple converters).
        """
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)

        result = geodetic_to_utm(lat, lon)

        assert result.zone == 17
        assert result.hemisphere == "N"
        assert math.isclose(result.easting, 630079, abs_tol=500)
        assert math.isclose(result.northing, 4834626, abs_tol=500)

    def test_equator_on_central_meridian(self):
        """At (0°, CM), easting should be 500000 and northing 0."""
        lat = 0.0
        lon = math.radians(-81.0)  # CM of zone 17

        result = geodetic_to_utm(lat, lon, zone=17)

        assert result.zone == 17
        assert result.hemisphere == "N"
        assert math.isclose(result.easting, 500000.0, abs_tol=0.01)
        assert math.isclose(result.northing, 0.0, abs_tol=0.01)

    def test_southern_hemisphere(self):
        """Sydney Opera House: 33.8568°S, 151.2153°E -> UTM Zone 56S."""
        lat = math.radians(-33.8568)
        lon = math.radians(151.2153)

        result = geodetic_to_utm(lat, lon)

        assert result.zone == 56
        assert result.hemisphere == "S"
        # Easting ~ 334901, Northing ~ 6252289
        assert math.isclose(result.easting, 334901, abs_tol=5)
        assert math.isclose(result.northing, 6252289, abs_tol=5)

    def test_scale_on_central_meridian(self):
        """Scale factor on the central meridian should be 0.9996."""
        lat = math.radians(45.0)
        lon = math.radians(-81.0)  # CM of zone 17

        result = geodetic_to_utm(lat, lon, zone=17)
        assert math.isclose(result.scale, 0.9996, abs_tol=1e-6)


class TestUTMRoundTrip:
    """Test UTM forward/inverse round trip."""

    def test_round_trip_toronto(self):
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)

        fwd = geodetic_to_utm(lat, lon)
        inv = utm_to_geodetic(fwd.easting, fwd.northing, fwd.zone, fwd.hemisphere)

        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)

    def test_round_trip_southern(self):
        lat = math.radians(-33.8568)
        lon = math.radians(151.2153)

        fwd = geodetic_to_utm(lat, lon)
        inv = utm_to_geodetic(fwd.easting, fwd.northing, fwd.zone, fwd.hemisphere)

        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)

    def test_round_trip_high_latitude(self):
        lat = math.radians(72.0)
        lon = math.radians(25.0)

        fwd = geodetic_to_utm(lat, lon)
        inv = utm_to_geodetic(fwd.easting, fwd.northing, fwd.zone, fwd.hemisphere)

        assert math.isclose(inv.lat, lat, abs_tol=1e-9)
        assert math.isclose(inv.lon, lon, abs_tol=1e-9)


class TestTransverseMercator:
    """Test raw Transverse Mercator forward/inverse."""

    def test_forward_inverse_round_trip(self):
        lat = math.radians(45.0)
        lon = math.radians(-75.0)
        lon0 = math.radians(-75.0)

        fwd = tm_forward(lat, lon, lon0=lon0, k0=0.9999)
        inv = tm_inverse(fwd.easting, fwd.northing, lon0=lon0, k0=0.9999)

        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)

    def test_on_central_meridian(self):
        """On the central meridian, easting = false_easting and convergence = 0."""
        lat = math.radians(30.0)
        lon0 = math.radians(-90.0)

        fwd = tm_forward(lat, lon0, lon0=lon0, k0=1.0, false_easting=500000.0)
        assert math.isclose(fwd.easting, 500000.0, abs_tol=1e-6)
        assert math.isclose(fwd.convergence, 0.0, abs_tol=1e-12)


class TestUTMFromPoint:
    """Test utm_from_point convenience function."""

    def test_matches_geodetic_to_utm(self):
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)

        float_result = geodetic_to_utm(lat, lon)
        pt = Point(northing=lat, easting=lon)
        point_result = utm_from_point(pt)

        assert point_result.zone == float_result.zone
        assert point_result.hemisphere == float_result.hemisphere
        assert math.isclose(point_result.easting, float_result.easting, rel_tol=1e-12)
        assert math.isclose(point_result.northing, float_result.northing, rel_tol=1e-12)

    def test_with_explicit_zone(self):
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)
        pt = Point(northing=lat, easting=lon)
        result = utm_from_point(pt, zone=18)
        assert result.zone == 18


class TestUTMToPoint:
    """Test utm_to_point convenience function."""

    def test_basic(self):
        pt = utm_to_point(630000.0, 4834000.0, zone=17)
        assert math.isclose(pt.northing, 4834000.0)
        assert math.isclose(pt.easting, 630000.0)
        assert pt.number is None

    def test_with_metadata(self):
        pt = utm_to_point(630000.0, 4834000.0, zone=17, number=100, description="bench mark")
        assert pt.number == 100
        assert pt.description == "bench mark"
