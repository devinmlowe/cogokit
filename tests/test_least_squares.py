"""Tests for least-squares network adjustment."""

from __future__ import annotations

import math

import pytest

from cogokit.core import Point

import numpy as np

# Import everything we need from the module
from cogokit.adjustments.least_squares import (
    AngleObservation,
    AzimuthObservation,
    DirectionObservation,
    DistanceObservation,
    GpsBaselineObservation,
    Network,
)
from cogokit.geodetic.conversions import geodetic_to_ecef


# ---------------------------------------------------------------------------
# Helper to build a simple triangle network with known coordinates
# ---------------------------------------------------------------------------

def _triangle_points() -> dict[int, Point]:
    """Three known points forming a right triangle."""
    return {
        1: Point(northing=0.0, easting=0.0, number=1),
        2: Point(northing=1000.0, easting=0.0, number=2),
        3: Point(northing=1000.0, easting=1000.0, number=3),
    }


def _compute_distance(a: Point, b: Point) -> float:
    return a.distance_to(b)


def _compute_azimuth(a: Point, b: Point) -> float:
    az = math.atan2(b.easting - a.easting, b.northing - a.northing)
    if az < 0:
        az += 2 * math.pi
    return az


def _compute_angle(at: Point, frm: Point, to: Point) -> float:
    """Compute angle at 'at' from 'frm' to 'to' (clockwise)."""
    az1 = _compute_azimuth(at, frm)
    az2 = _compute_azimuth(at, to)
    angle = az2 - az1
    if angle < 0:
        angle += 2 * math.pi
    return angle


# ===========================================================================
# Test observation dataclass construction
# ===========================================================================

class TestObservationTypes:
    def test_distance_observation_defaults(self):
        obs = DistanceObservation(from_point=1, to_point=2, distance=100.0)
        assert obs.from_point == 1
        assert obs.to_point == 2
        assert obs.distance == 100.0
        assert obs.std_dev == 0.005

    def test_angle_observation_defaults(self):
        obs = AngleObservation(at_point=2, from_point=1, to_point=3, angle=1.5708)
        assert obs.at_point == 2
        assert obs.std_dev == pytest.approx(0.00005)

    def test_direction_observation_defaults(self):
        obs = DirectionObservation(at_point=1, to_point=2, direction=0.0)
        assert obs.std_dev == pytest.approx(0.00005)

    def test_azimuth_observation_defaults(self):
        obs = AzimuthObservation(from_point=1, to_point=2, azimuth=0.0)
        assert obs.std_dev == pytest.approx(0.00005)


# ===========================================================================
# Test Network setup
# ===========================================================================

class TestNetworkSetup:
    def test_add_fixed_point(self):
        net = Network()
        pt = Point(northing=0.0, easting=0.0, number=1)
        net.add_fixed_point(pt)
        assert 1 in net.fixed_points

    def test_add_approximate_point(self):
        net = Network()
        pt = Point(northing=100.0, easting=100.0, number=5)
        net.add_approximate_point(pt)
        assert 5 in net.approximate_points

    def test_add_observation(self):
        net = Network()
        obs = DistanceObservation(from_point=1, to_point=2, distance=100.0)
        net.add_observation(obs)
        assert len(net.observations) == 1

    def test_adjust_requires_observations(self):
        net = Network()
        net.add_fixed_point(Point(northing=0.0, easting=0.0, number=1))
        with pytest.raises(ValueError, match="observation"):
            net.adjust()

    def test_adjust_requires_unknowns(self):
        net = Network()
        net.add_fixed_point(Point(northing=0.0, easting=0.0, number=1))
        net.add_fixed_point(Point(northing=100.0, easting=0.0, number=2))
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=100.0))
        with pytest.raises(ValueError, match="unknown"):
            net.adjust()


# ===========================================================================
# Distance-only networks
# ===========================================================================

