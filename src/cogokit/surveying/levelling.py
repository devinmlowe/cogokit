"""Differential levelling: reduce level runs and adjust loop closures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LevelObservation:
    """A single rod reading at a station in a level run."""

    station_name: str
    backsight: float | None = None
    foresight: float | None = None
    intermediate: float | None = None


@dataclass
class LevelRun:
    """An ordered sequence of level observations from one benchmark to another."""

    observations: list[LevelObservation]
    start_elevation: float


@dataclass
class LevelResult:
    """Results of a level run reduction or adjustment."""

    elevations: dict[str, float]
    closure_error: float
    adjustments: dict[str, float]


def reduce_level_run(
    observations: list[LevelObservation],
    start_elevation: float,
) -> LevelResult:
    """Reduce a differential level run to compute station elevations.

    Process BS/FS/IS observations sequentially:
    - BS at first station establishes HI = start_elevation + BS.
    - FS computes new elevation = HI - FS and becomes the current elevation.
    - A turning point (FS + BS) also establishes a new HI from the FS elevation.
    - Intermediate sights compute elevation = HI - IS without changing current elevation.
    """
    elevations: dict[str, float] = {}
    hi = 0.0
    current_elevation = start_elevation

    for obs in observations:
        # Foresight: compute elevation from current HI
        if obs.foresight is not None:
            current_elevation = hi - obs.foresight
            elevations[obs.station_name] = current_elevation

        # Intermediate sight: compute elevation from current HI (no setup change)
        if obs.intermediate is not None:
            elevations[obs.station_name] = hi - obs.intermediate

        # Backsight: establish new HI
        if obs.backsight is not None:
            if obs.foresight is None and obs.intermediate is None:
                # First station (benchmark) — record its known elevation
                elevations[obs.station_name] = current_elevation
            hi = current_elevation + obs.backsight

    return LevelResult(
        elevations=elevations,
        closure_error=0.0,
        adjustments={name: 0.0 for name in elevations},
    )


def adjust_level_loop(
    observations: list[LevelObservation],
    start_elevation: float,
    end_elevation: float,
) -> LevelResult:
    """Reduce a level run then distribute the closure error proportionally.

    Closure error = computed_end - known_end.  The correction is distributed
    across turning points (stations with foresight readings) proportionally
    to their position in the run.  Intermediate sights receive the same
    correction as the most recent preceding foresight station.
    """
    result = reduce_level_run(observations, start_elevation)

    # Identify the end station (last FS observation)
    end_station = None
    for obs in reversed(observations):
        if obs.foresight is not None:
            end_station = obs.station_name
            break

    if end_station is None:
        return result

    computed_end = result.elevations[end_station]
    closure_error = computed_end - end_elevation

    # Count total FS observations for proportional distribution
    total_fs = sum(1 for obs in observations if obs.foresight is not None)

    # Build per-station adjustments
    adjustments: dict[str, float] = {}
    fs_count = 0

    for obs in observations:
        if obs.foresight is not None:
            fs_count += 1
            adjustments[obs.station_name] = -(fs_count / total_fs) * closure_error
        elif obs.backsight is not None and obs.foresight is None:
            # Benchmark (start station) — no correction
            adjustments[obs.station_name] = 0.0
        elif obs.intermediate is not None:
            # IS inherits the correction of the current instrument setup
            adjustments[obs.station_name] = -(fs_count / total_fs) * closure_error

    # Apply adjustments
    adjusted_elevations = {
        name: elev + adjustments.get(name, 0.0)
        for name, elev in result.elevations.items()
    }

    return LevelResult(
        elevations=adjusted_elevations,
        closure_error=closure_error,
        adjustments=adjustments,
    )
