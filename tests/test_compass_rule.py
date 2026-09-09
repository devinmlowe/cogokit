"""Tests for compass rule (Bowditch) traverse adjustment."""

import math

import pytest

from cogokit.adjustments.compass_rule import compass_rule
from cogokit.core import Point


def test_closed_loop_traverse():
    """Adjust a closed-loop square traverse and verify precision ratio."""
    # Square traverse with 0.04N / 0.03E misclosure → linear = 0.05
    coords = [
        Point(northing=1000.0, easting=1000.0),
        Point(northing=1000.0, easting=1100.0),
        Point(northing=1100.0, easting=1100.0),
        Point(northing=1100.0, easting=1000.0),
        Point(northing=1000.04, easting=1000.03),
    ]

    result = compass_rule(coords)

    assert math.isclose(result.misclosure_n, 0.04, abs_tol=1e-10)
    assert math.isclose(result.misclosure_e, 0.03, abs_tol=1e-10)
    assert math.isclose(result.linear_misclosure, 0.05, abs_tol=1e-10)
    assert math.isclose(result.total_length, 400.0, rel_tol=1e-3)
    assert math.isclose(result.precision_ratio, 8000.0, rel_tol=1e-2)

    # First point unchanged
    assert result.adjusted[0].northing == 1000.0
    assert result.adjusted[0].easting == 1000.0

    # Last point coincides with first
    assert math.isclose(result.adjusted[-1].northing, 1000.0, abs_tol=1e-10)
    assert math.isclose(result.adjusted[-1].easting, 1000.0, abs_tol=1e-10)


def test_corrections_proportional():
    """Corrections should be proportional to cumulative distance."""
    # Equilateral-ish triangle: legs ≈ 100, 100, 100
    coords = [
        Point(northing=0.0, easting=0.0),
        Point(northing=100.0, easting=0.0),
        Point(northing=50.0, easting=86.6025),
        Point(northing=0.04, easting=0.03),  # misclosure back to origin
    ]
    result = compass_rule(coords)

    # With roughly equal legs, midpoint correction ≈ half the full correction
    # Point 2 is ~2/3 through → correction ≈ 2/3 of misclosure
    total = result.total_length
    cum1 = 100.0
    cum2 = cum1 + math.hypot(50.0 - 100.0, 86.6025 - 0.0)
    assert math.isclose(
        result.adjusted[1].northing, 100.0 - 0.04 * cum1 / total, abs_tol=1e-6
    )
    assert math.isclose(
        result.adjusted[2].northing, 50.0 - 0.04 * cum2 / total, abs_tol=1e-6
    )
    # Last point matches start
    assert math.isclose(result.adjusted[-1].northing, 0.0, abs_tol=1e-10)
    assert math.isclose(result.adjusted[-1].easting, 0.0, abs_tol=1e-10)


def test_fixed_endpoint_traverse():
    """Adjust a fixed-endpoint traverse."""
    coords = [
        Point(northing=1000.0, easting=1000.0),
        Point(northing=1000.0, easting=1100.0),
        Point(northing=1100.0, easting=1100.03),
    ]
    known_end = Point(northing=1100.0, easting=1100.0)

    result = compass_rule(coords, known_end=known_end)

    assert math.isclose(result.misclosure_n, 0.0, abs_tol=1e-10)
    assert math.isclose(result.misclosure_e, 0.03, abs_tol=1e-10)
    assert math.isclose(result.adjusted[-1].northing, 1100.0, abs_tol=1e-10)
    assert math.isclose(result.adjusted[-1].easting, 1100.0, abs_tol=1e-10)


def test_zero_misclosure():
    """No misclosure should return coordinates unchanged."""
    coords = [
        Point(northing=0.0, easting=0.0),
        Point(northing=100.0, easting=0.0),
        Point(northing=100.0, easting=100.0),
        Point(northing=0.0, easting=0.0),
    ]
    result = compass_rule(coords)

    assert math.isclose(result.linear_misclosure, 0.0, abs_tol=1e-10)
    assert result.precision_ratio == float("inf")
    for orig, adj in zip(coords, result.adjusted):
        assert math.isclose(orig.northing, adj.northing, abs_tol=1e-10)
        assert math.isclose(orig.easting, adj.easting, abs_tol=1e-10)


def test_too_few_points():
    """Compass rule needs at least 3 points."""
    with pytest.raises(ValueError):
        compass_rule([
            Point(northing=0.0, easting=0.0),
            Point(northing=1.0, easting=1.0),
        ])
