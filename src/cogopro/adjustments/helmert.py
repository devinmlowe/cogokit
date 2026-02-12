"""2D Helmert (similarity) transformation via least-squares."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogopro.core import Point


@dataclass
class HelmertResult:
    """Result of a 2D Helmert transformation computation."""

    a: float  # s * cos(theta)
    b: float  # s * sin(theta)
    tx: float  # translation in northing
    ty: float  # translation in easting
    scale: float
    rotation: float  # radians
    residuals: list[tuple[float, float]]  # (dN, dE) at each control point
    rmse: float


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve Ax = b using Gaussian elimination with partial pivoting."""
    n = len(matrix)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]

    for col in range(n):
        # Partial pivoting
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]

        pivot = aug[col][col]
        if abs(pivot) < 1e-15:
            raise ValueError("Singular or near-singular matrix in Helmert solution")

        for row in range(col + 1, n):
            factor = aug[row][col] / pivot
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n]
        for j in range(i + 1, n):
            s -= aug[i][j] * x[j]
        x[i] = s / aug[i][i]

    return x


def helmert_2d(
    source: list[Point],
    target: list[Point],
) -> HelmertResult:
    """Compute 2D Helmert (similarity) transformation parameters.

    Finds the best-fit transformation from source to target coordinates
    using least-squares.  The model is:

        N' = a*N - b*E + tx
        E' = b*N + a*E + ty

    where a = scale*cos(rotation), b = scale*sin(rotation).

    Args:
        source: Points in the source system.
        target: Points in the target system.

    Returns:
        HelmertResult with transformation parameters, residuals, and RMSE.
    """
    if len(source) != len(target):
        raise ValueError("Source and target must have the same number of points")
    if len(source) < 2:
        raise ValueError("At least 2 control point pairs required")

    n = len(source)

    # Build normal equations  A^T A  x  =  A^T L
    ata = [[0.0] * 4 for _ in range(4)]
    atl = [0.0] * 4

    for i in range(n):
        ns, es = source[i].northing, source[i].easting
        nt, et = target[i].northing, target[i].easting

        # Two observation rows per point
        rows = [(ns, -es, 1.0, 0.0, nt), (es, ns, 0.0, 1.0, et)]
        for r0, r1, r2, r3, obs in rows:
            row = (r0, r1, r2, r3)
            for j in range(4):
                atl[j] += row[j] * obs
                for k in range(4):
                    ata[j][k] += row[j] * row[k]

    params = _solve_linear_system(ata, atl)
    a, b, tx, ty = params

    scale = math.hypot(a, b)
    rotation = math.atan2(b, a)

    # Residuals
    residuals: list[tuple[float, float]] = []
    sum_sq = 0.0
    for i in range(n):
        ns, es = source[i].northing, source[i].easting
        nt, et = target[i].northing, target[i].easting
        comp_n = a * ns - b * es + tx
        comp_e = b * ns + a * es + ty
        dn = nt - comp_n
        de = et - comp_e
        residuals.append((dn, de))
        sum_sq += dn * dn + de * de

    rmse = math.sqrt(sum_sq / (2 * n)) if n > 0 else 0.0

    return HelmertResult(
        a=a, b=b, tx=tx, ty=ty,
        scale=scale, rotation=rotation,
        residuals=residuals, rmse=rmse,
    )


def apply_helmert(
    result: HelmertResult,
    points: list[Point],
) -> list[Point]:
    """Apply a computed Helmert transformation to points.

    Args:
        result: HelmertResult from helmert_2d().
        points: Points to transform.

    Returns:
        Transformed Points (preserving number and description).
    """
    out: list[Point] = []
    for pt in points:
        new_n = result.a * pt.northing - result.b * pt.easting + result.tx
        new_e = result.b * pt.northing + result.a * pt.easting + result.ty
        out.append(Point(
            northing=new_n,
            easting=new_e,
            elevation=pt.elevation,
            number=pt.number,
            description=pt.description,
        ))
    return out
