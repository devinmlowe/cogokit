"""Tests for Point primitive."""

import math

from cogopro.core import Angle, Point


class TestPointCreation:
    def test_basic_creation(self):
        p = Point(1000.0, 2000.0, 100.0, 1, "STAKE")
        assert p.number == 1
        assert p.northing == 1000.0
        assert p.easting == 2000.0
        assert p.elevation == 100.0
        assert p.description == "STAKE"

    def test_default_elevation_and_description(self):
        p = Point(1000.0, 2000.0)
        assert p.elevation == 0.0
        assert p.description == ""
        assert p.number is None

    def test_has_elevation(self):
        p1 = Point(0, 0, 0)
        assert not p1.has_elevation
        p2 = Point(0, 0, 100.5)
        assert p2.has_elevation

    def test_number_optional(self):
        p = Point(1000.0, 2000.0)
        assert p.number is None

    def test_number_explicit_none(self):
        p = Point(1000.0, 2000.0, number=None)
        assert p.number is None

    def test_number_set(self):
        p = Point(1000.0, 2000.0, number=5)
        assert p.number == 5


class TestPointFromCoords:
    def test_basic(self):
        p = Point.from_coords(1000.0, 2000.0)
        assert p.northing == 1000.0
        assert p.easting == 2000.0
        assert p.elevation == 0.0
        assert p.number is None
        assert p.description == ""

    def test_with_all_fields(self):
        p = Point.from_coords(1000.0, 2000.0, elevation=50.0, number=10, description="CP")
        assert p.northing == 1000.0
        assert p.easting == 2000.0
        assert p.elevation == 50.0
        assert p.number == 10
        assert p.description == "CP"

    def test_positional_elevation(self):
        p = Point.from_coords(1000.0, 2000.0, 50.0)
        assert p.elevation == 50.0


class TestPointCoordsTuples:
    def test_coords_2d(self):
        p = Point(1000.0, 2000.0)
        assert p.coords_2d == (1000.0, 2000.0)

    def test_coords_3d(self):
        p = Point(1000.0, 2000.0, 50.0)
        assert p.coords_3d == (1000.0, 2000.0, 50.0)

    def test_coords_3d_default_elevation(self):
        p = Point(1000.0, 2000.0)
        assert p.coords_3d == (1000.0, 2000.0, 0.0)


class TestPointEquality:
    def test_equal_points(self):
        p1 = Point(1000.0, 2000.0, 50.0, 1, "A")
        p2 = Point(1000.0, 2000.0, 50.0, 1, "A")
        assert p1 == p2

    def test_different_number(self):
        p1 = Point(1000.0, 2000.0, number=1)
        p2 = Point(1000.0, 2000.0, number=2)
        assert p1 != p2

    def test_different_coords(self):
        p1 = Point(1000.0, 2000.0, number=1)
        p2 = Point(1000.1, 2000.0, number=1)
        assert p1 != p2

    def test_hash_by_number(self):
        p1 = Point(100.0, 200.0, number=1)
        p2 = Point(999.0, 999.0, number=1)
        assert hash(p1) == hash(p2)

    def test_none_number_equal_by_coords(self):
        p1 = Point(1000.0, 2000.0)
        p2 = Point(1000.0, 2000.0)
        assert p1 == p2

    def test_none_number_hash_by_coords(self):
        p1 = Point(1000.0, 2000.0, 50.0)
        p2 = Point(1000.0, 2000.0, 50.0)
        assert hash(p1) == hash(p2)

    def test_none_number_different_coords(self):
        p1 = Point(1000.0, 2000.0)
        p2 = Point(1000.0, 2001.0)
        assert p1 != p2

    def test_mixed_number_none_same_coords(self):
        """A numbered and unnumbered point at the same coords are equal."""
        p1 = Point(1000.0, 2000.0, number=1)
        p2 = Point(1000.0, 2000.0)
        assert p1 == p2

    def test_none_number_in_set(self):
        p1 = Point(1000.0, 2000.0)
        p2 = Point(1000.0, 2000.0)
        s = {p1, p2}
        assert len(s) == 1


class TestPointDistance:
    def test_horizontal_distance(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(3.0, 4.0, number=2)
        assert math.isclose(p1.distance_to(p2), 5.0)

    def test_zero_distance(self):
        p = Point(100.0, 200.0, number=1)
        assert p.distance_to(p) == 0.0

    def test_3d_distance(self):
        p1 = Point(0.0, 0.0, 0.0, number=1)
        p2 = Point(3.0, 4.0, 12.0, number=2)
        assert math.isclose(p1.distance_3d(p2), 13.0)  # 3-4-12-13 right triangle analog


class TestPointAzimuth:
    def test_returns_angle(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(100.0, 0.0, number=2)
        result = p1.azimuth_to(p2)
        assert isinstance(result, Angle)

    def test_north(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(100.0, 0.0, number=2)
        assert math.isclose(p1.azimuth_to(p2).radians, 0.0, abs_tol=1e-9)

    def test_east(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(0.0, 100.0, number=2)
        assert math.isclose(p1.azimuth_to(p2).radians, math.pi / 2)

    def test_south(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(-100.0, 0.0, number=2)
        assert math.isclose(p1.azimuth_to(p2).radians, math.pi)

    def test_west(self):
        p1 = Point(0.0, 0.0, number=1)
        p2 = Point(0.0, -100.0, number=2)
        assert math.isclose(p1.azimuth_to(p2).radians, 3 * math.pi / 2)
