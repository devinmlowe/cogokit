"""Tests for traverse_plus: field observations, station processing, and resection."""

import math

import pytest

from cogokit.core import Point
from cogokit.cogo.inverse import inverse
from cogokit.surveying.traverse_plus import (
    FieldObservation,
    StationSetup,
    process_station,
    reduce_observation,
    resection_3point,
)


class TestReduceObservation:
    """Tests for reduce_observation function."""

    def test_zero_vertical_angle(self):
        """With 0 vertical angle, full slope distance is horizontal."""
        obs = FieldObservation(
            from_point=1,
            to_point=2,
            hz_angle=0.0,
            vertical_angle=0.0,
            slope_distance=100.0,
        )
        hz, vd, de = reduce_observation(obs)
        assert hz == pytest.approx(100.0)
        assert vd == pytest.approx(0.0, abs=1e-10)
        assert de == pytest.approx(0.0, abs=1e-10)

    def test_45_degree_slope(self):
        """At 45 degrees, horizontal and vertical components are equal."""
        obs = FieldObservation(
            from_point=1,
            to_point=2,
            hz_angle=0.0,
            vertical_angle=math.radians(45),
            slope_distance=100.0,
        )
        hz, vd, de = reduce_observation(obs)
        expected = 100.0 * math.cos(math.radians(45))
        assert hz == pytest.approx(expected)
        assert vd == pytest.approx(expected)
        assert de == pytest.approx(expected, abs=1e-10)

    def test_hi_ht_correction(self):
        """Instrument height and target height affect delta elevation."""
        obs = FieldObservation(
            from_point=1,
            to_point=2,
            hz_angle=0.0,
            vertical_angle=0.0,
            slope_distance=100.0,
            instrument_height=1.5,
            target_height=2.0,
        )
        hz, vd, de = reduce_observation(obs)
        assert hz == pytest.approx(100.0)
        assert vd == pytest.approx(0.0, abs=1e-10)
        # delta_elev = 0.0 + 1.5 - 2.0 = -0.5
        assert de == pytest.approx(-0.5)

    def test_negative_vertical_angle(self):
        """Negative vertical angle produces negative vertical distance."""
        obs = FieldObservation(
            from_point=1,
            to_point=2,
            hz_angle=0.0,
            vertical_angle=math.radians(-30),
            slope_distance=200.0,
        )
        hz, vd, de = reduce_observation(obs)
        assert hz == pytest.approx(200.0 * math.cos(math.radians(-30)))
        assert vd == pytest.approx(200.0 * math.sin(math.radians(-30)))
        assert de == pytest.approx(200.0 * math.sin(math.radians(-30)))

    def test_hi_ht_with_slope(self):
        """Combined HI/HT and vertical angle."""
        obs = FieldObservation(
            from_point=1,
            to_point=2,
            hz_angle=0.0,
            vertical_angle=math.radians(10),
            slope_distance=150.0,
            instrument_height=1.6,
            target_height=1.8,
        )
        hz, vd, de = reduce_observation(obs)
        expected_vd = 150.0 * math.sin(math.radians(10))
        expected_de = expected_vd + 1.6 - 1.8
        assert hz == pytest.approx(150.0 * math.cos(math.radians(10)))
        assert vd == pytest.approx(expected_vd)
        assert de == pytest.approx(expected_de)


class TestProcessStation:
    """Tests for process_station function."""

    def test_known_geometry_due_north(self):
        """Station at origin, backsight due south, observation due north."""
        occupy = Point(northing=0.0, easting=0.0, elevation=100.0)
        backsight = Point(northing=-100.0, easting=0.0, elevation=100.0)

        # hz_angle=0 means same direction as backsight (due south)
        # hz_angle=pi means opposite of backsight (due north)
        obs = FieldObservation(
            from_point=1,
            to_point=3,
            hz_angle=math.pi,  # 180 from backsight = due north
            vertical_angle=0.0,
            slope_distance=50.0,
        )
        setup = StationSetup(
            occupy_point=occupy,
            backsight_point=backsight,
            observations=[obs],
        )
        results = process_station(setup)
        assert len(results) == 1
        pt = results[0]
        assert pt.northing == pytest.approx(50.0)
        assert pt.easting == pytest.approx(0.0, abs=1e-10)
        assert pt.number == 3

    def test_known_geometry_right_angle(self):
        """Station at origin, backsight due north, observation due east (90 deg right)."""
        occupy = Point(northing=0.0, easting=0.0, elevation=0.0)
        backsight = Point(northing=100.0, easting=0.0, elevation=0.0)

        obs = FieldObservation(
            from_point=1,
            to_point=4,
            hz_angle=math.pi / 2,  # 90 degrees right of backsight
            vertical_angle=0.0,
            slope_distance=75.0,
        )
        setup = StationSetup(
            occupy_point=occupy,
            backsight_point=backsight,
            observations=[obs],
        )
        results = process_station(setup)
        assert len(results) == 1
        pt = results[0]
        assert pt.northing == pytest.approx(0.0, abs=1e-10)
        assert pt.easting == pytest.approx(75.0)
        assert pt.number == 4

    def test_multiple_observations(self):
        """Multiple foresights from a single station."""
        occupy = Point(northing=1000.0, easting=1000.0, elevation=50.0)
        backsight = Point(northing=1100.0, easting=1000.0, elevation=50.0)

        obs1 = FieldObservation(
            from_point=1, to_point=2,
            hz_angle=math.pi / 2, vertical_angle=0.0, slope_distance=100.0,
        )
        obs2 = FieldObservation(
            from_point=1, to_point=3,
            hz_angle=math.pi, vertical_angle=0.0, slope_distance=200.0,
        )
        setup = StationSetup(
            occupy_point=occupy,
            backsight_point=backsight,
            observations=[obs1, obs2],
        )
        results = process_station(setup)
        assert len(results) == 2
        # obs1: 90 right of north = due east
        assert results[0].easting == pytest.approx(1100.0)
        assert results[0].northing == pytest.approx(1000.0, abs=1e-10)
        # obs2: 180 from north = due south
        assert results[1].northing == pytest.approx(800.0)
        assert results[1].easting == pytest.approx(1000.0, abs=1e-10)

    def test_elevation_propagation(self):
        """Elevation is propagated through instrument/target heights."""
        occupy = Point(northing=0.0, easting=0.0, elevation=100.0)
        backsight = Point(northing=100.0, easting=0.0, elevation=100.0)

        obs = FieldObservation(
            from_point=1, to_point=5,
            hz_angle=0.0,  # same direction as backsight (due north)
            vertical_angle=math.radians(5),
            slope_distance=100.0,
            instrument_height=1.5,
            target_height=1.8,
        )
        setup = StationSetup(
            occupy_point=occupy,
            backsight_point=backsight,
            observations=[obs],
        )
        results = process_station(setup)
        pt = results[0]
        expected_vd = 100.0 * math.sin(math.radians(5))
        expected_de = expected_vd + 1.5 - 1.8
        assert pt.elevation == pytest.approx(100.0 + expected_de)


