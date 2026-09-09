"""Tests for ellipsoid definitions and derived parameters."""

import math

from cogokit.geodetic.ellipsoid import (
    AIRY_1830,
    AUSTRALIAN_NATIONAL,
    BESSEL_1841,
    CLARKE_1866,
    EVEREST_1830,
    GRS80,
    INTERNATIONAL_1924,
    KRASSOVSKY_1940,
    WGS84,
    Ellipsoid,
)


class TestWGS84Parameters:
    """Verify WGS84 ellipsoid parameters against published values."""

    def test_semi_major_axis(self):
        assert WGS84.a == 6378137.0

    def test_inverse_flattening(self):
        assert WGS84.inv_f == 298.257223563

    def test_flattening(self):
        assert math.isclose(WGS84.f, 1.0 / 298.257223563, rel_tol=1e-15)

    def test_semi_minor_axis(self):
        # WGS84 b ≈ 6356752.3142 m
        assert math.isclose(WGS84.b, 6356752.314245, rel_tol=1e-10)

    def test_first_eccentricity_squared(self):
        # Published e^2 ≈ 0.00669437999014
        assert math.isclose(WGS84.e2, 0.00669437999014, rel_tol=1e-10)

    def test_second_eccentricity_squared(self):
        # e'^2 ≈ 0.00673949674228
        assert math.isclose(WGS84.ep2, 0.00673949674228, rel_tol=1e-10)

    def test_first_eccentricity(self):
        assert math.isclose(WGS84.e, math.sqrt(WGS84.e2))

    def test_second_eccentricity(self):
        assert math.isclose(WGS84.ep, math.sqrt(WGS84.ep2))


class TestRadiiOfCurvature:
    """Test radius of curvature functions at known latitudes."""

    def test_N_at_equator(self):
        # At equator, N = a
        assert math.isclose(WGS84.N(0.0), WGS84.a, rel_tol=1e-12)

    def test_M_at_equator(self):
        # At equator, M = a*(1-e^2)
        expected = WGS84.a * (1.0 - WGS84.e2)
        assert math.isclose(WGS84.M(0.0), expected, rel_tol=1e-12)

    def test_N_at_pole(self):
        # At pole, N = a / sqrt(1 - e^2)
        lat = math.radians(90.0)
        expected = WGS84.a / math.sqrt(1.0 - WGS84.e2)
        assert math.isclose(WGS84.N(lat), expected, rel_tol=1e-12)

    def test_M_at_pole(self):
        # At pole, M = a / (1 - e^2)^(1/2)  -> same as N at pole
        lat = math.radians(90.0)
        # M at pole = a*(1-e^2)/(1-e^2)^(3/2) = a / sqrt(1-e^2) = N at pole
        expected = WGS84.a / math.sqrt(1.0 - WGS84.e2)
        assert math.isclose(WGS84.M(lat), expected, rel_tol=1e-10)

    def test_N_increases_with_latitude(self):
        N_eq = WGS84.N(0.0)
        N_45 = WGS84.N(math.radians(45.0))
        N_90 = WGS84.N(math.radians(90.0))
        assert N_eq < N_45 < N_90

    def test_mean_radius(self):
        lat = math.radians(45.0)
        R = WGS84.R(lat)
        M = WGS84.M(lat)
        N = WGS84.N(lat)
        assert math.isclose(R, math.sqrt(M * N), rel_tol=1e-12)


class TestGRS80:
    """Verify GRS80 is very close to WGS84 but distinct."""

    def test_same_semi_major(self):
        assert GRS80.a == WGS84.a

    def test_different_flattening(self):
        assert GRS80.inv_f != WGS84.inv_f

    def test_close_flattening(self):
        assert math.isclose(GRS80.f, WGS84.f, rel_tol=1e-8)


class TestOtherEllipsoids:
    """Verify other ellipsoid constants are reasonable."""

    def test_clarke_1866(self):
        assert CLARKE_1866.a == 6378206.4
        assert math.isclose(CLARKE_1866.inv_f, 294.9786982)

    def test_international_1924(self):
        assert INTERNATIONAL_1924.a == 6378388.0
        assert INTERNATIONAL_1924.inv_f == 297.0

    def test_all_have_positive_flattening(self):
        for ell in [WGS84, GRS80, CLARKE_1866, INTERNATIONAL_1924,
                     BESSEL_1841, AIRY_1830, AUSTRALIAN_NATIONAL,
                     KRASSOVSKY_1940, EVEREST_1830]:
            assert ell.f > 0
            assert ell.b < ell.a

    def test_sphere(self):
        sphere = Ellipsoid("Sphere", 6371000.0, 0.0)
        assert sphere.f == 0.0
        assert sphere.b == sphere.a
        assert sphere.e2 == 0.0
