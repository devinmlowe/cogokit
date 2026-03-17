"""Tests for Vincenty direct and inverse geodesic solutions."""

import math

import pytest

from cogokit.core import Angle
from cogokit.geodetic.ellipsoid import WGS84
from cogokit.geodetic.vincenty import (
    vincenty_direct,
    vincenty_inverse,
    vincenty_inverse_from_angles,
)


class TestVincentyInverse:
    """Test Vincenty inverse with well-known geodetic test cases."""

    def test_flinders_peak_to_buninyong(self):
        """Classic Vincenty test case: Flinders Peak -> Buninyong, Australia.

        Published values (Vincenty 1975 / Geoscience Australia):
          Flinders Peak: -37°57'03.72030"S, 144°25'29.52440"E
          Buninyong:     -37°39'10.15610"S, 143°55'35.38390"E
          Distance:      54972.271 m
          Fwd azimuth:   306°52'05.37"
          Rev azimuth:   127°10'25.07"
        """
        lat1 = math.radians(-(37 + 57 / 60 + 3.7203 / 3600))
        lon1 = math.radians(144 + 25 / 60 + 29.5244 / 3600)
        lat2 = math.radians(-(37 + 39 / 60 + 10.1561 / 3600))
        lon2 = math.radians(143 + 55 / 60 + 35.3839 / 3600)

        result = vincenty_inverse(lat1, lon1, lat2, lon2, WGS84)

        assert math.isclose(result.distance, 54972.271, abs_tol=0.01)
        expected_fwd = math.radians(306 + 52 / 60 + 5.37 / 3600)
        expected_rev = math.radians(127 + 10 / 60 + 25.07 / 3600)
        assert math.isclose(result.azimuth_forward, expected_fwd, abs_tol=1e-5)
        assert math.isclose(result.azimuth_reverse, expected_rev, abs_tol=1e-5)

    def test_coincident_points(self):
        """Two identical points should return zero distance."""
        lat = math.radians(45.0)
        lon = math.radians(-75.0)
        result = vincenty_inverse(lat, lon, lat, lon)
        assert result.distance == 0.0

    def test_equatorial_points(self):
        """Points on the equator, 1 degree apart."""
        lat1 = 0.0
        lon1 = 0.0
        lat2 = 0.0
        lon2 = math.radians(1.0)

        result = vincenty_inverse(lat1, lon1, lat2, lon2)

        # 1 degree on the equator ≈ 111,319 m
        assert math.isclose(result.distance, 111319.491, abs_tol=1.0)
        # Azimuth should be ~90 degrees (east)
        assert math.isclose(result.azimuth_forward, math.radians(90.0), abs_tol=1e-4)

    def test_meridional_points(self):
        """Points on the same meridian, 1 degree apart."""
        lat1 = 0.0
        lon1 = 0.0
        lat2 = math.radians(1.0)
        lon2 = 0.0

        result = vincenty_inverse(lat1, lon1, lat2, lon2)

        # 1 degree along the meridian at equator ≈ 110,574 m
        assert math.isclose(result.distance, 110574.389, abs_tol=1.0)
        # Azimuth should be ~0 degrees (north)
        assert math.isclose(result.azimuth_forward, 0.0, abs_tol=1e-4)

    def test_symmetry(self):
        """Distance from A->B should equal distance from B->A."""
        lat1 = math.radians(43.6532)
        lon1 = math.radians(-79.3832)
        lat2 = math.radians(40.7128)
        lon2 = math.radians(-74.0060)

        fwd = vincenty_inverse(lat1, lon1, lat2, lon2)
        rev = vincenty_inverse(lat2, lon2, lat1, lon1)

        assert math.isclose(fwd.distance, rev.distance, rel_tol=1e-12)


