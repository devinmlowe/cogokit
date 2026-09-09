"""Tests for traverse calculation."""

import math

from cogokit.cogo import Point
from cogokit.cogo.traverse import traverse, sideshot
from cogokit.cogo.inverse import inverse


def test_traverse_due_north():
    origin = Point(northing=1000.0, easting=1000.0)
    result = traverse(origin, 0.0, 100.0)
    assert math.isclose(result.northing, 1100.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 1000.0, abs_tol=1e-10)


def test_traverse_due_east():
    origin = Point(northing=1000.0, easting=1000.0)
    result = traverse(origin, math.pi / 2, 100.0)
    assert math.isclose(result.northing, 1000.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 1100.0, abs_tol=1e-10)


def test_traverse_due_south():
    origin = Point(northing=1000.0, easting=1000.0)
    result = traverse(origin, math.pi, 100.0)
    assert math.isclose(result.northing, 900.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 1000.0, abs_tol=1e-10)


def test_traverse_northeast_45():
    origin = Point(northing=0.0, easting=0.0)
    result = traverse(origin, math.radians(45), 100.0)
    expected_component = 100.0 * math.cos(math.radians(45))
    assert math.isclose(result.northing, expected_component, abs_tol=1e-10)
    assert math.isclose(result.easting, expected_component, abs_tol=1e-10)


def test_traverse_roundtrip():
    """Traverse forward then inverse back should recover original parameters."""
    origin = Point(northing=5000.0, easting=3000.0)
    azimuth = math.radians(127.5)
    distance = 253.75

    new_point = traverse(origin, azimuth, distance)
    result = inverse(origin, new_point)

    assert math.isclose(result.azimuth, azimuth, abs_tol=1e-10)
    assert math.isclose(result.horizontal_distance, distance, abs_tol=1e-10)


def test_traverse_with_elevation():
    origin = Point(northing=0.0, easting=0.0, elevation=100.0)
    result = traverse(origin, 0.0, 100.0, elevation=150.0)
    assert math.isclose(result.elevation, 150.0)


def test_sideshot_straight_ahead():
    """Angle right of 180 from backsight means continuing straight (away from backsight)."""
    origin = Point(northing=1000.0, easting=1000.0)
    # Backsight is due south (az from origin to backsight = pi).
    # Angle right of pi (180) = turn clockwise from south 180 = due north.
    result = sideshot(origin, math.pi, math.pi, 100.0)
    assert math.isclose(result.northing, 1100.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 1000.0, abs_tol=1e-10)


def test_sideshot_90_right():
    """90-degree angle right from backsight direction."""
    origin = Point(northing=1000.0, easting=1000.0)
    # Backsight is due north (az = 0). Turn 90 right from north = east (pi/2).
    result = sideshot(origin, 0.0, math.pi / 2, 100.0)
    assert math.isclose(result.northing, 1000.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 1100.0, abs_tol=1e-10)
