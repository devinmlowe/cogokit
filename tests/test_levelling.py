"""Tests for differential levelling module."""

import math

from cogokit.surveying.levelling import (
    LevelObservation,
    LevelRun,
    adjust_level_loop,
    reduce_level_run,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _obs(name, *, bs=None, fs=None, intermediate=None):
    return LevelObservation(name, backsight=bs, foresight=fs, intermediate=intermediate)


# ---------------------------------------------------------------------------
# reduce_level_run tests
# ---------------------------------------------------------------------------


def test_simple_bs_fs_run():
    """Three turning points between two benchmarks."""
    observations = [
        _obs("BM1", bs=5.000),
        _obs("TP1", fs=3.500, bs=4.200),
        _obs("TP2", fs=2.800, bs=6.100),
        _obs("TP3", fs=1.900, bs=3.700),
        _obs("BM2", fs=4.500),
    ]
    result = reduce_level_run(observations, start_elevation=100.000)

    assert math.isclose(result.elevations["BM1"], 100.000, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP1"], 101.500, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP2"], 102.900, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP3"], 107.100, abs_tol=1e-10)
    assert math.isclose(result.elevations["BM2"], 106.300, abs_tol=1e-10)
    assert math.isclose(result.closure_error, 0.0, abs_tol=1e-10)


def test_level_run_with_intermediate_sights():
    """Intermediate sights between setups."""
    observations = [
        _obs("BM1", bs=5.000),
        _obs("IS1", intermediate=2.500),
        _obs("IS2", intermediate=3.200),
        _obs("TP1", fs=3.500, bs=4.200),
        _obs("IS3", intermediate=1.800),
        _obs("BM2", fs=2.000),
    ]
    result = reduce_level_run(observations, start_elevation=100.000)

    # HI_0 = 100 + 5 = 105
    assert math.isclose(result.elevations["BM1"], 100.000, abs_tol=1e-10)
    assert math.isclose(result.elevations["IS1"], 102.500, abs_tol=1e-10)
    assert math.isclose(result.elevations["IS2"], 101.800, abs_tol=1e-10)
    # TP1: elev = 105 - 3.5 = 101.5, HI_1 = 101.5 + 4.2 = 105.7
    assert math.isclose(result.elevations["TP1"], 101.500, abs_tol=1e-10)
    assert math.isclose(result.elevations["IS3"], 103.900, abs_tol=1e-10)
    assert math.isclose(result.elevations["BM2"], 103.700, abs_tol=1e-10)


def test_multiple_turning_points():
    """Five turning points between two benchmarks."""
    observations = [
        _obs("BM1", bs=4.500),
        _obs("TP1", fs=2.100, bs=3.800),
        _obs("TP2", fs=1.500, bs=5.200),
        _obs("TP3", fs=3.300, bs=2.900),
        _obs("TP4", fs=4.100, bs=3.600),
        _obs("TP5", fs=2.700, bs=4.800),
        _obs("BM2", fs=3.200),
    ]
    result = reduce_level_run(observations, start_elevation=100.000)

    # HI0=104.5  TP1=102.4 HI1=106.2  TP2=104.7 HI2=109.9
    # TP3=106.6 HI3=109.5  TP4=105.4 HI4=109.0  TP5=106.3 HI5=111.1
    # BM2=107.9
    assert math.isclose(result.elevations["BM1"], 100.000, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP1"], 102.400, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP2"], 104.700, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP3"], 106.600, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP4"], 105.400, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP5"], 106.300, abs_tol=1e-10)
    assert math.isclose(result.elevations["BM2"], 107.900, abs_tol=1e-10)


# ---------------------------------------------------------------------------
# adjust_level_loop tests
# ---------------------------------------------------------------------------


