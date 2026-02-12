"""Tests for intersection calculations."""

import math

from cogopro.cogo import Point
from cogopro.cogo.intersections import bearing_bearing, bearing_distance, distance_distance


def test_bearing_bearing_perpendicular():
    """Two perpendicular lines should intersect at a known point."""
    # Line 1: from (0, 0) heading east (az = pi/2)
    # Line 2: from (0, 100) heading north (az = 0, but that goes up, won't intersect)
    # Actually: from (0, 100) heading north (az=0) intersects east line at (0, 100)?
    # No. Let me think more carefully.
    # Line 1: origin (0, 0), bearing pi/2 (east) -> travels along easting axis (N=0)
    # Line 2: origin (0, 100), bearing 0 (north) -> travels along northing axis (E=100)
    # Intersection: N = t2 (from line 2), E = t1 (from line 1)
    # Set N=0+t1*cos(pi/2)=0, E=0+t1*sin(pi/2)=t1
    # Set N=0+t2*cos(0)=t2, E=100+t2*sin(0)=100
    # So E=100 from line 2, and E=t1 from line 1 => t1=100
    # N=0 from line 1, N=t2 from line 2 => t2=0
    # Intersection: (0, 100)
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=100.0)
    result = bearing_bearing(p1, math.pi / 2, p2, 0.0)
    assert result is not None
    assert math.isclose(result.northing, 0.0, abs_tol=1e-10)
    assert math.isclose(result.easting, 100.0, abs_tol=1e-10)


def test_bearing_bearing_45_degrees():
    """Intersection of NE and NW bearings."""
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=200.0)
    # Line 1: from (0,0) bearing 45 (NE)
    # Line 2: from (0,200) bearing 315 (NW)
    result = bearing_bearing(p1, math.radians(45), p2, math.radians(315))
    assert result is not None
    assert math.isclose(result.northing, 100.0, abs_tol=1e-6)
    assert math.isclose(result.easting, 100.0, abs_tol=1e-6)


def test_bearing_bearing_parallel():
    """Parallel bearings should return None."""
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=100.0)
    result = bearing_bearing(p1, 0.0, p2, 0.0)
    assert result is None


def test_bearing_distance_basic():
    """Line intersects circle at known points."""
    # Line from origin heading east, circle at (0, 50) radius 10
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=50.0)
    result = bearing_distance(p1, math.pi / 2, p2, 10.0)
    assert result is not None
    pt_near, pt_far = result
    # Intersections at E=40 and E=60 (both at N=0)
    assert math.isclose(pt_near.easting, 40.0, abs_tol=1e-10)
    assert math.isclose(pt_far.easting, 60.0, abs_tol=1e-10)
    assert math.isclose(pt_near.northing, 0.0, abs_tol=1e-10)


def test_bearing_distance_no_intersection():
    """Line that misses the circle should return None."""
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=100.0, easting=100.0)
    result = bearing_distance(p1, math.pi / 2, p2, 5.0)
    assert result is None


def test_bearing_distance_tangent():
    """Line tangent to circle should return two nearly identical points."""
    # Line heading east at N=10, circle at (0,0) radius 10
    p1 = Point(northing=10.0, easting=0.0)
    p2 = Point(northing=0.0, easting=0.0)
    result = bearing_distance(p1, math.pi / 2, p2, 10.0)
    assert result is not None
    pt1, pt2 = result
    assert math.isclose(pt1.northing, pt2.northing, abs_tol=1e-6)
    assert math.isclose(pt1.easting, pt2.easting, abs_tol=1e-6)


def test_distance_distance_basic():
    """Two circles intersecting at known points."""
    # Circle 1: center (0, 0), radius 5
    # Circle 2: center (0, 6), radius 5
    # d=6, a=(25-25+36)/12=3, h=sqrt(25-9)=4
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=6.0)
    result = distance_distance(p1, 5.0, p2, 5.0)
    assert result is not None
    pt1, pt2 = result
    # Both points at E=3, N=+/-4
    assert math.isclose(pt1.easting, 3.0, abs_tol=1e-10)
    assert math.isclose(pt2.easting, 3.0, abs_tol=1e-10)
    assert math.isclose(abs(pt1.northing), 4.0, abs_tol=1e-10)
    assert math.isclose(abs(pt2.northing), 4.0, abs_tol=1e-10)
    assert not math.isclose(pt1.northing, pt2.northing, abs_tol=1e-6)


def test_distance_distance_no_intersection():
    """Circles too far apart should return None."""
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=100.0)
    result = distance_distance(p1, 5.0, p2, 5.0)
    assert result is None


def test_distance_distance_concentric():
    """Concentric circles should return None."""
    p1 = Point(northing=0.0, easting=0.0)
    result = distance_distance(p1, 5.0, p1, 10.0)
    assert result is None


def test_distance_distance_touching():
    """Externally tangent circles should return one point (two coincident)."""
    p1 = Point(northing=0.0, easting=0.0)
    p2 = Point(northing=0.0, easting=10.0)
    result = distance_distance(p1, 5.0, p2, 5.0)
    assert result is not None
    pt1, pt2 = result
    assert math.isclose(pt1.northing, pt2.northing, abs_tol=1e-6)
    assert math.isclose(pt1.easting, pt2.easting, abs_tol=1e-6)
    assert math.isclose(pt1.easting, 5.0, abs_tol=1e-6)
    assert math.isclose(pt1.northing, 0.0, abs_tol=1e-6)