class TestVincentyDirect:
    """Test Vincenty direct computation."""

    def test_flinders_peak_direct(self):
        """Direct from Flinders Peak with known azimuth & distance should reach Buninyong."""
        lat1 = math.radians(-(37 + 57 / 60 + 3.7203 / 3600))
        lon1 = math.radians(144 + 25 / 60 + 29.5244 / 3600)
        az = math.radians(306 + 52 / 60 + 5.37 / 3600)
        dist = 54972.271

        result = vincenty_direct(lat1, lon1, az, dist, WGS84)

        expected_lat = math.radians(-(37 + 39 / 60 + 10.1561 / 3600))
        expected_lon = math.radians(143 + 55 / 60 + 35.3839 / 3600)

        assert math.isclose(result.lat, expected_lat, abs_tol=1e-7)
        assert math.isclose(result.lon, expected_lon, abs_tol=1e-7)

    def test_zero_distance(self):
        """Zero distance should return the same point."""
        lat1 = math.radians(45.0)
        lon1 = math.radians(-75.0)
        result = vincenty_direct(lat1, lon1, math.radians(90.0), 0.0)
        assert math.isclose(result.lat, lat1, abs_tol=1e-12)
        assert math.isclose(result.lon, lon1, abs_tol=1e-12)

    def test_round_trip(self):
        """Direct + inverse should be consistent: go forward then measure back."""
        lat1 = math.radians(43.6532)
        lon1 = math.radians(-79.3832)
        az = math.radians(45.0)
        dist = 100_000.0

        direct = vincenty_direct(lat1, lon1, az, dist)
        inverse = vincenty_inverse(lat1, lon1, direct.lat, direct.lon)

        assert math.isclose(inverse.distance, dist, rel_tol=1e-10)
        assert math.isclose(inverse.azimuth_forward, az, abs_tol=1e-9)

    def test_north_pole_direction(self):
        """Going due north from 89°N should land near the pole."""
        lat1 = math.radians(89.0)
        lon1 = 0.0
        az = 0.0  # due north
        dist = 111_000.0  # ~1 degree

        result = vincenty_direct(lat1, lon1, az, dist)
        assert result.lat > math.radians(89.9)


class TestVincentyInverseFromAngles:
    """Test Vincenty inverse with Angle objects."""

    def test_matches_float_version(self):
        """Angle-based wrapper should produce identical results to float version."""
        lat1_f = math.radians(43.6532)
        lon1_f = math.radians(-79.3832)
        lat2_f = math.radians(40.7128)
        lon2_f = math.radians(-74.0060)

        float_result = vincenty_inverse(lat1_f, lon1_f, lat2_f, lon2_f)

        lat1 = Angle.from_degrees(43.6532)
        lon1 = Angle.from_degrees(-79.3832)
        lat2 = Angle.from_degrees(40.7128)
        lon2 = Angle.from_degrees(-74.0060)

        angle_result = vincenty_inverse_from_angles(lat1, lon1, lat2, lon2)

        assert math.isclose(angle_result.distance, float_result.distance, rel_tol=1e-12)
        assert math.isclose(angle_result.azimuth_forward, float_result.azimuth_forward, abs_tol=1e-12)
        assert math.isclose(angle_result.azimuth_reverse, float_result.azimuth_reverse, abs_tol=1e-12)

    def test_coincident_angle_points(self):
        lat = Angle.from_degrees(45.0)
        lon = Angle.from_degrees(-75.0)
        result = vincenty_inverse_from_angles(lat, lon, lat, lon)
        assert result.distance == 0.0

    def test_from_dms_angles(self):
        """Test with DMS-constructed Angle objects (Flinders Peak -> Buninyong)."""
        lat1 = Angle.from_dms(-37, 57, 3.7203)
        lon1 = Angle.from_dms(144, 25, 29.5244)
        lat2 = Angle.from_dms(-37, 39, 10.1561)
        lon2 = Angle.from_dms(143, 55, 35.3839)

        result = vincenty_inverse_from_angles(lat1, lon1, lat2, lon2)
        assert math.isclose(result.distance, 54972.271, abs_tol=0.01)


# --- Edge-case hardening (issue #5) -----------------------------------------


