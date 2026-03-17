"""Unit system management for surveying computations."""

from __future__ import annotations

from enum import Enum


class LinearUnit(Enum):
    METER = "meter"
    FOOT = "foot"  # International foot
    US_SURVEY_FOOT = "us_survey_foot"


class AngularUnit(Enum):
    DEGREES = "degrees"
    RADIANS = "radians"
    DMS = "dms"
    GRADIANS = "gradians"


# Conversion factors to meters
_LINEAR_TO_METERS = {
    LinearUnit.METER: 1.0,
    LinearUnit.FOOT: 0.3048,
    LinearUnit.US_SURVEY_FOOT: 1200.0 / 3937.0,
}


def linear_conversion_factor(from_unit: LinearUnit, to_unit: LinearUnit) -> float:
    """Get the multiplicative factor to convert from one linear unit to another."""
    return _LINEAR_TO_METERS[from_unit] / _LINEAR_TO_METERS[to_unit]


def convert_linear(value: float, from_unit: LinearUnit, to_unit: LinearUnit) -> float:
    """Convert a linear measurement between unit systems."""
    if from_unit == to_unit:
        return value
    return value * linear_conversion_factor(from_unit, to_unit)