def test_loop_closure_with_adjustment():
    """Distribute closure error across 4 FS stations."""
    observations = [
        _obs("BM1", bs=5.000),
        _obs("TP1", fs=3.500, bs=4.200),
        _obs("TP2", fs=2.800, bs=6.100),
        _obs("TP3", fs=1.900, bs=3.700),
        _obs("BM2", fs=4.500),
    ]
    # Computed BM2 = 106.300; known end = 106.000
    result = adjust_level_loop(observations, 100.000, end_elevation=106.000)

    assert math.isclose(result.closure_error, 0.300, abs_tol=1e-10)

    # Proportional corrections: -(k/4)*0.3
    assert math.isclose(result.adjustments["BM1"], 0.000, abs_tol=1e-10)
    assert math.isclose(result.adjustments["TP1"], -0.075, abs_tol=1e-10)
    assert math.isclose(result.adjustments["TP2"], -0.150, abs_tol=1e-10)
    assert math.isclose(result.adjustments["TP3"], -0.225, abs_tol=1e-10)
    assert math.isclose(result.adjustments["BM2"], -0.300, abs_tol=1e-10)

    # Adjusted elevations
    assert math.isclose(result.elevations["BM1"], 100.000, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP1"], 101.425, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP2"], 102.750, abs_tol=1e-10)
    assert math.isclose(result.elevations["TP3"], 106.875, abs_tol=1e-10)
    assert math.isclose(result.elevations["BM2"], 106.000, abs_tol=1e-10)


def test_zero_closure_error():
    """When computed end matches known end, no adjustments are applied."""
    observations = [
        _obs("BM1", bs=5.000),
        _obs("TP1", fs=3.500, bs=4.200),
        _obs("TP2", fs=2.800, bs=6.100),
        _obs("TP3", fs=1.900, bs=3.700),
        _obs("BM2", fs=4.500),
    ]
    # Known end equals computed end (106.300)
    result = adjust_level_loop(observations, 100.000, end_elevation=106.300)

    assert math.isclose(result.closure_error, 0.0, abs_tol=1e-10)

    for adj in result.adjustments.values():
        assert math.isclose(adj, 0.0, abs_tol=1e-10)

    # Elevations should match the unadjusted reduction
    unadjusted = reduce_level_run(observations, 100.000)
    for name in unadjusted.elevations:
        assert math.isclose(
            result.elevations[name],
            unadjusted.elevations[name],
            abs_tol=1e-10,
        )


def test_loop_adjustment_with_intermediate_sights():
    """Intermediate sights receive the correction of the current setup."""
    observations = [
        _obs("BM1", bs=5.000),
        _obs("IS1", intermediate=2.500),
        _obs("TP1", fs=3.500, bs=4.200),
        _obs("IS2", intermediate=1.800),
        _obs("BM2", fs=2.000),
    ]
    # Unadjusted: BM1=100, IS1=102.5, TP1=101.5, IS2=103.9, BM2=103.7
    # Known end = 103.500 → closure = 103.7 - 103.5 = 0.2
    result = adjust_level_loop(observations, 100.000, end_elevation=103.500)

    assert math.isclose(result.closure_error, 0.200, abs_tol=1e-10)

    # 2 FS observations (TP1, BM2)
    # BM1: 0.0
    # IS1: same as setup 0 → -(0/2)*0.2 = 0.0
    # TP1: -(1/2)*0.2 = -0.1
    # IS2: same as setup 1 (after TP1 FS) → -(1/2)*0.2 = -0.1
    # BM2: -(2/2)*0.2 = -0.2
    assert math.isclose(result.adjustments["BM1"], 0.000, abs_tol=1e-10)
    assert math.isclose(result.adjustments["IS1"], 0.000, abs_tol=1e-10)
    assert math.isclose(result.adjustments["TP1"], -0.100, abs_tol=1e-10)
    assert math.isclose(result.adjustments["IS2"], -0.100, abs_tol=1e-10)
    assert math.isclose(result.adjustments["BM2"], -0.200, abs_tol=1e-10)

    # Adjusted end station must equal known elevation
    assert math.isclose(result.elevations["BM2"], 103.500, abs_tol=1e-10)


def test_level_run_dataclass():
    """LevelRun is a simple container for observations + start elevation."""
    observations = [_obs("BM1", bs=1.0), _obs("BM2", fs=1.0)]
    run = LevelRun(observations=observations, start_elevation=100.0)
    assert run.start_elevation == 100.0
    assert len(run.observations) == 2
