"""Tests for the horizontal curve solver."""

import math

import pytest

from cogokit.core import Point
from cogokit.solvers.horizontal_curve import (
    CurveElements,
    solve_curve,
    spiral,
    three_point_curve,
    three_point_curve_from_points,
)


class TestSolveCurve:
    """Verify curve element relationships using known R and delta."""

    R = 500.0
    delta = math.radians(30)  # 30°

    @pytest.fixture()
    def curve(self) -> CurveElements:
        return solve_curve(R=self.R, delta=self.delta)

    def test_tangent(self, curve: CurveElements):
        expected_T = self.R * math.tan(self.delta / 2)
        assert math.isclose(curve.T, expected_T, rel_tol=1e-9)

    def test_arc_length(self, curve: CurveElements):
        expected_L = self.R * self.delta
        assert math.isclose(curve.L, expected_L, rel_tol=1e-9)

    def test_chord(self, curve: CurveElements):
        expected_C = 2 * self.R * math.sin(self.delta / 2)
        assert math.isclose(curve.C, expected_C, rel_tol=1e-9)

    def test_external(self, curve: CurveElements):
        expected_E = self.R * (1 / math.cos(self.delta / 2) - 1)
        assert math.isclose(curve.E, expected_E, rel_tol=1e-9)

    def test_middle_ordinate(self, curve: CurveElements):
        expected_M = self.R * (1 - math.cos(self.delta / 2))
        assert math.isclose(curve.M, expected_M, rel_tol=1e-9)

    def test_degree_of_curve(self, curve: CurveElements):
        expected_D = 5729.57795130823 / self.R
        assert math.isclose(curve.D, expected_D, rel_tol=1e-9)


class TestSolveCurveFromPairs:
    """Verify we can recover the same curve from different input pairs."""

    R = 800.0
    delta = math.radians(45)

    @pytest.fixture()
    def reference(self) -> CurveElements:
        return solve_curve(R=self.R, delta=self.delta)

    def test_from_R_T(self, reference: CurveElements):
        c = solve_curve(R=reference.R, T=reference.T)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-9)

    def test_from_R_L(self, reference: CurveElements):
        c = solve_curve(R=reference.R, L=reference.L)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-9)

    def test_from_R_C(self, reference: CurveElements):
        c = solve_curve(R=reference.R, C=reference.C)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-9)

    def test_from_R_E(self, reference: CurveElements):
        c = solve_curve(R=reference.R, E=reference.E)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-9)

    def test_from_R_M(self, reference: CurveElements):
        c = solve_curve(R=reference.R, M=reference.M)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-9)

    def test_from_delta_T(self, reference: CurveElements):
        c = solve_curve(delta=reference.delta, T=reference.T)
        assert math.isclose(c.R, reference.R, rel_tol=1e-9)

    def test_from_delta_L(self, reference: CurveElements):
        c = solve_curve(delta=reference.delta, L=reference.L)
        assert math.isclose(c.R, reference.R, rel_tol=1e-9)

    def test_from_D_delta(self, reference: CurveElements):
        c = solve_curve(D=reference.D, delta=reference.delta)
        assert math.isclose(c.R, reference.R, rel_tol=1e-9)

    def test_from_T_L(self, reference: CurveElements):
        c = solve_curve(T=reference.T, L=reference.L)
        assert math.isclose(c.R, reference.R, rel_tol=1e-6)
        assert math.isclose(c.delta, reference.delta, rel_tol=1e-6)

    def test_from_T_C(self, reference: CurveElements):
        c = solve_curve(T=reference.T, C=reference.C)
        assert math.isclose(c.R, reference.R, rel_tol=1e-9)

    def test_from_T_E(self, reference: CurveElements):
        c = solve_curve(T=reference.T, E=reference.E)
        assert math.isclose(c.R, reference.R, rel_tol=1e-9)

    def test_wrong_arg_count(self):
        with pytest.raises(ValueError, match="exactly 2"):
            solve_curve(R=500)

    def test_three_args(self):
        with pytest.raises(ValueError, match="exactly 2"):
            solve_curve(R=500, delta=0.5, T=100)


