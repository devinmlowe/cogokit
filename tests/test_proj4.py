# tests/test_proj4.py
"""Tests for the PROJ4 string parser."""

import math

import pytest

from cogokit.geodetic.ellipsoid import GRS80, WGS84


class TestParseTM:
    """Parse Transverse Mercator PROJ4 strings."""

    def test_new_york_east(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=tmerc +lat_0=38.8333333333333 +lon_0=-74.5 +k=0.9999 "
            "+x_0=150000 +y_0=0 +ellps=GRS80"
        )
        p = parse_proj4(s)
        assert p.proj_type == "tmerc"
        assert math.isclose(p.lat_0, math.radians(38.8333333333333), rel_tol=1e-12)
        assert math.isclose(p.lon_0, math.radians(-74.5), rel_tol=1e-12)
        assert math.isclose(p.k_0, 0.9999, rel_tol=1e-12)
        assert math.isclose(p.x_0, 150000.0)
        assert math.isclose(p.y_0, 0.0)
        assert p.ellipsoid is GRS80

    def test_illinois_east(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=tmerc +lat_0=36.6666666666667 +lon_0=-88.3333333333333 "
            "+k=0.999975 +x_0=300000 +y_0=0 +ellps=GRS80"
        )
        p = parse_proj4(s)
        assert p.proj_type == "tmerc"
        assert math.isclose(p.k_0, 0.999975)


class TestParseLCC:
    """Parse Lambert Conformal Conic PROJ4 strings."""

    def test_california_zone5(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=lcc +lat_0=33.5 +lon_0=-118 +lat_1=35.4666666666667 "
            "+lat_2=34.0333333333333 +x_0=2000000 +y_0=500000 +ellps=GRS80"
        )
        p = parse_proj4(s)
        assert p.proj_type == "lcc"
        assert math.isclose(p.lat_0, math.radians(33.5), rel_tol=1e-12)
        assert math.isclose(p.lon_0, math.radians(-118.0), rel_tol=1e-12)
        assert math.isclose(p.lat_1, math.radians(35.4666666666667), rel_tol=1e-12)
        assert math.isclose(p.lat_2, math.radians(34.0333333333333), rel_tol=1e-12)
        assert math.isclose(p.x_0, 2000000.0)
        assert math.isclose(p.y_0, 500000.0)
        assert p.k_0 == 1.0  # LCC has no explicit k

    def test_texas_central(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=lcc +lat_0=29.6666666666667 +lon_0=-100.333333333333 "
            "+lat_1=31.8833333333333 +lat_2=30.1166666666667 "
            "+x_0=699999.999898399 +y_0=3000000 +ellps=GRS80"
        )
        p = parse_proj4(s)
        assert p.proj_type == "lcc"
        assert p.lat_1 is not None
        assert p.lat_2 is not None


class TestParseOMerc:
    """Parse Oblique Mercator PROJ4 strings."""

    def test_alaska_zone1(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=omerc +lat_0=57 +lonc=-133.666666666667 "
            "+alpha=323.130102361111 +gamma=323.130102361111 "
            "+k=0.9999 +x_0=5000000 +y_0=-5000000 +no_uoff +ellps=GRS80"
        )
        p = parse_proj4(s)
        assert p.proj_type == "omerc"
        assert math.isclose(p.lat_0, math.radians(57.0), rel_tol=1e-12)
        assert math.isclose(p.lonc, math.radians(-133.666666666667), rel_tol=1e-12)
        assert math.isclose(p.alpha, math.radians(323.130102361111), rel_tol=1e-12)
        assert math.isclose(p.gamma, math.radians(323.130102361111), rel_tol=1e-12)
        assert math.isclose(p.k_0, 0.9999)
        assert p.no_uoff is True


class TestParseEdgeCases:
    """Edge cases and error handling."""

    def test_wgs84_ellipsoid(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = "+proj=tmerc +lat_0=0 +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84"
        p = parse_proj4(s)
        assert p.ellipsoid is WGS84

    def test_datum_nad83_implies_grs80(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = "+proj=tmerc +lat_0=0 +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=NAD83"
        p = parse_proj4(s)
        assert p.ellipsoid is GRS80

    def test_unknown_projection_raises(self):
        from cogokit.geodetic.proj4 import parse_proj4

        with pytest.raises(ValueError, match="Unsupported projection"):
            parse_proj4("+proj=merc +lat_0=0 +lon_0=0")

    def test_missing_proj_raises(self):
        from cogokit.geodetic.proj4 import parse_proj4

        with pytest.raises(ValueError, match="proj"):
            parse_proj4("+lat_0=0 +lon_0=0")

    def test_extra_tokens_ignored(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = (
            "+proj=tmerc +lat_0=0 +lon_0=0 +k=1 +x_0=0 +y_0=0 "
            "+ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=us-ft +no_defs +type=crs"
        )
        p = parse_proj4(s)
        assert p.proj_type == "tmerc"

    def test_units_parsed(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = "+proj=tmerc +lat_0=0 +lon_0=0 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=us-ft"
        p = parse_proj4(s)
        assert p.units == "us-ft"

    def test_units_default_meter(self):
        from cogokit.geodetic.proj4 import parse_proj4

        s = "+proj=tmerc +lat_0=0 +lon_0=0 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80"
        p = parse_proj4(s)
        assert p.units == "m"
