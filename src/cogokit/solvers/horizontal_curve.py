"""Horizontal (circular) curve solver, 3-point curve, and spiral basics.

Conventions:
- All angles in radians.
- Degree of curve (D) uses the arc definition: D = 5729.57795130823 / R
  (i.e. the central angle for a 100-ft arc).
- Stations increase along the arc from PC to PT.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogokit.core import Point


# Arc-definition constant: 100 * (180/pi) = 5729.57795130823
_D_CONST = 5729.57795130823


@dataclass(frozen=True)
class CurveElements:
    """Solved circular curve elements."""
    R: float       # radius
    delta: float   # central angle (radians)
    T: float       # tangent length
    L: float       # arc length
    C: float       # long chord length
    E: float       # external distance
    M: float       # middle ordinate
    D: float       # degree of curve (arc definition, degrees)


def solve_curve(*, R: float | None = None, delta: float | None = None,
                T: float | None = None, L: float | None = None,
                C: float | None = None, E: float | None = None,
                M: float | None = None, D: float | None = None) -> CurveElements:
    """Solve a circular curve given any two independent elements.

    Provide exactly two keyword arguments.  The solver derives R and delta
    first, then computes all remaining elements.
    """
    given = {k: v for k, v in locals().items() if v is not None}
    if len(given) != 2:
        raise ValueError(f"Provide exactly 2 elements; got {len(given)}.")

    r, d = _resolve_R_delta(given)
    if r <= 0:
        raise ValueError("Radius must be positive.")
    if d <= 0 or d >= math.pi:
        raise ValueError("Central angle must be in (0, pi).")

    return _compute_all(r, d)


def _resolve_R_delta(given: dict[str, float]) -> tuple[float, float]:
    """Derive R and delta from two known elements."""
    g = dict(given)  # mutable copy

    # Direct knowns
    if "R" in g and "delta" in g:
        return g["R"], g["delta"]

    # D <-> R conversion
    if "D" in g:
        g["R"] = _D_CONST / g["D"]
    if "R" in g and "D" not in g:
        pass  # fine, we may still need delta

    # If we now have R, recover delta from whichever element is given
    if "R" in g:
        r = g["R"]
        if "delta" in g:
            return r, g["delta"]
        if "T" in g:
            return r, 2 * math.atan(g["T"] / r)
        if "L" in g:
            return r, g["L"] / r
        if "C" in g:
            return r, 2 * math.asin(g["C"] / (2 * r))
        if "E" in g:
            return r, 2 * math.acos(r / (r + g["E"]))
        if "M" in g:
            return r, 2 * math.acos(1 - g["M"] / r)

    # If we have delta, recover R from whichever element is given
    if "delta" in g:
        d = g["delta"]
        if "T" in g:
            return g["T"] / math.tan(d / 2), d
        if "L" in g:
            return g["L"] / d, d
        if "C" in g:
            return g["C"] / (2 * math.sin(d / 2)), d
        if "E" in g:
            return g["E"] / (1 / math.cos(d / 2) - 1), d
        if "M" in g:
            return g["M"] / (1 - math.cos(d / 2)), d

    # Two non-R, non-delta elements: solve by pairing formulas.
    # T and L: T = R*tan(d/2), L = R*d  -->  T/L = tan(d/2)/d
    # Use Newton iteration on f(d) = tan(d/2)/d - T/L = 0
    if "T" in g and "L" in g:
        target = g["T"] / g["L"]
        d = _newton_TL(target)
        return g["L"] / d, d
    if "T" in g and "C" in g:
        # T/C = tan(d/2) / (2*sin(d/2)) = 1/(2*cos(d/2))
        cos_half = g["C"] / (2 * g["T"])
        d = 2 * math.acos(cos_half)
        return g["T"] / math.tan(d / 2), d
    if "T" in g and "E" in g:
        # E = T * sin(d/2) / (cos(d/2) + cos(d/2)... )  simplify:
        # T = R*tan(d/2), E = R*(sec(d/2)-1) => E/T = (1-cos(d/2))/sin(d/2) = tan(d/4)
        d = 4 * math.atan(g["E"] / g["T"])
        return g["T"] / math.tan(d / 2), d
    if "T" in g and "M" in g:
        # T = R*tan(d/2), M = R*(1-cos(d/2))
        # M/T = (1-cos(d/2))/tan(d/2) = (1-cos(d/2))*cos(d/2)/sin(d/2)
        # Use: M/T = sin(d/2)/(1+cos(d/2))... = tan(d/4)
        # Actually M/T = (1-cos(d/2))/tan(d/2) = sin^2(d/2)/(sin(d/2)) ... let me derive:
        # M/T = (1-cos(d/2)) * cos(d/2) / sin(d/2)
        # Use half-angle: let h = d/4, then d/2 = 2h
        # 1-cos(2h) = 2*sin^2(h), tan(2h) = 2*tan(h)/(1-tan^2(h))
        # This gets complex; use Newton's method
        d = _newton_generic(
            lambda dd: (1 - math.cos(dd/2)) / math.tan(dd/2) - g["M"] / g["T"],
            init=1.0,
        )
        return g["T"] / math.tan(d / 2), d

    # Fall back to Newton for remaining pairs
    keys = sorted(given.keys())
    raise ValueError(f"Cannot directly solve from pair: {keys}. Provide R or delta.")


def _newton_TL(target: float, tol: float = 1e-12, maxiter: int = 50) -> float:
    """Solve tan(d/2)/d = target for d via Newton's method."""
    d = 1.0  # initial guess
    for _ in range(maxiter):
        half = d / 2
        t = math.tan(half)
        f = t / d - target
        # df/dd = (sec^2(half)/2 * d - t) / d^2
        sec2 = 1 / math.cos(half) ** 2
        fp = (sec2 / 2 * d - t) / d**2
        if abs(fp) < 1e-30:
            break
        d -= f / fp
        if abs(f) < tol:
            break
    return d


