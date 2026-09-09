"""Tests for the triangle solver."""

import math

import pytest

from cogokit.solvers.triangle import (
    SolveCase,
    solve_aas,
    solve_asa,
    solve_sas,
    solve_ssa,
    solve_sss,
)


# --- SSS ---------------------------------------------------------------------

class TestSSS:
    def test_3_4_5_right_triangle(self):
        sol = solve_sss(3, 4, 5)
        assert sol.case is SolveCase.SSS
        assert math.isclose(sol.A, math.asin(3 / 5), rel_tol=1e-9)
        assert math.isclose(sol.B, math.asin(4 / 5), rel_tol=1e-9)
        assert math.isclose(sol.C, math.pi / 2, rel_tol=1e-9)
        assert math.isclose(sol.area, 6.0, rel_tol=1e-9)
        assert math.isclose(sol.perimeter, 12.0)

    def test_equilateral(self):
        sol = solve_sss(10, 10, 10)
        assert math.isclose(sol.A, math.pi / 3, rel_tol=1e-9)
        assert math.isclose(sol.area, 10**2 * math.sqrt(3) / 4, rel_tol=1e-9)

    def test_invalid_inequality(self):
        with pytest.raises(ValueError, match="inequality"):
            solve_sss(1, 2, 10)

    def test_negative_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sss(-3, 4, 5)


# --- SAS ---------------------------------------------------------------------

class TestSAS:
    def test_known_triangle(self):
        # sides 5, 7, included angle 60°
        sol = solve_sas(5, math.radians(60), 7)
        assert sol.case is SolveCase.SAS
        # law of cosines: c^2 = 25 + 49 - 2*5*7*cos(60°) = 74 - 35 = 39
        expected_c = math.sqrt(39)
        assert math.isclose(sol.c, expected_c, rel_tol=1e-9)

    def test_right_angle(self):
        sol = solve_sas(3, math.pi / 2, 4)
        assert math.isclose(sol.c, 5.0, rel_tol=1e-9)


# --- ASA ---------------------------------------------------------------------

class TestASA:
    def test_known_triangle(self):
        A = math.radians(45)
        B = math.radians(75)
        c = 10.0
        sol = solve_asa(A, c, B)
        assert sol.case is SolveCase.ASA
        C = math.pi - A - B
        assert math.isclose(sol.C, C, rel_tol=1e-9)
        # law of sines check
        ratio = c / math.sin(C)
        assert math.isclose(sol.a, ratio * math.sin(A), rel_tol=1e-9)
        assert math.isclose(sol.b, ratio * math.sin(B), rel_tol=1e-9)

    def test_invalid_angles(self):
        with pytest.raises(ValueError):
            solve_asa(math.radians(100), 10, math.radians(100))  # sum > 180


# --- AAS ---------------------------------------------------------------------

class TestAAS:
    def test_known_triangle(self):
        A = math.radians(30)
        B = math.radians(60)
        a = 5.0
        sol = solve_aas(A, B, a)
        assert sol.case is SolveCase.AAS
        assert math.isclose(sol.A + sol.B + sol.C, math.pi, rel_tol=1e-9)
        # a/sin(A) = b/sin(B)
        assert math.isclose(sol.b, a * math.sin(B) / math.sin(A), rel_tol=1e-9)


# --- SSA (ambiguous case) ----------------------------------------------------

class TestSSA:
    def test_two_solutions(self):
        # Classic ambiguous case: a=8, b=12, A=30°
        A = math.radians(30)
        solutions = solve_ssa(8, 12, A)
        assert len(solutions) == 2
        for sol in solutions:
            assert sol.case is SolveCase.SSA
            assert math.isclose(sol.A + sol.B + sol.C, math.pi, rel_tol=1e-9)
            assert math.isclose(sol.a, 8, rel_tol=1e-9)
            assert math.isclose(sol.b, 12, rel_tol=1e-9)

    def test_one_solution(self):
        # When a >= b, only one solution
        solutions = solve_ssa(10, 7, math.radians(40))
        assert len(solutions) == 1

    def test_no_solution(self):
        # a too short to reach opposite side
        solutions = solve_ssa(2, 10, math.radians(80))
        assert len(solutions) == 0

    def test_right_angle_single(self):
        # a = b * sin(A) exactly -> right triangle, one solution
        A = math.radians(30)
        b = 10.0
        a = b * math.sin(A)  # exactly 5.0
        solutions = solve_ssa(a, b, A)
        assert len(solutions) == 1
        assert math.isclose(solutions[0].B, math.pi / 2, rel_tol=1e-6)


