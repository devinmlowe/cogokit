"""Tests for polygon area and perimeter calculations."""

import math

from cogopro.cogo import Point
from cogopro.cogo.area import polygon_area, polygon_perimeter


def test_area_unit_square():
    points = [Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)]
    assert math.isclose(polygon_area(points), 1.0, abs_tol=1e-10)


def test_area_rectangle():
    points = [Point(0, 0), Point(10, 0), Point(10, 5), Point(0, 5)]
    assert math.isclose(polygon_area(points), 50.0, abs_tol=1e-10)


def test_area_triangle():
    points = [Point(0, 0), Point(10, 0), Point(0, 10)]
    assert math.isclose(polygon_area(points), 50.0, abs_tol=1e-10)


def test_area_reversed_winding():
    """Area should be positive regardless of point order (CW vs CCW)."""
    points_ccw = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
    points_cw = list(reversed(points_ccw))
    assert math.isclose(polygon_area(points_ccw), polygon_area(points_cw), abs_tol=1e-10)


def test_area_sample_data():
    """Compute area of polygon from AREA.txt sample data (corners: 10,11,12,13,15)."""
    points = [
        Point(3000.0000, 3000.0000),  # 10
        Point(2979.0430, 3000.1800),  # 11
        Point(2976.3950, 2995.4290),  # 12
        Point(2994.9938, 2969.0919),  # 13
        Point(3004.0355, 2972.7121),  # 15
    ]
    area = polygon_area(points)
    assert area > 0
    # Verified via independent shoelace calculation
    assert math.isclose(area, 534.042, abs_tol=0.01)


def test_perimeter_unit_square():
    points = [Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)]
    assert math.isclose(polygon_perimeter(points), 4.0, abs_tol=1e-10)


def test_perimeter_rectangle():
    points = [Point(0, 0), Point(10, 0), Point(10, 5), Point(0, 5)]
    assert math.isclose(polygon_perimeter(points), 30.0, abs_tol=1e-10)


def test_perimeter_equilateral_triangle():
    side = 10.0
    points = [
        Point(0, 0),
        Point(side, 0),
        Point(side / 2, side * math.sqrt(3) / 2),
    ]
    assert math.isclose(polygon_perimeter(points), 3 * side, abs_tol=1e-10)


def test_area_too_few_points():
    try:
        polygon_area([Point(0, 0), Point(1, 1)])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_perimeter_too_few_points():
    try:
        polygon_perimeter([Point(0, 0), Point(1, 1)])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
