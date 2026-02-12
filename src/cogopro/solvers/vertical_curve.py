"""Vertical (parabolic) curve solver.

Supports equal-tangent parabolic vertical curves used in highway design.
Grades are expressed as decimal fractions (e.g., 0.03 for 3%).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerticalCurveData:
    """Solved vertical curve parameters."""
    bvc_station: float   # station of Beginning of Vertical Curve
    bvc_elevation: float
    evc_station: float   # station of End of Vertical Curve
    evc_elevation: float
    pvi_station: float   # station of Point of Vertical Intersection
    pvi_elevation: float
    G1: float            # grade in  (decimal)
    G2: float            # grade out (decimal)
    L: float             # curve length (station units)
    K: float             # rate of curvature: L / |G2 - G1| (in percent terms)
    high_low_station: float | None     # station of high/low point (None if outside curve)
    high_low_elevation: float | None


def solve_vertical_curve(
    pvi_station: float,
    pvi_elevation: float,
    G1: float,
    G2: float,
    L: float,
) -> VerticalCurveData:
    """Solve an equal-tangent parabolic vertical curve.

    Parameters
    ----------
    pvi_station : float
        Station of the Point of Vertical Intersection.
    pvi_elevation : float
        Elevation at the PVI.
    G1 : float
        Grade in (decimal fraction, e.g. 0.03 for +3%).
    G2 : float
        Grade out (decimal fraction).
    L : float
        Length of the vertical curve (same units as stations).
    """
    if L <= 0:
        raise ValueError("Curve length must be positive.")

    half_L = L / 2
    bvc_station = pvi_station - half_L
    bvc_elevation = pvi_elevation - G1 * half_L

    evc_station = pvi_station + half_L
    evc_elevation = pvi_elevation + G2 * half_L

    # K value: L (in station units) / absolute change in grade (in percent)
    dg = G2 - G1
    if abs(dg) < 1e-15:
        raise ValueError("G1 and G2 must differ (no curve needed for equal grades).")

    # K = L / |G2% - G1%|  where grades are in percent
    K = L / abs(dg * 100)

    # High/low point: x from BVC where tangent slope = 0
    # slope at x: G1 + (G2-G1)/L * x = 0  =>  x = -G1*L / (G2-G1)
    x_hl = -G1 * L / dg

    if 0 < x_hl < L:
        hl_station = bvc_station + x_hl
        hl_elevation = elevation_at(bvc_elevation, G1, G2, L, x_hl)
    else:
        hl_station = None
        hl_elevation = None

    return VerticalCurveData(
        bvc_station=bvc_station,
        bvc_elevation=bvc_elevation,
        evc_station=evc_station,
        evc_elevation=evc_elevation,
        pvi_station=pvi_station,
        pvi_elevation=pvi_elevation,
        G1=G1,
        G2=G2,
        L=L,
        K=K,
        high_low_station=hl_station,
        high_low_elevation=hl_elevation,
    )


def elevation_at(bvc_elevation: float, G1: float, G2: float,
                 L: float, x: float) -> float:
    """Compute elevation at distance x from BVC along a vertical curve.

    Uses the standard parabolic equation:
        elev(x) = bvc_elevation + G1*x + ((G2 - G1) / (2*L)) * x^2
    """
    return bvc_elevation + G1 * x + ((G2 - G1) / (2 * L)) * x**2
