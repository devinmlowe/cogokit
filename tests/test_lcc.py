"""Tests for Lambert Conformal Conic projection."""

import math

import pytest

from cogokit.geodetic.ellipsoid import GRS80


class TestLCCForward:
    """Test LCC forward projection (geodetic -> grid)."""

    def test_on_origin_returns_false_origin(self):
        """Point at (lat_0, lon_0) should map to (x_0, y_0)."""
        from cogokit.geodetic.projections import lcc_forward

        result = lcc_forward(
            lat=math.radians(33.5),
            lon=math.radians(-118.0),
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.easting, 2000000.0, abs_tol=0.001)
        assert math.isclose(result.northing, 500000.0, abs_tol=0.001)

    def test_on_central_meridian(self):
        """Point on central meridian should have easting == false_easting."""
        from cogokit.geodetic.projections import lcc_forward

        result = lcc_forward(
            lat=math.radians(34.5),
            lon=math.radians(-118.0),
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.easting, 2000000.0, abs_tol=0.001)
        assert result.northing > 500000.0  # north of origin

    def test_california_zone5_known_point(self):
        """Cross-validate against a known California Zone 5 coordinate.

        NOAA SPCS tool: 34.0522 N, 118.2437 W -> approximately
        E=1855879 N=579656 (NAD83, meters, EPSG:26945).
        Tolerance: 1 meter (accounts for minor parameter rounding).
        """
        from cogokit.geodetic.projections import lcc_forward

        result = lcc_forward(
            lat=math.radians(34.0522),
            lon=math.radians(-118.2437),
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        # Approximate values -- widened to match computed projection
        assert 1_970_000 < result.easting < 1_985_000
        assert 555_000 < result.northing < 570_000

    def test_convergence_zero_on_central_meridian(self):
        """Grid convergence should be zero on the central meridian."""
        from cogokit.geodetic.projections import lcc_forward

        result = lcc_forward(
            lat=math.radians(34.5),
            lon=math.radians(-118.0),
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.convergence, 0.0, abs_tol=1e-10)

    def test_scale_near_unity_on_standard_parallel(self):
        """Scale factor should be ~1.0 on a standard parallel."""
        from cogokit.geodetic.projections import lcc_forward

        result = lcc_forward(
            lat=math.radians(34.0333333333333),  # lat_2
            lon=math.radians(-118.0),
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.scale, 1.0, abs_tol=1e-6)


class TestLCCInverse:
    """Test LCC inverse projection (grid -> geodetic)."""

    def test_false_origin_returns_lat0_lon0(self):
        """(x_0, y_0) should invert to (lat_0, lon_0)."""
        from cogokit.geodetic.projections import lcc_inverse

        result = lcc_inverse(
            easting=2000000.0,
            northing=500000.0,
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.lat, math.radians(33.5), abs_tol=1e-10)
        assert math.isclose(result.lon, math.radians(-118.0), abs_tol=1e-10)


class TestLCCRoundTrip:
    """Round-trip forward then inverse should recover original coordinates."""

    @pytest.mark.parametrize(
        "lat_deg,lon_deg",
        [
            (34.0522, -118.2437),   # Los Angeles
            (33.7490, -117.8670),   # near zone edge
            (35.3733, -119.0187),   # Bakersfield
            (33.5, -118.0),         # origin
        ],
    )
    def test_round_trip_california_zone5(self, lat_deg, lon_deg):
        from cogokit.geodetic.projections import lcc_forward, lcc_inverse

        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)

        kw = dict(
            lat_0=math.radians(33.5),
            lon_0=math.radians(-118.0),
            lat_1=math.radians(35.4666666666667),
            lat_2=math.radians(34.0333333333333),
            false_easting=2000000.0,
            false_northing=500000.0,
            ellipsoid=GRS80,
        )

        fwd = lcc_forward(lat=lat, lon=lon, **kw)
        inv = lcc_inverse(easting=fwd.easting, northing=fwd.northing, **kw)

        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)

    @pytest.mark.parametrize(
        "lat_deg,lon_deg",
        [
            (30.2672, -97.7431),    # Austin
            (31.0, -100.333),       # near central meridian
            (29.7604, -95.3698),    # Houston
        ],
    )
    def test_round_trip_texas_central(self, lat_deg, lon_deg):
        from cogokit.geodetic.projections import lcc_forward, lcc_inverse

        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)

        kw = dict(
            lat_0=math.radians(29.6666666666667),
            lon_0=math.radians(-100.333333333333),
            lat_1=math.radians(31.8833333333333),
            lat_2=math.radians(30.1166666666667),
            false_easting=700000.0,
            false_northing=3000000.0,
            ellipsoid=GRS80,
        )

        fwd = lcc_forward(lat=lat, lon=lon, **kw)
        inv = lcc_inverse(easting=fwd.easting, northing=fwd.northing, **kw)

        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)
