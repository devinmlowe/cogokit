"""Tests for unified projection dispatch."""

import math

import pytest

from cogopro.geodetic.ellipsoid import GRS80


class TestProjectionForward:
    """Test dispatch to correct forward projection."""

    def test_tmerc_dispatch(self):
        from cogopro.geodetic.proj4 import parse_proj4
        from cogopro.geodetic.projections import projection_forward

        pdef = parse_proj4(
            "+proj=tmerc +lat_0=38.8333333333333 +lon_0=-74.5 "
            "+k=0.9999 +x_0=150000 +y_0=0 +ellps=GRS80"
        )
        result = projection_forward(math.radians(42.0), math.radians(-74.0), pdef)
        assert result.easting > 0
        assert result.northing > 0

    def test_lcc_dispatch(self):
        from cogopro.geodetic.proj4 import parse_proj4
        from cogopro.geodetic.projections import projection_forward

        pdef = parse_proj4(
            "+proj=lcc +lat_0=33.5 +lon_0=-118 +lat_1=35.4666666666667 "
            "+lat_2=34.0333333333333 +x_0=2000000 +y_0=500000 +ellps=GRS80"
        )
        result = projection_forward(math.radians(34.0), math.radians(-118.0), pdef)
        assert math.isclose(result.easting, 2000000.0, abs_tol=1.0)

    def test_omerc_dispatch(self):
        from cogopro.geodetic.proj4 import parse_proj4
        from cogopro.geodetic.projections import projection_forward

        pdef = parse_proj4(
            "+proj=omerc +lat_0=57 +lonc=-133.666666666667 "
            "+alpha=323.130102361111 +gamma=323.130102361111 "
            "+k=0.9999 +x_0=5000000 +y_0=-5000000 +no_uoff +ellps=GRS80"
        )
        result = projection_forward(math.radians(57.0), math.radians(-133.666666666667), pdef)
        assert math.isclose(result.easting, 5000000.0, abs_tol=1.0)


class TestProjectionInverse:
    """Test dispatch to correct inverse projection."""

    def test_round_trip_tmerc(self):
        from cogopro.geodetic.proj4 import parse_proj4
        from cogopro.geodetic.projections import projection_forward, projection_inverse

        pdef = parse_proj4(
            "+proj=tmerc +lat_0=38.8333333333333 +lon_0=-74.5 "
            "+k=0.9999 +x_0=150000 +y_0=0 +ellps=GRS80"
        )
        lat, lon = math.radians(42.0), math.radians(-74.0)
        fwd = projection_forward(lat, lon, pdef)
        inv = projection_inverse(fwd.easting, fwd.northing, pdef)
        assert math.isclose(inv.lat, lat, abs_tol=1e-10)
        assert math.isclose(inv.lon, lon, abs_tol=1e-10)

    def test_unsupported_proj_type_raises(self):
        from cogopro.geodetic.proj4 import ProjectionDef
        from cogopro.geodetic.projections import projection_forward

        pdef = ProjectionDef(proj_type="merc")
        with pytest.raises(ValueError, match="Unsupported"):
            projection_forward(0.0, 0.0, pdef)
