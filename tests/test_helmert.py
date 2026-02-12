"""Tests for 2D Helmert (similarity) transformation."""

import math

import pytest

from cogopro.adjustments.helmert import apply_helmert, helmert_2d

# HELMERTS.txt data (point_number northing easting elevation description)
HELMERTS_SOURCE = [
    (3002.0000, 2970.0000),
    (3002.0000, 2997.3240),
    (3004.4369, 2999.9736),
    (3004.3983, 2972.3691),
    (2994.9164, 2970.1321),
    (2992.7957, 2977.8281),
    (3001.6433, 2980.1024),
    (2998.2278, 2993.3873),
    (2989.3818, 2991.1114),
    (2983.7203, 3003.2333),
    (2980.4860, 2998.9078),
]


def _make_target(
    source: list[tuple[float, float]],
    s: float,
    theta: float,
    tx: float,
    ty: float,
) -> list[tuple[float, float]]:
    """Apply known Helmert parameters to generate target coordinates."""
    a = s * math.cos(theta)
    b = s * math.sin(theta)
    return [(a * n - b * e + tx, b * n + a * e + ty) for n, e in source]


def test_identity():
    """Identity transformation: scale=1, rotation=0, no translation."""
    source = [(100.0, 200.0), (300.0, 400.0), (500.0, 100.0)]

    result = helmert_2d(source, source)

    assert math.isclose(result.scale, 1.0, abs_tol=1e-10)
    assert math.isclose(result.rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(result.tx, 0.0, abs_tol=1e-6)
    assert math.isclose(result.ty, 0.0, abs_tol=1e-6)
    assert result.rmse < 1e-10


def test_pure_translation():
    """Pure translation: scale=1, rotation=0."""
    source = [(100.0, 200.0), (300.0, 400.0), (500.0, 100.0)]
    target = [(110.0, 220.0), (310.0, 420.0), (510.0, 120.0)]

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
    source = [(100.0, 200.0), (300.0, 400.0)]
    target = _make_target(source, 1.5, math.radians(30), 10.0, 20.0)

    result = helmert_2d(source, target)

    new_points = [(150.0, 250.0)]
    transformed = apply_helmert(result, new_points)
    expected = _make_target(new_points, 1.5, math.radians(30), 10.0, 20.0)

    assert math.isclose(transformed[0][0], expected[0][0], abs_tol=1e-6)
    assert math.isclose(transformed[0][1], expected[0][1], abs_tol=1e-6)


def test_minimum_two_points():
    """Exactly 2 control points gives an exact solution."""
    source = [(0.0, 0.0), (100.0, 0.0)]
    target = [(10.0, 20.0), (110.0, 20.0)]

    result = helmert_2d(source, target)

    assert math.isclose(result.scale, 1.0, abs_tol=1e-10)
    assert math.isclose(result.tx, 10.0, abs_tol=1e-6)
    assert math.isclose(result.ty, 20.0, abs_tol=1e-6)
    assert result.rmse < 1e-10


def test_too_few_points():
    """Must have at least 2 control point pairs."""
    with pytest.raises(ValueError):
        helmert_2d([(0, 0)], [(1, 1)])


def test_mismatched_counts():
    """Source and target must have the same length."""
    with pytest.raises(ValueError):
        helmert_2d([(0, 0), (1, 1)], [(0, 0)])