class TestDistanceOnlyNetwork:
    def test_triangle_exact_distances(self):
        """Triangle with exact distances — should converge to known coords."""
        pts = _triangle_points()

        net = Network()
        # Fix point 1 and 2, adjust point 3
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        # Start with approximate coords slightly off
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        # Add exact distances
        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))

        result = net.adjust()
        assert result.converged
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.001)
        assert adj3.easting == pytest.approx(1000.0, abs=0.001)

    def test_redundant_distances_improve_coords(self):
        """Extra distance observations should still converge."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1010.0, easting=990.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        d12 = _compute_distance(pts[1], pts[2])

        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))
        # Redundant: distance between two fixed points (adds strength)
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=d12))

        result = net.adjust()
        assert result.converged
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.001)
        assert adj3.easting == pytest.approx(1000.0, abs=0.001)


# ===========================================================================
# Azimuth observations
# ===========================================================================

class TestAzimuthNetwork:
    def test_azimuth_only_network(self):
        """Azimuths alone define direction but not distance — combine with distances."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        # Distances + azimuths
        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        az13 = _compute_azimuth(pts[1], pts[3])
        az23 = _compute_azimuth(pts[2], pts[3])

        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))
        net.add_observation(AzimuthObservation(from_point=1, to_point=3, azimuth=az13))
        net.add_observation(AzimuthObservation(from_point=2, to_point=3, azimuth=az23))

        result = net.adjust()
        assert result.converged
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.001)
        assert adj3.easting == pytest.approx(1000.0, abs=0.001)


# ===========================================================================
# Angle + distance networks
# ===========================================================================

class TestAngleDistanceNetwork:
    def test_angle_and_distance_convergence(self):
        """Angles are nonlinear — verify iterative convergence."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        angle_at_1 = _compute_angle(pts[1], pts[2], pts[3])
        angle_at_2 = _compute_angle(pts[2], pts[3], pts[1])

        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))
        net.add_observation(
            AngleObservation(at_point=1, from_point=2, to_point=3, angle=angle_at_1)
        )
        net.add_observation(
            AngleObservation(at_point=2, from_point=3, to_point=1, angle=angle_at_2)
        )

        result = net.adjust()
        assert result.converged
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.001)
        assert adj3.easting == pytest.approx(1000.0, abs=0.001)


# ===========================================================================
# Direction observations (with orientation unknowns)
# ===========================================================================

class TestDirectionNetwork:
    def test_direction_observations(self):
        """Directions require orientation unknowns per instrument station."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        # Directions from station 1 to points 2 and 3
        az12 = _compute_azimuth(pts[1], pts[2])
        az13 = _compute_azimuth(pts[1], pts[3])
        # Simulate observed directions with an arbitrary orientation offset
        orient_1 = 0.1  # arbitrary orientation constant
        net.add_observation(
            DirectionObservation(at_point=1, to_point=2, direction=az12 + orient_1)
        )
        net.add_observation(
            DirectionObservation(at_point=1, to_point=3, direction=az13 + orient_1)
        )

        # Directions from station 2 to points 1 and 3
        az21 = _compute_azimuth(pts[2], pts[1])
        az23 = _compute_azimuth(pts[2], pts[3])
        orient_2 = -0.05
        net.add_observation(
            DirectionObservation(at_point=2, to_point=1, direction=az21 + orient_2)
        )
        net.add_observation(
            DirectionObservation(at_point=2, to_point=3, direction=az23 + orient_2)
        )

        # Add distances for full determination
        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))

        result = net.adjust()
        assert result.converged
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.001)
        assert adj3.easting == pytest.approx(1000.0, abs=0.001)


# ===========================================================================
# Fixed points remain unchanged
# ===========================================================================

class TestFixedPointsUnchanged:
    def test_fixed_points_not_adjusted(self):
        """Fixed points must appear in result unchanged."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))

        result = net.adjust()
        # Fixed points should be in the result with their original coordinates
        assert result.adjusted_points[1].northing == pytest.approx(0.0)
        assert result.adjusted_points[1].easting == pytest.approx(0.0)
        assert result.adjusted_points[2].northing == pytest.approx(1000.0)
        assert result.adjusted_points[2].easting == pytest.approx(0.0)


# ===========================================================================
# Result statistics
# ===========================================================================

class TestResultStatistics:
    def test_residuals_near_zero_for_exact_observations(self):
        """With exact observations, residuals should be near zero."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        d12 = _compute_distance(pts[1], pts[2])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=d12))

        result = net.adjust()
        assert result.converged
        for r in result.residuals:
            assert abs(r) < 0.001

    def test_std_errors_computed(self):
        """Standard errors should be present for adjusted points."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        d12 = _compute_distance(pts[1], pts[2])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=d12))

        result = net.adjust()
        assert 3 in result.std_errors
        std_n, std_e = result.std_errors[3]
        assert std_n >= 0.0
        assert std_e >= 0.0

    def test_iterations_reported(self):
        """Number of iterations should be a positive integer."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23))

        result = net.adjust()
        assert result.iterations >= 1


