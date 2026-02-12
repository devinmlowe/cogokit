"""Tests for Point primitive."""

import math

from cogopro.core import Point


class TestPointCreation:
    def test_basic_creation(self):
        p = Point(1, 1000.0, 2000.0, 100.0, "STAKE")
        assert p.number == 1
        assert p.northing == 1000.0
        assert p.easting == 2000.0
        assert p.elevation == 100.0
        assert p.description == "STAKE"

    def test_default_elevation_and_description(self):
        p = Point(1, 1000.0, 2000.0)
        assert p.elevation == 0.0
        assert p.description == ""

    def test_has_elevation(self):
        p1 = Point(1, 0, 0, 0)
        assert not p1.has_elevation
        p2 = Point(2, 0, 0, 100.5)
        assert p2.has_elevation


class TestPointEquality:
    def test_equal_points(self):
        p1 = Point(1, 1000.0, 2000.0, 50.0, "A")
        p2 = Point(1, 1000.0, 2000.0, 50.0, "A")
        assert p1 == p2

    def test_different_number(self):
        p1 = Point(1, 1000.0, 2000.0)
        p2 = Point(2, 1000.0, 2000.0)
        assert p1 != p2

    def test_different_coords(self):
        p1 = Point(1, 1000.0, 2000.0)
        p2 = Point(1, 1000.1, 2000.0)
        assert p1 != p2

    def test_hash_by_number(self):
        p1 = Point(1, 100.0, 200.0)
        p2 = Point(1, 999.0, 999.0)
        assert hash(p1) == hash(p2)


class TestPointDistance:
    def test_horizontal_distance(self):
        p1 = Point(1, 0.0, 0.0)
        p2 = Point(2, 3.0, 4.0)
        assert math.isclose(p1.distance_to(p2), 5.0)

    def test_zero_distance(self):
        p = Point(1, 100.0, 200.0)
        assert p.distance_to(p) == 0.0

    def test_3d_distance(self):
        p1 = Point(1, 0.0, 0.0, 0.0)
        p2 = Point(2, 3.0, 4.0, 12.0)
        assert math.isclose(p1.distance_3d(p2), 13.0)  # 3-4-12-13 right triangle analog


class TestPointAzimuth:
    def test_north(self):
        p1 = Point(1, 0.0, 0.0)
        p2 = Point(2, 100.0, 0.0)
        assert math.isclose(p1.azimuth_to(p2), 0.0, abs_tol=1e-9)

    def test_east(self):
        p1 = Point(1, 0.0, 0.0)
        p2 = Point(2, 0.0, 100.0)
        assert math.isclose(p1.azimuth_to(p2), math.pi / 2)

    def test_south(self):
        p1 = Point(1, 0.0, 0.0)
        p2 = Point(2, -100.0, 0.0)
        assert math.isclose(p1.azimuth_to(p2), math.pi)

    def test_west(self):
        p1 = Point(1, 0.0, 0.0)
        p2 = Point(2, 0.0, -100.0)
        assert math.isclose(p1.azimuth_to(p2), 3 * math.pi / 2)
