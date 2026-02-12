"""Adjustments: compass rule, Helmert transformation, coordinate transforms, LSA."""

from cogopro.adjustments.compass_rule import CompassRuleResult, compass_rule
from cogopro.adjustments.helmert import HelmertResult, apply_helmert, helmert_2d
from cogopro.adjustments.transforms import average, mirror, rotate, scale, shift

# Least-squares is optional (requires numpy)
try:
    from cogopro.adjustments.least_squares import (
        AdjustmentResult,
        AngleObservation,
        AzimuthObservation,
        DirectionObservation,
        DistanceObservation,
        Network,
    )

    _LSA_AVAILABLE = True
except ImportError:
    _LSA_AVAILABLE = False

__all__ = [
    "CompassRuleResult",
    "HelmertResult",
    "apply_helmert",
    "average",
    "compass_rule",
    "helmert_2d",
    "mirror",
    "rotate",
    "scale",
    "shift",
]

if _LSA_AVAILABLE:
    __all__ += [
        "AdjustmentResult",
        "AngleObservation",
        "AzimuthObservation",
        "DirectionObservation",
        "DistanceObservation",
        "Network",
    ]
