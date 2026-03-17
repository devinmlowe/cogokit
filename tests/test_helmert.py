"""Tests for 2D Helmert (similarity) transformation."""

import math

import pytest

from cogokit.adjustments.helmert import apply_helmert, helmert_2d
from cogokit.core import Point

# HELMERTS.txt data (point_number northing easting elevation description)
HELMERTS_SOURCE = [
    Point(northing=3002.0000, easting=2970.0000),
    Point(northing=3002.0000, easting=2997.3240),
    Point(northing=3004.4369, easting=2999.9736),
    Point(northing=3004.3983, easting=2972.3691),
    Point(northing=2994.9164, easting=2970.1321),
    Point(northing=2992.7957, easting=2977.8281),
    Point(northing=3001.6433, easting=2980.1024),
    Point(northing=2998.2278, easting=2993.3873),
    Point(northing=2989.3818, easting=2991.1114),
    Point(northing=2983.7203, easting=3003.2333),
    Point(northing=2980.4860, easting=2998.9078),
]


def _make_target(
    source: list[Point],
    s: float,
    theta: float,
    tx: float,
    ty: float,
) -> list[Point]:
    """Apply known Helmert parameters to generate target coordinates."""
    a = s * math.cos(theta)
    b = s * math.sin(theta)
    return [
        Point(
            northing=a * pt.northing - b * pt.easting + tx,
            easting=b * pt.northing + a * pt.easting + ty,
        )
        for pt in source
    ]


def test_identity():
    """Identity transformation: scale=1, rotation=0, no translation."""
    source = [
        Point(northing=100.0, easting=200.0),
        Point(northing=300.0, easting=400.0),
        Point(northing=500.0, easting=100.0),
    ]

    result = helmert_2d(source, source)

    assert math.isclose(result.scale, 1.0, abs_tol=1e-10)
    assert math.isclose(result.rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(result.tx, 0.0, abs_tol=1e-6)
    assert math.isclose(result.ty, 0.0, abs_tol=1e-6)
    assert result.rmse < 1e-10


def test_pure_translation():
    """Pure translation: scale=1, rotation=0."""
    source = [
        Point(northing=100.0, easting=200.0),
        Point(northing=300.0, easting=400.0),
        Point(northing=500.0, easting=100.0),
    ]
    target = [
        Point(northing=110.0, easting=220.0),
        Point(northing=310.0, easting=420.0),
        Point(northing=510.0, easting=120.0),
    ]

    result = helmert_2d(source, target)

    assert math.isclose(result.scale, 1.0, abs_tol=1e-10)
    assert math.isclose(result.rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(result.tx, 10.0, abs_tol=1e-6)
    assert math.isclose(result.ty, 20.0, abs_tol=1e-6)


def test_with_helmerts_data():
    """Full Helmert using HELMERTS.txt source data with known transformation."""
    known_scale = 1.00025
    known_rotation = math.radians(0.5)
    known_tx = 50.0
    known_ty = -30.0

    target = _make_target(HELMERTS_SOURCE, known_scale, known_rotation, known_tx, known_ty)

    result = helmert_2d(HELMERTS_SOURCE, target)

    assert math.isclose(result.scale, known_scale, rel_tol=1e-8)
    assert math.isclose(result.rotation, known_rotation, abs_tol=1e-10)
    assert math.isclose(result.tx, known_tx, abs_tol=1e-4)
    assert math.isclose(result.ty, known_ty, abs_tol=1e-4)
    assert result.rmse < 1e-8


def test_apply_helmert():
    """Apply computed transformation to new points."""
    source = [
        Point(northing=100.0, easting=200.0),
        Point(northing=300.0, easting=400.0),
    ]
    target = _make_target(source, 1.5, math.radians(30), 10.0, 20.0)

    result = helmert_2d(source, target)

    new_points = [Point(northing=150.0, easting=250.0)]
    transformed = apply_helmert(result, new_points)
    expected = _make_target(new_points, 1.5, math.radians(30), 10.0, 20.0)

    assert math.isclose(transformed[0].northing, expected[0].northing, abs_tol=1e-6)
    assert math.isclose(transformed[0].easting, expected[0].easting, abs_tol=1e-6)


def test_minimum_two_points():
    """Exactly 2 control points gives an exact solution."""
    source = [
        Point(northing=0.0, easting=0.0),
        Point(northing=100.0, easting=0.0),
    ]
    target = [
        Point(northing=10.0, easting=20.0),
        Point(northing=110.0, easting=20.0),
    ]

    result = helmert_2d(source, target)

    assert math.isclose(result.scale, 1.0, abs_tol=1e-10)
    assert math.isclose(result.tx, 10.0, abs_tol=1e-6)
    assert math.isclose(result.ty, 20.0, abs_tol=1e-6)
    assert result.rmse < 1e-10


def test_too_few_points():
    """Must have at least 2 control point pairs."""
    with pytest.raises(ValueError):
        helmert_2d(
            [Point(northing=0.0, easting=0.0)],
            [Point(northing=1.0, easting=1.0)],
        )


def test_mismatched_counts():
    """Source and target must have the same length."""
    with pytest.raises(ValueError):
        helmert_2d(
            [Point(northing=0.0, easting=0.0), Point(northing=1.0, easting=1.0)],
            [Point(northing=0.0, easting=0.0)],
        )