# ===========================================================================
# Known benchmark: 4-point network
# ===========================================================================

class TestBenchmarkNetwork:
    def test_four_point_benchmark(self):
        """A 4-point network with exact observations should recover known coords."""
        # Square network: 1(0,0), 2(1000,0), 3(1000,1000), 4(0,1000)
        known = {
            1: Point(northing=0.0, easting=0.0, number=1),
            2: Point(northing=1000.0, easting=0.0, number=2),
            3: Point(northing=1000.0, easting=1000.0, number=3),
            4: Point(northing=0.0, easting=1000.0, number=4),
        }

        net = Network()
        net.add_fixed_point(known[1])
        net.add_fixed_point(known[2])
        # Approximate coords for 3 and 4 (slightly off)
        net.add_approximate_point(
            Point(northing=1005.0, easting=1005.0, number=3)
        )
        net.add_approximate_point(
            Point(northing=5.0, easting=995.0, number=4)
        )

        # All six pairwise distances
        for i in range(1, 5):
            for j in range(i + 1, 5):
                d = _compute_distance(known[i], known[j])
                net.add_observation(DistanceObservation(from_point=i, to_point=j, distance=d))

        # Azimuths from fixed to unknown
        for fp in [1, 2]:
            for up in [3, 4]:
                az = _compute_azimuth(known[fp], known[up])
                net.add_observation(AzimuthObservation(from_point=fp, to_point=up, azimuth=az))

        result = net.adjust()
        assert result.converged

        for pn in [3, 4]:
            adj = result.adjusted_points[pn]
            assert adj.northing == pytest.approx(known[pn].northing, abs=0.001)
            assert adj.easting == pytest.approx(known[pn].easting, abs=0.001)


# ===========================================================================
# Noisy observations
# ===========================================================================

class TestNoisyObservations:
    def test_noisy_distances_converge(self):
        """Network with small noise in observations should still converge."""
        pts = _triangle_points()

        net = Network()
        net.add_fixed_point(pts[1])
        net.add_fixed_point(pts[2])
        net.add_approximate_point(
            Point(northing=1005.0, easting=995.0, number=3)
        )

        d13 = _compute_distance(pts[1], pts[3])
        d23 = _compute_distance(pts[2], pts[3])
        d12 = _compute_distance(pts[1], pts[2])

        # Add small noise
        net.add_observation(DistanceObservation(from_point=1, to_point=3, distance=d13 + 0.003))
        net.add_observation(DistanceObservation(from_point=2, to_point=3, distance=d23 - 0.002))
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=d12 + 0.001))

        result = net.adjust()
        assert result.converged
        # Should be close to true coords (within noise level)
        adj3 = result.adjusted_points[3]
        assert adj3.northing == pytest.approx(1000.0, abs=0.01)
        assert adj3.easting == pytest.approx(1000.0, abs=0.01)
        # Reference variance should be reasonable
        assert result.reference_variance > 0


# ===========================================================================
# Multiple unknown points
# ===========================================================================

class TestMultipleUnknowns:
    def test_three_unknowns_with_distances_and_azimuths(self):
        """Network with 3 unknowns — must have enough observations."""
        # Pentagon: 5 points, fix 2, adjust 3
        known = {
            1: Point(northing=0.0, easting=0.0, number=1),
            2: Point(northing=500.0, easting=-200.0, number=2),
            3: Point(northing=800.0, easting=300.0, number=3),
            4: Point(northing=400.0, easting=700.0, number=4),
            5: Point(northing=-100.0, easting=400.0, number=5),
        }

        net = Network()
        net.add_fixed_point(known[1])
        net.add_fixed_point(known[2])
        net.add_approximate_point(Point(northing=810.0, easting=290.0, number=3))
        net.add_approximate_point(Point(northing=410.0, easting=690.0, number=4))
        net.add_approximate_point(Point(northing=-90.0, easting=410.0, number=5))

        # Observations: all pairwise distances
        for i in range(1, 6):
            for j in range(i + 1, 6):
                d = _compute_distance(known[i], known[j])
                net.add_observation(DistanceObservation(from_point=i, to_point=j, distance=d))

        # A few azimuths for strength
        for fp in [1, 2]:
            for up in [3, 4, 5]:
                az = _compute_azimuth(known[fp], known[up])
                net.add_observation(AzimuthObservation(from_point=fp, to_point=up, azimuth=az))

        result = net.adjust()
        assert result.converged

        for pn in [3, 4, 5]:
            adj = result.adjusted_points[pn]
            assert adj.northing == pytest.approx(known[pn].northing, abs=0.001)
            assert adj.easting == pytest.approx(known[pn].easting, abs=0.001)


