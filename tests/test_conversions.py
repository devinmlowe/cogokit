"""Tests for high-level coordinate conversions."""

import math

from cogokit.core import Point
from cogokit.geodetic.conversions import (
    GeodeticCoordinate,
    GridCoordinate,
    combined_scale_factor,
    ecef_to_geodetic,
    geodetic_to_ecef,
    geodetic_to_grid,
    grid_to_geodetic,
    grid_to_ground,
    ground_to_grid,
)

import pytest


class TestGeodeticToGridRoundTrip:
    """Test geodetic <-> grid round trip conversions."""

    def test_round_trip_toronto(self):
        geo = GeodeticCoordinate.from_degrees(43.6532, -79.3832)
        grid = geodetic_to_grid(geo)

        assert grid.zone == 17
        assert grid.hemisphere == "N"

        recovered = grid_to_geodetic(grid)
        assert math.isclose(recovered.lat, geo.lat, abs_tol=1e-10)
        assert math.isclose(recovered.lon, geo.lon, abs_tol=1e-10)

    def test_round_trip_southern_hemisphere(self):
        geo = GeodeticCoordinate.from_degrees(-33.8568, 151.2153)
        grid = geodetic_to_grid(geo)

        assert grid.hemisphere == "S"

        recovered = grid_to_geodetic(grid)
        assert math.isclose(recovered.lat, geo.lat, abs_tol=1e-10)
        assert math.isclose(recovered.lon, geo.lon, abs_tol=1e-10)

    def test_forced_zone(self):
        """Force a specific zone different from auto-detected."""
        geo = GeodeticCoordinate.from_degrees(43.6532, -79.3832)
        grid = geodetic_to_grid(geo, zone=18)
        assert grid.zone == 18

        recovered = grid_to_geodetic(grid)
        assert math.isclose(recovered.lat_deg, 43.6532, abs_tol=1e-6)
        assert math.isclose(recovered.lon_deg, -79.3832, abs_tol=1e-6)


class TestGeodeticCoordinate:
    """Test GeodeticCoordinate helpers."""

    def test_from_degrees(self):
        geo = GeodeticCoordinate.from_degrees(45.0, -75.0)
        assert math.isclose(geo.lat, math.radians(45.0))
        assert math.isclose(geo.lon, math.radians(-75.0))

    def test_lat_lon_deg(self):
        geo = GeodeticCoordinate(math.radians(45.0), math.radians(-75.0))
        assert math.isclose(geo.lat_deg, 45.0, abs_tol=1e-10)
        assert math.isclose(geo.lon_deg, -75.0, abs_tol=1e-10)


class TestGridCoordinateNoZone:
    """Test that grid_to_geodetic raises when zone is missing."""

    def test_missing_zone_raises(self):
        grid = GridCoordinate(easting=500000, northing=0)
        with pytest.raises(ValueError):
            grid_to_geodetic(grid)


class TestCombinedScaleFactor:
    """Test combined scale factor computations."""

    def test_at_sea_level(self):
        csf = combined_scale_factor(0.9996, 0.0)
        assert math.isclose(csf, 0.9996, rel_tol=1e-10)

    def test_at_elevation(self):
        # At 1000m elevation, the elevation factor ≈ R / (R + 1000)
        R = 6_371_000.0
        expected_ef = R / (R + 1000.0)
        csf = combined_scale_factor(1.0, 1000.0)
        assert math.isclose(csf, expected_ef, rel_tol=1e-10)

    def test_elevation_reduces_scale(self):
        csf_low = combined_scale_factor(0.9996, 0.0)
        csf_high = combined_scale_factor(0.9996, 2000.0)
        assert csf_high < csf_low


class TestDistanceConversions:
    """Test ground <-> grid distance conversions."""

    def test_ground_to_grid_identity_at_sea_level(self):
        # With scale=1.0 at sea level, distances should be identical
        grid_dist = ground_to_grid(1000.0, grid_scale=1.0, elevation=0.0)
        assert math.isclose(grid_dist, 1000.0, rel_tol=1e-12)

    def test_grid_to_ground_inverse(self):
        ground_dist = 1000.0
        scale = 0.9996
        elev = 500.0

        gd = ground_to_grid(ground_dist, scale, elev)
        recovered = grid_to_ground(gd, scale, elev)
        assert math.isclose(recovered, ground_dist, rel_tol=1e-12)

    def test_ground_to_grid_with_utm_scale(self):
        # At CM, scale ≈ 0.9996, at sea level
        grid_dist = ground_to_grid(1000.0, 0.9996, 0.0)
        assert math.isclose(grid_dist, 999.6, abs_tol=0.01)


