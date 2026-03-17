"""Triangle solver: solve any triangle given 3 known elements.

Supports SSS, SAS, ASA, AAS, and SSA (with ambiguous case).
All angles are in radians internally; the public API accepts/returns radians.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto


class SolveCase(Enum):
    """Which combination of knowns was provided."""
    SSS = auto()
    SAS = auto()
    ASA = auto()
    AAS = auto()
    SSA = auto()


@dataclass(frozen=True)
class TriangleSolution:
    """All six elements of a solved triangle plus derived quantities."""
    a: float
    b: float
    c: float
    A: float  # angle opposite side a (radians)
    B: float  # angle opposite side b (radians)
    C: float  # angle opposite side c (radians)
    area: float
    perimeter: float
    case: SolveCase


def _validate_triangle(a: float, b: float, c: float, A: float, B: float, C: float) -> None:
    """Raise ValueError if the solved values are geometrically invalid."""
    if any(s <= 0 for s in (a, b, c)):
        raise ValueError("All sides must be positive.")
    if any(ang <= 0 or ang >= math.pi for ang in (A, B, C)):
        raise ValueError("All angles must be in (0, pi).")
    if not math.isclose(A + B + C, math.pi, rel_tol=1e-9):
        raise ValueError("Angles must sum to pi.")


def _build_solution(a: float, b: float, c: float,
                    A: float, B: float, C: float,
                    case: SolveCase) -> TriangleSolution:
    _validate_triangle(a, b, c, A, B, C)
    area = 0.5 * a * b * math.sin(C)
    perimeter = a + b + c
    return TriangleSolution(a=a, b=b, c=c, A=A, B=B, C=C,
                            area=area, perimeter=perimeter, case=case)


def solve_sss(a: float, b: float, c: float) -> TriangleSolution:
    """Solve triangle given three sides."""
    if a <= 0 or b <= 0 or c <= 0:
        raise ValueError("All sides must be positive.")
    if a + b <= c or a + c <= b or b + c <= a:
        raise ValueError("Triangle inequality violated.")

    A = math.acos((b**2 + c**2 - a**2) / (2 * b * c))
    B = math.acos((a**2 + c**2 - b**2) / (2 * a * c))
    C = math.pi - A - B
    return _build_solution(a, b, c, A, B, C, SolveCase.SSS)


def solve_sas(a: float, C: float, b: float) -> TriangleSolution:
    """Solve triangle given two sides and the included angle.

    Parameters: side a, included angle C (between a and b), side b.
    """
    if a <= 0 or b <= 0:
        raise ValueError("Sides must be positive.")
    if C <= 0 or C >= math.pi:
        raise ValueError("Included angle must be in (0, pi).")

    c = math.sqrt(a**2 + b**2 - 2 * a * b * math.cos(C))
    A = math.acos((b**2 + c**2 - a**2) / (2 * b * c))
    B = math.pi - A - C
    return _build_solution(a, b, c, A, B, C, SolveCase.SAS)


def solve_asa(A: float, c: float, B: float) -> TriangleSolution:
    """Solve triangle given two angles and the included side.

    Parameters: angle A, included side c (between A and B), angle B.
    """
    if c <= 0:
        raise ValueError("Side must be positive.")
    C = math.pi - A - B
    if C <= 0 or A <= 0 or B <= 0:
        raise ValueError("All angles must be positive and sum to pi.")

    # Law of sines: a/sin(A) = c/sin(C)
    ratio = c / math.sin(C)
    a = ratio * math.sin(A)
    b = ratio * math.sin(B)
    return _build_solution(a, b, c, A, B, C, SolveCase.ASA)


def solve_aas(A: float, B: float, a: float) -> TriangleSolution:
    """Solve triangle given two angles and a non-included side.

    Parameters: angle A, angle B, side a (opposite angle A).
    """
    if a <= 0:
        raise ValueError("Side must be positive.")
    C = math.pi - A - B
    if C <= 0 or A <= 0 or B <= 0:
        raise ValueError("All angles must be positive and sum to pi.")

    ratio = a / math.sin(A)
    b = ratio * math.sin(B)
    c = ratio * math.sin(C)
    return _build_solution(a, b, c, A, B, C, SolveCase.AAS)


def solve_ssa(a: float, b: float, A: float) -> list[TriangleSolution]:
    """Solve triangle given two sides and an angle opposite one of them.

    Parameters: side a, side b, angle A (opposite side a).
    Returns a list of 0, 1, or 2 solutions (ambiguous case).
    """
    if a <= 0 or b <= 0:
        raise ValueError("Sides must be positive.")
    if A <= 0 or A >= math.pi:
        raise ValueError("Angle must be in (0, pi).")

    sin_B = b * math.sin(A) / a
    if sin_B > 1.0 + 1e-12:
        return []  # no solution
    sin_B = min(sin_B, 1.0)  # clamp for floating-point

    solutions: list[TriangleSolution] = []
    B1 = math.asin(sin_B)

    for B in (B1, math.pi - B1):
        C = math.pi - A - B
        if C <= 1e-12:
            continue
        ratio = a / math.sin(A)
        c = ratio * math.sin(C)
        if c <= 0:
            continue
        solutions.append(_build_solution(a, b, c, A, B, C, SolveCase.SSA))

    # Deduplicate when B1 ≈ pi - B1 (right-angle case)
    if len(solutions) == 2:
        if math.isclose(solutions[0].B, solutions[1].B, rel_tol=1e-9):
            solutions = solutions[:1]

    return solutions
