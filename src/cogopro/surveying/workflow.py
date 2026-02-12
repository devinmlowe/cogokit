"""Traverse workflow: field-to-final pipeline for traverse adjustments."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cogopro.adjustments.compass_rule import compass_rule
from cogopro.cogo.traverse import traverse
from cogopro.core import Angle, Point
from cogopro.core.job import Job


@dataclass
class TraverseLeg:
    """A single leg in a traverse workflow."""

    occupied: int
    backsight: int
    foresight: int
    angle_dms: float  # turned angle in HP notation (DDD.MMSS)
    distance: float  # slope distance (assumed horizontal if no vertical angle)
    hi: float = 0.0
    ht: float = 0.0


@dataclass
class TraverseResult:
    """Complete results from a traverse workflow computation."""

    raw_points: list[Point]
    adjusted_points: list[Point]
    angular_misclosure: Angle
    angular_tolerance: Angle
    closure_north: float
    closure_east: float
    linear_misclosure: float
    perimeter: float
    precision_ratio: float  # the N in "1:N"
    adjusted_job: Job


class TraverseWorkflow:
    """High-level traverse workflow: reduce, close, adjust.

    Chains field observations through reduction, angular closure check,
    coordinate computation, linear closure, and compass rule adjustment.
    """

    def __init__(
        self,
        start_point: Point,
        start_azimuth: float | None = None,
        close_to_start: bool = True,
        close_to_point: Point | None = None,
    ):
        self.start_point = start_point
        self.start_azimuth = start_azimuth  # HP notation (DDD.MMSS)
        self.close_to_start = close_to_start
        self.close_to_point = close_to_point
        self._legs: list[TraverseLeg] = []

    def add_leg(
        self,
        occupied: int,
        backsight: int,
        foresight: int,
        angle_dms: float,
        distance: float,
        hi: float = 0.0,
        ht: float = 0.0,
    ) -> None:
        """Add a traverse leg to the workflow."""
        self._legs.append(
            TraverseLeg(occupied, backsight, foresight, angle_dms, distance, hi, ht)
        )

    def run(self) -> TraverseResult:
        """Execute the full traverse workflow pipeline.

        Steps:
            1. Convert HP-notation angles to radians
            2. Reduce slope distances to horizontal
            3. Compute angular closure and distribute misclosure
            4. Compute preliminary coordinates via sequential forward traverse
            5. Compute linear closure and apply compass rule adjustment
        """
        if not self._legs:
            raise ValueError("No traverse legs added")
        if self.start_azimuth is None:
            raise ValueError("Start azimuth is required")

        # Step 1-2: Convert angles and reduce distances
        angles_rad = self._convert_angles()
        distances = self._reduce_distances()

        # Step 3: Angular closure
        n = len(angles_rad)
        theoretical = math.radians((n - 2) * 180.0)
        observed_sum = sum(angles_rad)
        misclosure_rad = observed_sum - theoretical

        # Step 4: Distribute angular misclosure equally
        correction = -misclosure_rad / n
        corrected_angles = [a + correction for a in angles_rad]

        angular_misclosure = Angle.from_radians(misclosure_rad)
        angular_tolerance = Angle.from_dms(0, 0, 10) * math.sqrt(n)

        # Step 5: Compute preliminary coordinates
        raw_points = self._compute_coordinates(corrected_angles, distances)

        # Step 6-7: Linear closure and compass rule
        known_end = None
        if not self.close_to_start and self.close_to_point is not None:
            known_end = self.close_to_point

        cr = compass_rule(raw_points, known_end)

        # Build adjusted job with unique points
        adjusted_job = Job(name="Traverse Adjustment")
        seen: set[int] = set()
        for pt in cr.adjusted:
            if pt.number is not None and pt.number not in seen:
                adjusted_job.add_point(pt)
                seen.add(pt.number)

        return TraverseResult(
            raw_points=raw_points,
            adjusted_points=cr.adjusted,
            angular_misclosure=angular_misclosure,
            angular_tolerance=angular_tolerance,
            closure_north=cr.misclosure_n,
            closure_east=cr.misclosure_e,
            linear_misclosure=cr.linear_misclosure,
            perimeter=cr.total_length,
            precision_ratio=cr.precision_ratio,
            adjusted_job=adjusted_job,
        )

    def _convert_angles(self) -> list[float]:
        """Convert HP-notation angles to radians."""
        return [Angle.from_hp_notation(leg.angle_dms).radians for leg in self._legs]

    def _reduce_distances(self) -> list[float]:
        """Reduce slope distances to horizontal.

        Assumes horizontal distances when no vertical angle is provided.
        """
        return [leg.distance for leg in self._legs]

    def _compute_coordinates(
        self, corrected_angles: list[float], distances: list[float]
    ) -> list[Point]:
        """Compute preliminary coordinates from corrected angles and distances."""
        start_az_rad = Angle.from_hp_notation(self.start_azimuth).radians

        coords: list[Point] = [self.start_point]
        current_backsight_az = start_az_rad

        for i, (angle, dist) in enumerate(zip(corrected_angles, distances)):
            foresight_az = (current_backsight_az + angle) % (2 * math.pi)
            new_pt = traverse(
                coords[-1], foresight_az, dist, elevation=self.start_point.elevation
            )
            new_pt = Point(
                northing=new_pt.northing,
                easting=new_pt.easting,
                elevation=new_pt.elevation,
                number=self._legs[i].foresight,
            )
            coords.append(new_pt)
            # Next station's backsight is reverse of current foresight
            current_backsight_az = (foresight_az + math.pi) % (2 * math.pi)

        return coords