# --- Cross-checks ------------------------------------------------------------

class TestCrossChecks:
    def test_sss_sas_agree(self):
        """Solve SSS then verify SAS gives the same triangle."""
        sss = solve_sss(7, 8, 9)
        sas = solve_sas(sss.a, sss.C, sss.b)
        assert math.isclose(sss.c, sas.c, rel_tol=1e-9)
        assert math.isclose(sss.area, sas.area, rel_tol=1e-9)

    def test_angle_sum(self):
        sol = solve_sss(5, 12, 13)
        assert math.isclose(sol.A + sol.B + sol.C, math.pi, rel_tol=1e-12)


# --- Edge-case tests --------------------------------------------------------

class TestSSSEdgeCases:
    def test_zero_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sss(0, 4, 5)

    def test_negative_side_b(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sss(3, -4, 5)

    def test_negative_side_c(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sss(3, 4, -5)

    def test_collinear_exact(self):
        """a + b == c exactly: degenerate triangle."""
        with pytest.raises(ValueError, match="inequality"):
            solve_sss(1, 2, 3)

    def test_near_collinear(self):
        """Near-degenerate triangle: tiny area, one angle near pi."""
        sol = solve_sss(1, 1, 1.9999)
        assert sol.area < 0.01  # very small area
        assert sol.C > math.radians(170)  # angle nearly flat


class TestSASEdgeCases:
    def test_zero_side_a(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sas(0, math.radians(60), 7)

    def test_zero_side_b(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sas(5, math.radians(60), 0)

    def test_negative_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_sas(-5, math.radians(60), 7)

    def test_zero_angle(self):
        with pytest.raises(ValueError, match="angle"):
            solve_sas(5, 0, 7)

    def test_pi_angle(self):
        with pytest.raises(ValueError, match="angle"):
            solve_sas(5, math.pi, 7)

    def test_negative_angle(self):
        with pytest.raises(ValueError, match="angle"):
            solve_sas(5, -0.5, 7)


class TestASAEdgeCases:
    def test_angles_sum_greater_than_pi(self):
        with pytest.raises(ValueError):
            solve_asa(math.radians(91), 10, math.radians(91))

    def test_zero_angle_A(self):
        with pytest.raises(ValueError):
            solve_asa(0, 10, math.radians(60))

    def test_zero_angle_B(self):
        with pytest.raises(ValueError):
            solve_asa(math.radians(60), 10, 0)

    def test_negative_angle(self):
        with pytest.raises(ValueError):
            solve_asa(-0.5, 10, math.radians(60))

    def test_zero_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_asa(math.radians(60), 0, math.radians(60))


class TestAASEdgeCases:
    def test_angles_sum_greater_than_pi(self):
        with pytest.raises(ValueError):
            solve_aas(math.radians(100), math.radians(100), 5)

    def test_zero_angle(self):
        with pytest.raises(ValueError):
            solve_aas(0, math.radians(60), 5)

    def test_negative_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_aas(math.radians(30), math.radians(60), -5)

    def test_zero_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_aas(math.radians(30), math.radians(60), 0)


class TestSSAEdgeCases:
    def test_zero_side_a(self):
        with pytest.raises(ValueError, match="positive"):
            solve_ssa(0, 10, math.radians(30))

    def test_negative_side(self):
        with pytest.raises(ValueError, match="positive"):
            solve_ssa(-5, 10, math.radians(30))

    def test_zero_angle(self):
        with pytest.raises(ValueError, match="Angle"):
            solve_ssa(5, 10, 0)

    def test_pi_angle(self):
        with pytest.raises(ValueError, match="Angle"):
            solve_ssa(5, 10, math.pi)
