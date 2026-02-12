"""Tests for basic coordinate transformations."""

import math

import pytest

from cogopro.adjustments.transforms import average, mirror, rotate, scale, shift


class TestRotate:
    def test_90_ccw_about_origin(self):
        result = rotate([(1.0, 0.0)], math.pi / 2)
        assert math.isclose(result[0][0], 0.0, abs_tol=1e-10)
        assert math.isclose(result[0][1], 1.0, abs_tol=1e-10)

    def test_180_about_center(self):
        result = rotate([(10.0, 5.0)], math.pi, center=(5.0, 5.0))
        assert math.isclose(result[0][0], 0.0, abs_tol=1e-10)
        assert math.isclose(result[0][1], 5.0, abs_tol=1e-10)

    def test_360_identity(self):
        pts = [(3.0, 7.0), (1.5, -2.3)]
        result = rotate(pts, 2 * math.pi)
        for orig, rot in zip(pts, result):
            assert math.isclose(orig[0], rot[0], abs_tol=1e-10)
            assert math.isclose(orig[1], rot[1], abs_tol=1e-10)

    def test_multiple_points(self):
        pts = [(1.0, 0.0), (0.0, 1.0)]
        result = rotate(pts, math.pi / 2)
        # (1,0) → (0,1);  (0,1) → (-1,0)
        assert math.isclose(result[0][0], 0.0, abs_tol=1e-10)
        assert math.isclose(result[0][1], 1.0, abs_tol=1e-10)
        assert math.isclose(result[1][0], -1.0, abs_tol=1e-10)
        assert math.isclose(result[1][1], 0.0, abs_tol=1e-10)


class TestMirror:
    def test_across_northing_axis(self):
        result = mirror([(5.0, 3.0)], axis="n", value=0.0)
        assert result[0] == (5.0, -3.0)

    def test_across_easting_axis(self):
        result = mirror([(5.0, 3.0)], axis="e", value=0.0)
        assert result[0] == (-5.0, 3.0)

    def test_across_offset_axis(self):
        result = mirror([(5.0, 3.0)], axis="n", value=5.0)
        assert math.isclose(result[0][1], 7.0, abs_tol=1e-10)

    def test_double_mirror_identity(self):
        pts = [(5.0, 3.0)]
        once = mirror(pts, axis="n", value=2.0)
        twice = mirror(once, axis="n", value=2.0)
        assert math.isclose(twice[0][0], pts[0][0], abs_tol=1e-10)
        assert math.isclose(twice[0][1], pts[0][1], abs_tol=1e-10)

    def test_invalid_axis(self):
        with pytest.raises(ValueError):
            mirror([(0, 0)], axis="x")


class TestShift:
    def test_basic_shift(self):
        result = shift([(100.0, 200.0), (300.0, 400.0)], dn=10.0, de=-20.0)
        assert result[0] == (110.0, 180.0)
        assert result[1] == (310.0, 380.0)

    def test_zero_shift(self):
        pts = [(1.0, 2.0)]
        result = shift(pts)
        assert result[0] == (1.0, 2.0)


class TestScale:
    def test_from_origin(self):
        result = scale([(10.0, 20.0)], factor=2.0)
        assert result[0] == (20.0, 40.0)

    def test_from_center(self):
        result = scale([(10.0, 20.0)], factor=2.0, center=(5.0, 10.0))
        assert result[0] == (15.0, 30.0)

    def test_unity_factor(self):
        pts = [(3.0, 7.0)]
        result = scale(pts, factor=1.0, center=(1.0, 2.0))
        assert math.isclose(result[0][0], 3.0, abs_tol=1e-10)
        assert math.isclose(result[0][1], 7.0, abs_tol=1e-10)

    def test_zero_factor_collapses_to_center(self):
        result = scale([(10.0, 20.0), (30.0, 40.0)], factor=0.0, center=(5.0, 5.0))
        for pt in result:
            assert pt == (5.0, 5.0)


class TestAverage:
    def test_three_observations(self):
        obs = [(10.0, 20.0), (10.2, 19.8), (9.8, 20.2)]
        result = average(obs)
        assert math.isclose(result[0], 10.0, abs_tol=1e-10)
        assert math.isclose(result[1], 20.0, abs_tol=1e-10)

    def test_single_observation(self):
        assert average([(5.0, 10.0)]) == (5.0, 10.0)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            average([])