# ===========================================================================
# GPS Baseline observations
# ===========================================================================

# Helper: three geodetic points forming a triangle
_GPS_POINTS = {
    1: (math.radians(43.6532), math.radians(-79.3832), 76.0),   # Toronto
    2: (math.radians(43.6600), math.radians(-79.3900), 80.0),   # ~800m NW
    3: (math.radians(43.6550), math.radians(-79.3750), 85.0),   # ~700m E
}


def _ecef_points() -> dict[int, tuple[float, float, float]]:
    """Convert the geodetic test points to ECEF."""
    return {pn: geodetic_to_ecef(*llh) for pn, llh in _GPS_POINTS.items()}


def _compute_baseline(
    ecef: dict[int, tuple[float, float, float]],
    from_pn: int,
    to_pn: int,
) -> tuple[float, float, float]:
    """Compute the exact ECEF baseline vector between two points."""
    pi = ecef[from_pn]
    pj = ecef[to_pn]
    return (pj[0] - pi[0], pj[1] - pi[1], pj[2] - pi[2])


class TestGpsBaselineDataclass:
    def test_gps_baseline_dataclass_defaults(self):
        obs = GpsBaselineObservation(from_point=1, to_point=2, dx=10.0, dy=20.0, dz=30.0)
        assert obs.from_point == 1
        assert obs.to_point == 2
        assert obs.dx == 10.0
        assert obs.dy == 20.0
        assert obs.dz == 30.0
        assert obs.covariance is None
        assert obs.std_dev == 0.010

    def test_gps_baseline_custom_covariance(self):
        cov = np.diag([0.001, 0.001, 0.002])
        obs = GpsBaselineObservation(
            from_point=1, to_point=2,
            dx=10.0, dy=20.0, dz=30.0,
            covariance=cov,
        )
        assert obs.covariance is not None
        assert obs.covariance[2, 2] == pytest.approx(0.002)