def _newton_generic(f, init: float = 1.0, tol: float = 1e-12,
                    maxiter: int = 50, h: float = 1e-8) -> float:
    """Solve f(d) = 0 via Newton's method with numerical derivative."""
    d = init
    for _ in range(maxiter):
        fd = f(d)
        if abs(fd) < tol:
            break
        fp = (f(d + h) - f(d - h)) / (2 * h)
        if abs(fp) < 1e-30:
            break
        d -= fd / fp
    return d


def _compute_all(R: float, delta: float) -> CurveElements:
    """Compute all curve elements from R and delta."""
    half = delta / 2
    return CurveElements(
        R=R,
        delta=delta,
        T=R * math.tan(half),
        L=R * delta,
        C=2 * R * math.sin(half),
        E=R * (1 / math.cos(half) - 1),
        M=R * (1 - math.cos(half)),
        D=_D_CONST / R,
    )


# --- 3-point curve -----------------------------------------------------------

def three_point_curve(x1: float, y1: float,
                      x2: float, y2: float,
                      x3: float, y3: float) -> tuple[float, float, float]:
    """Compute circumscribed circle (circumcenter and circumradius) from 3 points.

    Returns (cx, cy, R) where (cx, cy) is the circumcenter.
    Raises ValueError if points are collinear.
    """
    ax, ay = x1, y1
    bx, by = x2, y2
    cx, cy = x3, y3

    D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(D) < 1e-12:
        raise ValueError("Points are collinear; no unique circle exists.")

    ux = ((ax**2 + ay**2) * (by - cy) +
          (bx**2 + by**2) * (cy - ay) +
          (cx**2 + cy**2) * (ay - by)) / D
    uy = ((ax**2 + ay**2) * (cx - bx) +
          (bx**2 + by**2) * (ax - cx) +
          (cx**2 + cy**2) * (bx - ax)) / D

    R = math.hypot(ax - ux, ay - uy)
    return ux, uy, R


# --- Spiral (clothoid / Euler spiral) basics ---------------------------------

@dataclass(frozen=True)
class SpiralElements:
    """Basic clothoid spiral parameters."""
    Ls: float       # spiral length
    R: float        # radius at end of spiral
    theta_s: float  # spiral angle (radians)
    X: float        # tangent offset (X coord at end of spiral)
    Y: float        # tangent offset (Y coord at end of spiral)
    p: float        # offset from tangent to shifted PC
    k: float        # increase in tangent length due to spiral


def spiral(Ls: float, R: float) -> SpiralElements:
    """Compute spiral (clothoid) parameters given spiral length and radius.

    Uses series approximations for X and Y (sufficient for most survey work).
    """
    if Ls <= 0 or R <= 0:
        raise ValueError("Ls and R must be positive.")

    theta_s = Ls / (2 * R)
    ts2 = theta_s**2

    # Series expansions (truncated; accurate for theta_s < ~0.5 rad)
    X = Ls * (1 - ts2 / 10 + ts2**2 / 216 - ts2**3 / 9360)
    Y = Ls * (theta_s / 3 - ts2 * theta_s / 42 + ts2**2 * theta_s / 1320
              - ts2**3 * theta_s / 75600)

    p = Y - R * (1 - math.cos(theta_s))
    k = X - R * math.sin(theta_s)

    return SpiralElements(Ls=Ls, R=R, theta_s=theta_s, X=X, Y=Y, p=p, k=k)


def three_point_curve_from_points(
    p1: Point, p2: Point, p3: Point,
) -> tuple[Point, float]:
    """Compute circumscribed circle from three core.Point objects.

    Parameters:
        p1, p2, p3: Points (using easting as x, northing as y).

    Returns:
        (center_point, radius) where center_point is a core.Point at the
        circumcenter and radius is the circumradius.

    Raises:
        ValueError: If points are collinear.
    """
    cx, cy, R = three_point_curve(
        p1.easting, p1.northing,
        p2.easting, p2.northing,
        p3.easting, p3.northing,
    )
    return Point(northing=cy, easting=cx), R
