"""Tests for inverse calculation."""

import math

from cogokit.cogo import Point
from cogokit.cogo.inverse import inverse


def test_inverse_due_north():
    p1 = Point(northing=1000.0, easting=1000.0)
    p2 = Point(northing=1100.0, easting=1000.0)
    result = inverse(p1, p2)
    assert math.isclose(result.azimuth, 0.0, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, 100.0, rel_tol=1e-10)


def test_inverse_due_east():
    p1 = Point(northing=1000.0, easting=1000.0)
    p2 = Point(northing=1000.0, easting=1100.0)
    result = inverse(p1, p2)
    assert math.isclose(result.azimuth, math.pi / 2, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, 100.0, rel_tol=1e-10)


def test_inverse_due_south():
    p1 = Point(northing=1000.0, easting=1000.0)
    p2 = Point(northing=900.0, easting=1000.0)
    result = inverse(p1, p2)
    assert math.isclose(result.azimuth, math.pi, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, 100.0, rel_tol=1e-10)


def test_inverse_due_west():
    p1 = Point(northing=1000.0, easting=1000.0)
    p2 = Point(northing=1000.0, easting=900.0)
    result = inverse(p1, p2)
    assert math.isclose(result.azimuth, 3 * math.pi / 2, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, 100.0, rel_tol=1e-10)


def test_inverse_northeast_45():
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=100.0, easting=100.0)
    result = inverse(p1, p2)
    assert math.isclose(result.azimuth, math.pi / 4, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, math.sqrt(20000), rel_tol=1e-10)


def test_inverse_with_elevation():
    p1 = Point(northing=0.0, easting=0.0, elevation=100.0)
    p2 = Point(northing=300.0, easting=400.0, elevation=200.0)
    result = inverse(p1, p2)
    assert math.isclose(result.horizontal_distance, 500.0, rel_tol=1e-10)
    assert math.isclose(result.vertical_distance, 100.0, rel_tol=1e-10)
    assert math.isclose(result.slope_distance, math.sqrt(500**2 + 100**2), rel_tol=1e-10)
    assert math.isclose(result.grade, 20.0, rel_tol=1e-10)


def test_inverse_area_points():
    """Verify inverse between known points from AREA.txt sample data."""
    p10 = Point(northing=3000.0000, easting=3000.0000)
    p11 = Point(northing=2979.0430, easting=3000.1800)

    result = inverse(p10, p11)
    # Mostly south with tiny eastward component
    assert math.isclose(result.horizontal_distance, 20.9578, abs_tol=0.001)
    # Azimuth should be just past 180 degrees (slightly east of due south)
    assert math.radians(179) < result.azimuth < math.radians(181)


def test_inverse_compass_closure():
    """Verify closure of COMPASS1.txt traverse (point 20 to 26)."""
    p20 = Point(northing=3102.894, easting=3125.949)
    p26 = Point(northing=3102.885, easting=3125.942)

    result = inverse(p20, p26)
    # Should be very small closure error
    assert result.horizontal_distance < 0.015


def test_inverse_same_point():
    p = Point(northing=500.0, easting=500.0)
    result = inverse(p, p)
    assert math.isclose(result.horizontal_distance, 0.0)
    assert math.isclose(result.azimuth, 0.0)
    assert math.isclose(result.grade, 0.0)