class TestGeodeticToEcef:
    """Test geodetic <-> ECEF conversions."""

    def test_geodetic_to_ecef_origin(self):
        """Equator / prime meridian at sea level: X ≈ a, Y ≈ 0, Z ≈ 0."""
        x, y, z = geodetic_to_ecef(0.0, 0.0, 0.0)
        assert x == pytest.approx(6378137.0, abs=0.001)
        assert y == pytest.approx(0.0, abs=0.001)
        assert z == pytest.approx(0.0, abs=0.001)

    def test_ecef_round_trip(self):
        """Convert to ECEF and back should recover original coordinates."""
        lat = math.radians(43.6532)
        lon = math.radians(-79.3832)
        h = 76.0

        x, y, z = geodetic_to_ecef(lat, lon, h)
        lat2, lon2, h2 = ecef_to_geodetic(x, y, z)

        assert lat2 == pytest.approx(lat, abs=1e-12)
        assert lon2 == pytest.approx(lon, abs=1e-12)
        assert h2 == pytest.approx(h, abs=0.001)

    def test_ecef_known_values(self):
        """North pole at sea level: X ≈ 0, Y ≈ 0, Z ≈ b."""
        from cogokit.geodetic.ellipsoid import WGS84

        x, y, z = geodetic_to_ecef(math.pi / 2, 0.0, 0.0)
        assert x == pytest.approx(0.0, abs=0.001)
        assert y == pytest.approx(0.0, abs=0.001)
        assert z == pytest.approx(WGS84.b, abs=0.001)

    def test_ecef_round_trip_southern_hemisphere(self):
        """Round-trip for a southern-hemisphere point."""
        lat = math.radians(-33.8568)
        lon = math.radians(151.2153)
        h = 50.0

        x, y, z = geodetic_to_ecef(lat, lon, h)
        lat2, lon2, h2 = ecef_to_geodetic(x, y, z)

        assert lat2 == pytest.approx(lat, abs=1e-12)
        assert lon2 == pytest.approx(lon, abs=1e-12)
        assert h2 == pytest.approx(h, abs=0.001)

    def test_ecef_round_trip_high_elevation(self):
        """Round-trip at high elevation (5000 m)."""
        lat = math.radians(27.9881)
        lon = math.radians(86.9250)
        h = 8848.0

        x, y, z = geodetic_to_ecef(lat, lon, h)
        lat2, lon2, h2 = ecef_to_geodetic(x, y, z)

        assert lat2 == pytest.approx(lat, abs=1e-12)
        assert lon2 == pytest.approx(lon, abs=1e-12)
        assert h2 == pytest.approx(h, abs=0.001)


class TestGridCoordinateToPoint:
    """Test GridCoordinate.to_point() interop."""

    def test_to_point_basic(self):
        grid = GridCoordinate(easting=630000.0, northing=4834000.0, zone=17)
        pt = grid.to_point()
        assert math.isclose(pt.northing, 4834000.0)
        assert math.isclose(pt.easting, 630000.0)
        assert pt.number is None
        assert pt.description == ""

    def test_to_point_with_metadata(self):
        grid = GridCoordinate(easting=500000.0, northing=0.0, zone=17)
        pt = grid.to_point(number=1, description="origin")
        assert pt.number == 1
        assert pt.description == "origin"

    def test_from_point(self):
        pt = Point(northing=4834000.0, easting=630000.0)
        grid = GridCoordinate.from_point(pt, zone=17, hemisphere="N")
        assert math.isclose(grid.easting, 630000.0)
        assert math.isclose(grid.northing, 4834000.0)
        assert grid.zone == 17
        assert grid.hemisphere == "N"

    def test_round_trip_point_grid(self):
        pt = Point(northing=4834000.0, easting=630000.0, number=42)
        grid = GridCoordinate.from_point(pt, zone=17)
        recovered = grid.to_point(number=42)
        assert math.isclose(recovered.northing, pt.northing)
        assert math.isclose(recovered.easting, pt.easting)