class TestGpsBaselineTriangle:
    def test_simple_baseline_triangle(self):
        """Three points, fix point 1, adjust points 2 and 3 from baselines."""
        ecef = _ecef_points()

        net = Network()
        # Fix point 1
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        # Approximate points 2 and 3 with slight offsets
        lat2, lon2, h2 = _GPS_POINTS[2]
        net.add_approximate_point_3d(2, lat2 + 1e-6, lon2 + 1e-6, h2 + 0.5)
        lat3, lon3, h3 = _GPS_POINTS[3]
        net.add_approximate_point_3d(3, lat3 - 1e-6, lon3 - 1e-6, h3 - 0.3)

        # Baselines: 1->2, 1->3, 2->3
        for from_pn, to_pn in [(1, 2), (1, 3), (2, 3)]:
            dx, dy, dz = _compute_baseline(ecef, from_pn, to_pn)
            net.add_observation(GpsBaselineObservation(
                from_point=from_pn, to_point=to_pn,
                dx=dx, dy=dy, dz=dz,
            ))

        result = net.adjust()
        assert result.converged
        assert result.adjusted_points_3d is not None

        # Check adjusted ECEF coordinates match known values
        for pn in [2, 3]:
            adj = result.adjusted_points_3d[pn]
            known = ecef[pn]
            assert adj[0] == pytest.approx(known[0], abs=0.001)
            assert adj[1] == pytest.approx(known[1], abs=0.001)
            assert adj[2] == pytest.approx(known[2], abs=0.001)

    def test_baseline_residuals_near_zero(self):
        """With exact baselines, residuals should be near zero."""
        ecef = _ecef_points()

        net = Network()
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        net.add_approximate_point_3d(2, *_GPS_POINTS[2])  # exact approx
        net.add_approximate_point_3d(3, *_GPS_POINTS[3])  # exact approx

        # Only two baselines (minimum for 2 unknowns with 3 components each = 6 obs, 6 unknowns)
        for from_pn, to_pn in [(1, 2), (1, 3), (2, 3)]:
            dx, dy, dz = _compute_baseline(ecef, from_pn, to_pn)
            net.add_observation(GpsBaselineObservation(
                from_point=from_pn, to_point=to_pn,
                dx=dx, dy=dy, dz=dz,
            ))

        result = net.adjust()
        assert result.converged
        for r in result.residuals:
            assert abs(r) < 1e-6

    def test_baseline_convergence(self):
        """GPS baseline adjustment should converge in 1 iteration (linear)."""
        ecef = _ecef_points()

        net = Network()
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        lat2, lon2, h2 = _GPS_POINTS[2]
        net.add_approximate_point_3d(2, lat2 + 2e-6, lon2 - 2e-6, h2 + 1.0)

        dx, dy, dz = _compute_baseline(ecef, 1, 2)
        net.add_observation(GpsBaselineObservation(
            from_point=1, to_point=2, dx=dx, dy=dy, dz=dz,
        ))

        result = net.adjust()
        assert result.converged
        # Linear problem: should converge quickly (1 solve + 1 verification pass)
        assert result.iterations <= 2

    def test_baseline_with_covariance(self):
        """Adjustment should work with a full 3x3 covariance matrix."""
        ecef = _ecef_points()

        net = Network()
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        lat2, lon2, h2 = _GPS_POINTS[2]
        net.add_approximate_point_3d(2, lat2 + 1e-6, lon2 + 1e-6, h2 + 0.5)

        dx, dy, dz = _compute_baseline(ecef, 1, 2)
        cov = np.array([
            [0.0001, 0.00001, 0.00001],
            [0.00001, 0.0001, 0.00001],
            [0.00001, 0.00001, 0.0002],
        ])
        net.add_observation(GpsBaselineObservation(
            from_point=1, to_point=2,
            dx=dx, dy=dy, dz=dz,
            covariance=cov,
        ))

        result = net.adjust()
        assert result.converged
        adj = result.adjusted_points_3d[2]
        known = ecef[2]
        assert adj[0] == pytest.approx(known[0], abs=0.001)
        assert adj[1] == pytest.approx(known[1], abs=0.001)
        assert adj[2] == pytest.approx(known[2], abs=0.001)

    def test_adjusted_points_contain_geodetic(self):
        """The 2D adjusted_points dict should contain geodetic lat/lon as northing/easting."""
        ecef = _ecef_points()

        net = Network()
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        net.add_approximate_point_3d(2, *_GPS_POINTS[2])

        dx, dy, dz = _compute_baseline(ecef, 1, 2)
        net.add_observation(GpsBaselineObservation(
            from_point=1, to_point=2, dx=dx, dy=dy, dz=dz,
        ))

        result = net.adjust()
        assert result.converged

        # adjusted_points should have geodetic degrees in northing/easting
        adj2 = result.adjusted_points[2]
        assert adj2.northing == pytest.approx(math.degrees(_GPS_POINTS[2][0]), abs=1e-6)
        assert adj2.easting == pytest.approx(math.degrees(_GPS_POINTS[2][1]), abs=1e-6)
        assert adj2.elevation == pytest.approx(_GPS_POINTS[2][2], abs=0.01)

    def test_mixed_2d_3d_raises(self):
        """Mixing 2D and GPS observations should raise an error."""
        net = Network()
        net.add_fixed_point_3d(1, *_GPS_POINTS[1])
        net.add_approximate_point_3d(2, *_GPS_POINTS[2])

        net.add_observation(GpsBaselineObservation(
            from_point=1, to_point=2, dx=1.0, dy=2.0, dz=3.0,
        ))
        net.add_observation(DistanceObservation(from_point=1, to_point=2, distance=100.0))

        with pytest.raises(ValueError, match="Mixed"):
            net.adjust()
