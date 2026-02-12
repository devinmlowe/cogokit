"""Tests for Hotine Oblique Mercator projection."""

import math

import pytest

from cogopro.geodetic.ellipsoid import GRS80


class TestOMercForward:
    """Test OMerc forward projection (geodetic -> grid)."""

    def test_on_center_returns_false_origin(self):
        """Point at projection center should map near false origin."""
        from cogopro.geodetic.projections import omerc_forward

        result = omerc_forward(
            lat=math.radians(57.0),
            lon=math.radians(-133.666666666667),
            lat_0=math.radians(57.0),
            lonc=math.radians(-133.666666666667),
            alpha=math.radians(323.130102361111),
            gamma=math.radians(323.130102361111),
            k_0=0.9999,
            false_easting=5000000.0,
            false_northing=-5000000.0,
            no_uoff=True,
            ellipsoid=GRS80,
        )
        assert math.isclose(result.easting, 5000000.0, abs_tol=1.0)
        assert math.isclose(result.northing, -5000000.0, abs_tol=1.0)


class TestOMercRoundTrip:
    """Round-trip forward then inverse should recover original coordinates."""

    @pytest.mark.parametrize(
        "lat_deg,lon_deg",
        [
            (58.3005, -134.4197),   # Juneau
            (57.0531, -135.3346),   # Sitka
            (56.0, -133.0),         # southern panhandle
            (59.0, -135.0),         # northern panhandle
            (57.0, -133.666666666667),  # center
        ],
    )
    def test_round_trip_alaska_zone1(self, lat_deg, lon_deg):
        from cogopro.geodetic.projections import omerc_forward, omerc_inverse

        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)

        kw = dict(
            lat_0=math.radians(57.0),
            lonc=math.radians(-133.666666666667),
            alpha=math.radians(323.130102361111),
            gamma=math.radians(323.130102361111),
            k_0=0.9999,
            false_easting=5000000.0,
            false_northing=-5000000.0,
            no_uoff=True,
            ellipsoid=GRS80,
        )

        fwd = omerc_forward(lat=lat, lon=lon, **kw)
        inv = omerc_inverse(easting=fwd.easting, northing=fwd.northing, **kw)

        assert math.isclose(inv.lat, lat, abs_tol=1e-9)
        assert math.isclose(inv.lon, lon, abs_tol=1e-9)