def _abs_angle(az1: float, az2: float) -> float:
    """Compute the absolute angle between two azimuths (0 to pi)."""
    d = abs(az2 - az1) % (2 * math.pi)
    if d > math.pi:
        d = 2 * math.pi - d
    return d


class TestResection3Point:
    """Tests for resection_3point using Tienstra's method."""

    def test_equilateral_triangle_center(self):
        """Resection from center of equilateral triangle."""
        # Equilateral triangle with side 1000
        p1 = Point(northing=0.0, easting=0.0)
        p2 = Point(northing=0.0, easting=1000.0)
        p3 = Point(northing=1000.0 * math.sin(math.radians(60)), easting=500.0)

        # The centroid of the equilateral triangle
        centroid_n = (p1.northing + p2.northing + p3.northing) / 3.0
        centroid_e = (p1.easting + p2.easting + p3.easting) / 3.0
        centroid = Point(northing=centroid_n, easting=centroid_e)

        # Compute subtended angles from the centroid (absolute angles)
        inv_c1 = inverse(centroid, p1)
        inv_c2 = inverse(centroid, p2)
        inv_c3 = inverse(centroid, p3)

        angle_1_2 = _abs_angle(inv_c1.azimuth, inv_c2.azimuth)
        angle_2_3 = _abs_angle(inv_c2.azimuth, inv_c3.azimuth)

        result = resection_3point(p1, p2, p3, angle_1_2, angle_2_3)
        assert result.northing == pytest.approx(centroid_n, abs=0.001)
        assert result.easting == pytest.approx(centroid_e, abs=0.001)

    def test_right_triangle(self):
        """Resection with a right triangle configuration."""
        p1 = Point(northing=0.0, easting=0.0)
        p2 = Point(northing=0.0, easting=500.0)
        p3 = Point(northing=500.0, easting=0.0)

        # Known point inside the triangle
        unknown = Point(northing=150.0, easting=150.0)

        inv_u1 = inverse(unknown, p1)
        inv_u2 = inverse(unknown, p2)
        inv_u3 = inverse(unknown, p3)

        angle_1_2 = _abs_angle(inv_u1.azimuth, inv_u2.azimuth)
        angle_2_3 = _abs_angle(inv_u2.azimuth, inv_u3.azimuth)

        result = resection_3point(p1, p2, p3, angle_1_2, angle_2_3)
        assert result.northing == pytest.approx(150.0, abs=0.01)
        assert result.easting == pytest.approx(150.0, abs=0.01)

    def test_asymmetric_position(self):
        """Resection from an asymmetric point."""
        p1 = Point(northing=0.0, easting=0.0)
        p2 = Point(northing=1000.0, easting=0.0)
        p3 = Point(northing=500.0, easting=800.0)

        unknown = Point(northing=400.0, easting=300.0)

        inv_u1 = inverse(unknown, p1)
        inv_u2 = inverse(unknown, p2)
        inv_u3 = inverse(unknown, p3)

        angle_1_2 = _abs_angle(inv_u1.azimuth, inv_u2.azimuth)
        angle_2_3 = _abs_angle(inv_u2.azimuth, inv_u3.azimuth)

        result = resection_3point(p1, p2, p3, angle_1_2, angle_2_3)
        assert result.northing == pytest.approx(400.0, abs=0.01)
        assert result.easting == pytest.approx(300.0, abs=0.01)