class TestThreePointCurve:
    def test_known_circle(self):
        # Points on a circle of radius 5 centered at (0, 0)
        cx, cy, R = three_point_curve(5, 0, 0, 5, -5, 0)
        assert math.isclose(cx, 0, abs_tol=1e-9)
        assert math.isclose(cy, 0, abs_tol=1e-9)
        assert math.isclose(R, 5, rel_tol=1e-9)

    def test_offset_circle(self):
        # Circle of radius 10 centered at (3, 4)
        import math as m
        pts = [(3 + 10 * m.cos(a), 4 + 10 * m.sin(a))
               for a in (0, m.radians(120), m.radians(240))]
        cx, cy, R = three_point_curve(*pts[0], *pts[1], *pts[2])
        assert math.isclose(cx, 3, abs_tol=1e-9)
        assert math.isclose(cy, 4, abs_tol=1e-9)
        assert math.isclose(R, 10, rel_tol=1e-9)

    def test_collinear_raises(self):
        with pytest.raises(ValueError, match="collinear"):
            three_point_curve(0, 0, 1, 1, 2, 2)


class TestSpiral:
    def test_basic_spiral(self):
        # Ls=200, R=1000
        sp = spiral(200, 1000)
        assert math.isclose(sp.theta_s, 200 / (2 * 1000), rel_tol=1e-9)
        # X should be close to Ls (spiral is nearly tangent for small theta)
        assert sp.X < 200
        assert sp.X > 199  # for small angle, X ≈ Ls
        assert sp.Y > 0

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            spiral(-10, 500)
        with pytest.raises(ValueError):
            spiral(100, 0)


class TestThreePointCurveFromPoints:
    """Test three_point_curve_from_points with core.Point objects."""

    def test_known_circle(self):
        p1 = Point(northing=0.0, easting=5.0)
        p2 = Point(northing=5.0, easting=0.0)
        p3 = Point(northing=0.0, easting=-5.0)
        center, R = three_point_curve_from_points(p1, p2, p3)
        assert math.isclose(center.easting, 0, abs_tol=1e-9)
        assert math.isclose(center.northing, 0, abs_tol=1e-9)
        assert math.isclose(R, 5, rel_tol=1e-9)

    def test_offset_circle(self):
        pts = [
            Point(northing=4 + 10 * math.sin(a), easting=3 + 10 * math.cos(a))
            for a in (0, math.radians(120), math.radians(240))
        ]
        center, R = three_point_curve_from_points(pts[0], pts[1], pts[2])
        assert math.isclose(center.easting, 3, abs_tol=1e-9)
        assert math.isclose(center.northing, 4, abs_tol=1e-9)
        assert math.isclose(R, 10, rel_tol=1e-9)

    def test_collinear_raises(self):
        p1 = Point(northing=0.0, easting=0.0)
        p2 = Point(northing=1.0, easting=1.0)
        p3 = Point(northing=2.0, easting=2.0)
        with pytest.raises(ValueError, match="collinear"):
            three_point_curve_from_points(p1, p2, p3)

    def test_matches_float_version(self):
        """Point version should produce same results as float version."""
        p1 = Point(northing=10.0, easting=20.0)
        p2 = Point(northing=30.0, easting=0.0)
        p3 = Point(northing=10.0, easting=-20.0)

        cx_f, cy_f, R_f = three_point_curve(20, 10, 0, 30, -20, 10)
        center, R = three_point_curve_from_points(p1, p2, p3)

        assert math.isclose(center.easting, cx_f, abs_tol=1e-9)
        assert math.isclose(center.northing, cy_f, abs_tol=1e-9)
        assert math.isclose(R, R_f, rel_tol=1e-9)
