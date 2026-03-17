"""Tests for polygon area and perimeter calculations."""

import math

from cogokit.cogo import Point
from cogokit.cogo.area import polygon_area, polygon_perimeter


def test_area_unit_square():
    points = [
        Point(northing=0, easting=0),
        Point(northing=1, easting=0),
        Point(northing=1, easting=1),
        Point(northing=0, easting=1),
    ]
    assert math.isclose(polygon_area(points), 1.0, abs_tol=1e-10)


def test_area_rectangle():
    points = [
        Point(northing=0, easting=0),
        Point(northing=10, easting=0),
        Point(northing=10, easting=5),
        Point(northing=0, easting=5),
    ]
    assert math.isclose(polygon_area(points), 50.0, abs_tol=1e-10)


def test_area_triangle():
    points = [
        Point(northing=0, easting=0),
        Point(northing=10, easting=0),
        Point(northing=0, easting=10),
    ]
    assert math.isclose(polygon_area(points), 50.0, abs_tol=1e-10)


def test_area_reversed_winding():
    """Area should be positive regardless of point order (CW vs CCW)."""
    points_ccw = [
        Point(northing=0, easting=0),
        Point(northing=10, easting=0),
        Point(northing=10, easting=10),
        Point(northing=0, easting=10),
    ]
    points_cw = list(reversed(points_ccw))
    assert math.isclose(polygon_area(points_ccw), polygon_area(points_cw), abs_tol=1e-10)


def test_area_sample_data():
    """Compute area of polygon from AREA.txt sample data (corners: 10,11,12,13,15)."""
    points = [
        Point(northing=3000.0000, easting=3000.0000),  # 10
        Point(northing=2979.0430, easting=3000.1800),  # 11
        Point(northing=2976.3950, easting=2995.4290),  # 12
        Point(northing=2994.9938, easting=2969.0919),  # 13
        Point(northing=3004.0355, easting=2972.7121),  # 15
    ]
    area = polygon_area(points)
    assert area > 0
    # Verified via independent shoelace calculation
    assert math.isclose(area, 534.042, abs_tol=0.01)


def test_perimeter_unit_square():
    points = [
        Point(northing=0, easting=0),
        Point(northing=1, easting=0),
        Point(northing=1, easting=1),
        Point(northing=0, easting=1),
    ]
    assert math.isclose(polygon_perimeter(points), 4.0, abs_tol=1e-10)


def test_perimeter_rectangle():
    points = [
        Point(northing=0, easting=0),
        Point(northing=10, easting=0),
        Point(northing=10, easting=5),
        Point(northing=0, easting=5),
    ]
    assert math.isclose(polygon_perimeter(points), 30.0, abs_tol=1e-10)


def test_perimeter_equilateral_triangle():
    side = 10.0
    points = [
        Point(northing=0, easting=0),
        Point(northing=side, easting=0),
        Point(northing=side / 2, easting=side * math.sqrt(3) / 2),
    ]
    assert math.isclose(polygon_perimeter(points), 3 * side, abs_tol=1e-10)


def test_area_too_few_points():
    try:
        polygon_area([Point(northing=0, easting=0), Point(northing=1, easting=1)])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_perimeter_too_few_points():
    try:
        polygon_perimeter([Point(northing=0, easting=0), Point(northing=1, easting=1)])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