class TestVincentyAntipodalBehavior:
    """Antipodal and near-antipodal points: known Vincenty limitation.

    Vincenty's algorithm is undefined for antipodal points. The current
    implementation's sin_sigma guard treats these as coincident (returns 0),
    which is incorrect but a known limitation. These tests document the
    actual behavior. A future implementation (e.g., Karney's method) would
    handle these correctly.
    """

    def test_exactly_antipodal_returns_zero(self):
        """(0,0) and (0,180deg): sin_sigma guard returns 0 (known limitation)."""
        result = vincenty_inverse(0.0, 0.0, 0.0, math.radians(180.0))
        assert result.distance == 0.0  # Known incorrect — should be ~20003.93 km

    def test_nearly_antipodal_mid_latitude_returns_zero(self):
        """(45,0) and (-45,180): falls through to coincident guard."""
        result = vincenty_inverse(
            math.radians(45.0), 0.0,
            math.radians(-45.0), math.radians(180.0),
        )
        assert result.distance == 0.0  # Known incorrect

    def test_nearly_antipodal_high_latitude(self):
        """(89,0) and (-89,180): may converge or hit guard."""
        # At high latitudes with flattening, behavior varies
        result = vincenty_inverse(
            math.radians(89.0), 0.0,
            math.radians(-89.0), math.radians(180.0),
        )
        # Either returns 0 (guard) or raises ValueError (non-convergence)
        # Currently returns 0
        assert result.distance == 0.0


class TestVincentyConvergenceCorrectness:
    """Convergence and correctness edge cases."""

    def test_equatorial_90_degrees(self):
        """Equatorial path 90deg apart: distance ~10018.754 km, azimuth ~90deg."""
        result = vincenty_inverse(0.0, 0.0, 0.0, math.radians(90.0))
        assert math.isclose(result.distance, 10018754.17, abs_tol=5.0)
        assert math.isclose(result.azimuth_forward, math.radians(90.0), abs_tol=1e-6)

    def test_meridional_equator_to_near_pole(self):
        """(0,0) to (89,0): azimuth should be ~0deg."""
        result = vincenty_inverse(0.0, 0.0, math.radians(89.0), 0.0)
        assert math.isclose(result.azimuth_forward, 0.0, abs_tol=1e-4)

    def test_coincident_at_pole(self):
        """North pole to itself should return zero distance."""
        lat = math.radians(90.0)
        result = vincenty_inverse(lat, 0.0, lat, 0.0)
        assert result.distance == 0.0

    def test_very_short_path_one_arcsecond(self):
        """1 arc-second on the equator: distance ~30.9 m."""
        lon2 = math.radians(1.0 / 3600.0)
        result = vincenty_inverse(0.0, 0.0, 0.0, lon2)
        assert math.isclose(result.distance, 30.9, abs_tol=0.5)

    def test_direct_zero_distance_returns_start(self):
        """Direct with zero distance should return the start point."""
        lat1 = math.radians(33.0)
        lon1 = math.radians(-117.0)
        result = vincenty_direct(lat1, lon1, math.radians(45.0), 0.0)
        assert math.isclose(result.lat, lat1, abs_tol=1e-12)
        assert math.isclose(result.lon, lon1, abs_tol=1e-12)

    def test_direct_from_north_pole_moves_south(self):
        """From north pole, any azimuth should move south (lat decreases)."""
        lat1 = math.radians(90.0)
        lon1 = 0.0
        result = vincenty_direct(lat1, lon1, math.radians(45.0), 100_000.0)
        assert result.lat < lat1


class TestVincentyParametrizedEquatorial:
    """Parametrized equatorial symmetry tests."""

    @pytest.mark.parametrize("lon_diff", [30, 60, 90, 120, 150])
    def test_equatorial_symmetry(self, lon_diff):
        """Inverse distance at equator should be symmetric in longitude direction."""
        lon = math.radians(lon_diff)
        fwd = vincenty_inverse(0.0, 0.0, 0.0, lon)
        rev = vincenty_inverse(0.0, lon, 0.0, 0.0)
        assert math.isclose(fwd.distance, rev.distance, rel_tol=1e-12)


class TestVincentyParametrizedMeridional:
    """Parametrized meridional azimuth tests."""

    @pytest.mark.parametrize("lat", [0, 15, 30, 45, 60, 75])
    def test_meridional_azimuth_northward(self, lat):
        """Moving north along a meridian: forward azimuth should be ~0deg."""
        lat1 = math.radians(lat)
        lat2 = math.radians(lat + 1)
        result = vincenty_inverse(lat1, 0.0, lat2, 0.0)
        assert math.isclose(result.azimuth_forward, 0.0, abs_tol=1e-4)
