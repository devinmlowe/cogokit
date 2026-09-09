"""Tests for basic coordinate transformations."""

import math

import pytest

from cogokit.adjustments.transforms import average, mirror, rotate, scale, shift
from cogokit.core import Point


class TestRotate:
    def test_90_ccw_about_origin(self):
        result = rotate([Point(northing=1.0, easting=0.0)], math.pi / 2)
        assert math.isclose(result[0].northing, 0.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 1.0, abs_tol=1e-10)

    def test_180_about_center(self):
        result = rotate(
            [Point(northing=10.0, easting=5.0)],
            math.pi,
            center=Point(northing=5.0, easting=5.0),
        )
        assert math.isclose(result[0].northing, 0.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 5.0, abs_tol=1e-10)

    def test_360_identity(self):
        pts = [Point(northing=3.0, easting=7.0), Point(northing=1.5, easting=-2.3)]
        result = rotate(pts, 2 * math.pi)
        for orig, rot in zip(pts, result):
            assert math.isclose(orig.northing, rot.northing, abs_tol=1e-10)
            assert math.isclose(orig.easting, rot.easting, abs_tol=1e-10)

    def test_multiple_points(self):
        pts = [Point(northing=1.0, easting=0.0), Point(northing=0.0, easting=1.0)]
        result = rotate(pts, math.pi / 2)
        # (1,0) → (0,1);  (0,1) → (-1,0)
        assert math.isclose(result[0].northing, 0.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 1.0, abs_tol=1e-10)
        assert math.isclose(result[1].northing, -1.0, abs_tol=1e-10)
        assert math.isclose(result[1].easting, 0.0, abs_tol=1e-10)


class TestMirror:
    def test_across_northing_axis(self):
        result = mirror([Point(northing=5.0, easting=3.0)], axis="n", value=0.0)
        assert math.isclose(result[0].northing, 5.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, -3.0, abs_tol=1e-10)

    def test_across_easting_axis(self):
        result = mirror([Point(northing=5.0, easting=3.0)], axis="e", value=0.0)
        assert math.isclose(result[0].northing, -5.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 3.0, abs_tol=1e-10)

    def test_across_offset_axis(self):
        result = mirror([Point(northing=5.0, easting=3.0)], axis="n", value=5.0)
        assert math.isclose(result[0].easting, 7.0, abs_tol=1e-10)

    def test_double_mirror_identity(self):
        pts = [Point(northing=5.0, easting=3.0)]
        once = mirror(pts, axis="n", value=2.0)
        twice = mirror(once, axis="n", value=2.0)
        assert math.isclose(twice[0].northing, pts[0].northing, abs_tol=1e-10)
        assert math.isclose(twice[0].easting, pts[0].easting, abs_tol=1e-10)

    def test_invalid_axis(self):
        with pytest.raises(ValueError):
            mirror([Point(northing=0.0, easting=0.0)], axis="x")


class TestShift:
    def test_basic_shift(self):
        result = shift(
            [Point(northing=100.0, easting=200.0), Point(northing=300.0, easting=400.0)],
            dn=10.0,
            de=-20.0,
        )
        assert math.isclose(result[0].northing, 110.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 180.0, abs_tol=1e-10)
        assert math.isclose(result[1].northing, 310.0, abs_tol=1e-10)
        assert math.isclose(result[1].easting, 380.0, abs_tol=1e-10)

    def test_zero_shift(self):
        pts = [Point(northing=1.0, easting=2.0)]
        result = shift(pts)
        assert math.isclose(result[0].northing, 1.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 2.0, abs_tol=1e-10)


class TestScale:
    def test_from_origin(self):
        result = scale([Point(northing=10.0, easting=20.0)], factor=2.0)
        assert math.isclose(result[0].northing, 20.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 40.0, abs_tol=1e-10)

    def test_from_center(self):
        result = scale(
            [Point(northing=10.0, easting=20.0)],
            factor=2.0,
            center=Point(northing=5.0, easting=10.0),
        )
        assert math.isclose(result[0].northing, 15.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 30.0, abs_tol=1e-10)

    def test_unity_factor(self):
        pts = [Point(northing=3.0, easting=7.0)]
        result = scale(pts, factor=1.0, center=Point(northing=1.0, easting=2.0))
        assert math.isclose(result[0].northing, 3.0, abs_tol=1e-10)
        assert math.isclose(result[0].easting, 7.0, abs_tol=1e-10)

    def test_zero_factor_collapses_to_center(self):
        result = scale(
            [Point(northing=10.0, easting=20.0), Point(northing=30.0, easting=40.0)],
            factor=0.0,
            center=Point(northing=5.0, easting=5.0),
        )
        for pt in result:
            assert math.isclose(pt.northing, 5.0, abs_tol=1e-10)
            assert math.isclose(pt.easting, 5.0, abs_tol=1e-10)


class TestAverage:
    def test_three_observations(self):
        obs = [
            Point(northing=10.0, easting=20.0),
            Point(northing=10.2, easting=19.8),
            Point(northing=9.8, easting=20.2),
        ]
        result = average(obs)
        assert math.isclose(result.northing, 10.0, abs_tol=1e-10)
        assert math.isclose(result.easting, 20.0, abs_tol=1e-10)

    def test_single_observation(self):
        result = average([Point(northing=5.0, easting=10.0)])
        assert math.isclose(result.northing, 5.0, abs_tol=1e-10)
        assert math.isclose(result.easting, 10.0, abs_tol=1e-10)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            average([])
