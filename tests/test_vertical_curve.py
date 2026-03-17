"""Tests for the vertical curve solver."""

import math

import pytest

from cogokit.solvers.vertical_curve import (
    elevation_at,
    solve_vertical_curve,
)


class TestSolveVerticalCurve:
    """Verify vertical curve with known values.

    Example: PVI at station 50+00, elev 500 ft,
    G1 = +3%, G2 = -2%, L = 600 ft.
    """

    pvi_sta = 5000.0
    pvi_elev = 500.0
    G1 = 0.03
    G2 = -0.02
    L = 600.0

    @pytest.fixture()
    def vc(self):
        return solve_vertical_curve(self.pvi_sta, self.pvi_elev,
                                    self.G1, self.G2, self.L)

    def test_bvc(self, vc):
        assert math.isclose(vc.bvc_station, 4700.0)
        # BVC elev = PVI elev - G1 * L/2 = 500 - 0.03*300 = 491.0
        assert math.isclose(vc.bvc_elevation, 491.0, rel_tol=1e-9)

    def test_evc(self, vc):
        assert math.isclose(vc.evc_station, 5300.0)
        # EVC elev = PVI elev + G2 * L/2 = 500 + (-0.02)*300 = 494.0
        assert math.isclose(vc.evc_elevation, 494.0, rel_tol=1e-9)

    def test_pvi(self, vc):
        assert math.isclose(vc.pvi_station, 5000.0)
        assert math.isclose(vc.pvi_elevation, 500.0)

    def test_k_value(self, vc):
        # K = L / |G2% - G1%| = 600 / |(-2) - 3| = 600 / 5 = 120
        assert math.isclose(vc.K, 120.0, rel_tol=1e-9)

    def test_high_low_point(self, vc):
        # High/low at x = -G1*L/(G2-G1) = -0.03*600/(-0.05) = 360 from BVC
        assert vc.high_low_station is not None
        x_hl = 360.0
        assert math.isclose(vc.high_low_station, 4700.0 + x_hl, rel_tol=1e-9)
        expected_elev = elevation_at(vc.bvc_elevation, self.G1, self.G2, self.L, x_hl)
        assert math.isclose(vc.high_low_elevation, expected_elev, rel_tol=1e-9)

    def test_elevation_at_bvc(self, vc):
        # At x=0 (BVC), elevation = BVC elevation
        elev = elevation_at(vc.bvc_elevation, self.G1, self.G2, self.L, 0)
        assert math.isclose(elev, vc.bvc_elevation)

    def test_elevation_at_evc(self, vc):
        # At x=L (EVC)
        elev = elevation_at(vc.bvc_elevation, self.G1, self.G2, self.L, self.L)
        assert math.isclose(elev, vc.evc_elevation, rel_tol=1e-9)

    def test_elevation_at_midpoint(self, vc):
        # At PVI x=L/2
        elev = elevation_at(vc.bvc_elevation, self.G1, self.G2, self.L, self.L / 2)
        # elev = 491 + 0.03*300 + ((-0.05)/(1200))*300^2
        # = 491 + 9 + (-0.00004167)*90000 = 491 + 9 - 3.75 = 496.25
        assert math.isclose(elev, 496.25, rel_tol=1e-9)


class TestVerticalCurveEdgeCases:
    def test_sag_curve(self):
        # G1 negative, G2 positive -> sag curve with a low point
        vc = solve_vertical_curve(1000, 200, -0.04, 0.02, 400)
        assert vc.high_low_station is not None
        # Low point inside curve
        assert vc.bvc_station < vc.high_low_station < vc.evc_station

    def test_no_high_low_inside(self):
        # Both grades positive, descending to ascending won't have a turning point
        # Actually: G1=+2%, G2=+5% -> x_hl = -0.02*L/0.03 < 0 -> outside curve
        vc = solve_vertical_curve(1000, 500, 0.02, 0.05, 300)
        assert vc.high_low_station is None
        assert vc.high_low_elevation is None

    def test_equal_grades_raises(self):
        with pytest.raises(ValueError, match="differ"):
            solve_vertical_curve(1000, 500, 0.03, 0.03, 200)

    def test_zero_length_raises(self):
        with pytest.raises(ValueError, match="positive"):
            solve_vertical_curve(1000, 500, 0.03, -0.02, 0)
