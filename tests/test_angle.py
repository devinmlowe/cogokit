"""Tests for Angle class."""

import math

from cogokit.core import Angle, BearingQuadrant


class TestAngleCreation:
    def test_from_degrees(self):
        a = Angle.from_degrees(45.5)
        assert math.isclose(a.degrees, 45.5)

    def test_from_radians(self):
        a = Angle.from_radians(math.pi)
        assert math.isclose(a.degrees, 180.0)

    def test_from_dms(self):
        a = Angle.from_dms(45, 30, 0)
        assert math.isclose(a.degrees, 45.5)

    def test_from_dms_with_seconds(self):
        a = Angle.from_dms(90, 15, 30)
        expected = 90 + 15 / 60 + 30 / 3600
        assert math.isclose(a.degrees, expected)

    def test_from_dms_negative(self):
        a = Angle.from_dms(-10, 30, 0)
        assert math.isclose(a.degrees, -10.5)


class TestFromAzimuth:
    def test_zero(self):
        a = Angle.from_azimuth(0.0)
        assert math.isclose(a.degrees, 0.0)

    def test_pi(self):
        a = Angle.from_azimuth(math.pi)
        assert math.isclose(a.degrees, 180.0)

    def test_negative_radians(self):
        """Negative radians should normalize to [0, 360)."""
        a = Angle.from_azimuth(-math.pi / 2)
        assert math.isclose(a.degrees, 270.0)

    def test_greater_than_2pi(self):
        """Radians > 2*pi should normalize to [0, 360)."""
        a = Angle.from_azimuth(3 * math.pi)
        assert math.isclose(a.degrees, 180.0)

    def test_full_circle(self):
        a = Angle.from_azimuth(2 * math.pi)
        assert math.isclose(a.degrees, 0.0, abs_tol=1e-9)


class TestAngleFloat:
    def test_float_returns_radians(self):
        a = Angle.from_degrees(180.0)
        assert math.isclose(float(a), math.pi)

    def test_float_zero(self):
        a = Angle.from_degrees(0.0)
        assert float(a) == 0.0

    def test_float_90(self):
        a = Angle.from_degrees(90.0)
        assert math.isclose(float(a), math.pi / 2)


class TestHPNotation:
    def test_simple(self):
        a = Angle.from_hp_notation(45.3000)
        assert math.isclose(a.degrees, 45.5)

    def test_with_seconds(self):
        a = Angle.from_hp_notation(90.1530)
        expected = 90 + 15 / 60 + 30 / 3600
        assert math.isclose(a.degrees, expected, abs_tol=1e-6)

    def test_round_trip(self):
        original = 123.4530
        a = Angle.from_hp_notation(original)
        assert math.isclose(a.hp_notation, original, abs_tol=1e-6)

    def test_negative(self):
        a = Angle.from_hp_notation(-45.3000)
        assert math.isclose(a.degrees, -45.5)


class TestDMSConversion:
    def test_to_dms(self):
        a = Angle.from_degrees(45.5)
        d, m, s = a.dms
        assert d == 45
        assert m == 30
        assert math.isclose(s, 0.0, abs_tol=1e-6)

    def test_to_dms_with_seconds(self):
        a = Angle.from_dms(90, 15, 30)
        d, m, s = a.dms
        assert d == 90
        assert m == 15
        assert math.isclose(s, 30.0, abs_tol=1e-6)

    def test_dms_string(self):
        a = Angle.from_dms(45, 30, 15)
        s = a.to_dms_string(precision=0)
        assert "45" in s
        assert "30" in s
        assert "15" in s


class TestBearing:
    def test_from_bearing_ne(self):
        a = Angle.from_bearing(BearingQuadrant.NE, 45.0)
        assert math.isclose(a.degrees, 45.0)

    def test_from_bearing_se(self):
        a = Angle.from_bearing(BearingQuadrant.SE, 45.0)
        assert math.isclose(a.degrees, 135.0)

    def test_from_bearing_sw(self):
        a = Angle.from_bearing(BearingQuadrant.SW, 45.0)
        assert math.isclose(a.degrees, 225.0)

    def test_from_bearing_nw(self):
        a = Angle.from_bearing(BearingQuadrant.NW, 45.0)
        assert math.isclose(a.degrees, 315.0)

    def test_bearing_string_ne(self):
        a = Angle.from_degrees(45.0)
        bs = a.to_bearing_string()
        assert bs.startswith("N")
        assert bs.endswith("E")

    def test_bearing_string_sw(self):
        a = Angle.from_degrees(225.0)
        bs = a.to_bearing_string()
        assert bs.startswith("S")
        assert bs.endswith("W")


class TestAngleArithmetic:
    def test_add(self):
        a = Angle.from_degrees(30.0)
        b = Angle.from_degrees(15.0)
        assert math.isclose((a + b).degrees, 45.0)

    def test_subtract(self):
        a = Angle.from_degrees(90.0)
        b = Angle.from_degrees(45.0)
        assert math.isclose((a - b).degrees, 45.0)

    def test_negate(self):
        a = Angle.from_degrees(45.0)
        assert math.isclose((-a).degrees, -45.0)

    def test_multiply(self):
        a = Angle.from_degrees(30.0)
        assert math.isclose((a * 3).degrees, 90.0)
        assert math.isclose((3 * a).degrees, 90.0)

    def test_divide(self):
        a = Angle.from_degrees(90.0)
        assert math.isclose((a / 2).degrees, 45.0)

    def test_normalize(self):
        a = Angle.from_degrees(400.0)
        n = a.normalize()
        assert math.isclose(n.degrees, 40.0)

    def test_normalize_negative(self):
        a = Angle.from_degrees(-30.0)
        n = a.normalize()
        assert math.isclose(n.degrees, 330.0)


class TestAngleComparison:
    def test_equal(self):
        a = Angle.from_degrees(45.0)
        b = Angle.from_degrees(45.0)
        assert a == b

    def test_less_than(self):
        a = Angle.from_degrees(30.0)
        b = Angle.from_degrees(45.0)
        assert a < b
        assert a <= b

    def test_not_equal(self):
        a = Angle.from_degrees(30.0)
        b = Angle.from_degrees(45.0)
        assert a != b
