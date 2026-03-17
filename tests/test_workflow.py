"""Tests for traverse workflow pipeline."""

import math

import pytest
from typer.testing import CliRunner

from cogokit.cli import app
from cogokit.core import Angle, Point
from cogokit.core.job import Job
from cogokit.surveying.workflow import TraverseLeg, TraverseResult, TraverseWorkflow

runner = CliRunner()


class TestTraverseLeg:
    """Tests for TraverseLeg dataclass."""

    def test_create_leg(self):
        leg = TraverseLeg(
            occupied=1, backsight=4, foresight=2, angle_dms=90.0000, distance=100.0
        )
        assert leg.occupied == 1
        assert leg.backsight == 4
        assert leg.foresight == 2
        assert leg.angle_dms == 90.0
        assert leg.distance == 100.0
        assert leg.hi == 0.0
        assert leg.ht == 0.0

    def test_create_leg_with_heights(self):
        leg = TraverseLeg(
            occupied=1, backsight=4, foresight=2,
            angle_dms=90.0000, distance=100.0, hi=1.5, ht=1.7,
        )
        assert leg.hi == 1.5
        assert leg.ht == 1.7


class TestTraverseWorkflowPerfectSquare:
    """Test with a perfect closed square traverse (counter-clockwise).

    P1 (1000, 5000) -> P2 (1100, 5000) -> P3 (1100, 4900) -> P4 (1000, 4900) -> P1
    All angles right = 90 degrees, all distances = 100.0
    Backsight at P1 is toward west (azimuth 270 degrees)
    """

    def setup_method(self):
        self.start = Point(northing=1000.0, easting=5000.0, elevation=100.0, number=1)
        self.wf = TraverseWorkflow(
            start_point=self.start,
            start_azimuth=270.0,  # HP notation: 270d00'00"
            close_to_start=True,
        )
        # Leg 1: P1->P2 (north)
        self.wf.add_leg(occupied=1, backsight=0, foresight=2, angle_dms=90.0, distance=100.0)
        # Leg 2: P2->P3 (west)
        self.wf.add_leg(occupied=2, backsight=1, foresight=3, angle_dms=90.0, distance=100.0)
        # Leg 3: P3->P4 (south)
        self.wf.add_leg(occupied=3, backsight=2, foresight=4, angle_dms=90.0, distance=100.0)
        # Leg 4: P4->P1 (east)
        self.wf.add_leg(occupied=4, backsight=3, foresight=1, angle_dms=90.0, distance=100.0)

    def test_zero_angular_misclosure(self):
        result = self.wf.run()
        assert abs(result.angular_misclosure.degrees) < 1e-6

    def test_zero_linear_misclosure(self):
        result = self.wf.run()
        assert result.linear_misclosure < 1e-6

    def test_infinite_precision(self):
        result = self.wf.run()
        assert result.precision_ratio == float("inf")

    def test_correct_perimeter(self):
        result = self.wf.run()
        assert result.perimeter == pytest.approx(400.0, abs=1e-6)

    def test_raw_points_count(self):
        result = self.wf.run()
        # start + 4 computed points (including closing back to start)
        assert len(result.raw_points) == 5

    def test_adjusted_points_count(self):
        result = self.wf.run()
        assert len(result.adjusted_points) == 5

    def test_intermediate_coordinates(self):
        result = self.wf.run()
        # P2 should be north of P1
        p2 = result.raw_points[1]
        assert p2.northing == pytest.approx(1100.0, abs=1e-3)
        assert p2.easting == pytest.approx(5000.0, abs=1e-3)
        # P3 should be northwest
        p3 = result.raw_points[2]
        assert p3.northing == pytest.approx(1100.0, abs=1e-3)
        assert p3.easting == pytest.approx(4900.0, abs=1e-3)
        # P4 should be west of P1
        p4 = result.raw_points[3]
        assert p4.northing == pytest.approx(1000.0, abs=1e-3)
        assert p4.easting == pytest.approx(4900.0, abs=1e-3)

    def test_adjusted_job(self):
        result = self.wf.run()
        assert isinstance(result.adjusted_job, Job)
        # Job should have 4 unique points (start + 3 intermediates; closing duplicate removed)
        assert result.adjusted_job.point_count == 4

    def test_closure_components(self):
        result = self.wf.run()
        assert abs(result.closure_north) < 1e-6
        assert abs(result.closure_east) < 1e-6


class TestTraverseWorkflowAngularError:
    """Test traverse with deliberate angular error."""

    def setup_method(self):
        self.start = Point(northing=1000.0, easting=5000.0, elevation=100.0, number=1)
        self.wf = TraverseWorkflow(
            start_point=self.start,
            start_azimuth=270.0,
            close_to_start=True,
        )
        # 10-second error on first angle: 90d00'10" = 90.0010 HP
        self.wf.add_leg(1, 0, 2, 90.001, 100.0)
        self.wf.add_leg(2, 1, 3, 90.0, 100.0)
        self.wf.add_leg(3, 2, 4, 90.0, 100.0)
        self.wf.add_leg(4, 3, 1, 90.0, 100.0)

    def test_nonzero_angular_misclosure(self):
        result = self.wf.run()
        # 10 seconds = 10/3600 degrees
        expected = 10.0 / 3600.0
        assert abs(result.angular_misclosure.degrees - expected) < 1e-4

    def test_angular_tolerance(self):
        result = self.wf.run()
        # Default tolerance is 10"*sqrt(n) = 10"*2 = 20"
        expected_tol_deg = (10.0 * math.sqrt(4)) / 3600.0
        assert abs(result.angular_tolerance.degrees - expected_tol_deg) < 1e-6

    def test_adjustment_still_closes(self):
        result = self.wf.run()
        # After compass rule, adjusted points should form a closed figure
        # (linear misclosure exists but is corrected)
        assert result.precision_ratio > 100  # should be good precision


class TestTraverseWorkflowLinearError:
    """Test traverse with correct angles but one leg distance off."""

    def setup_method(self):
        self.start = Point(northing=1000.0, easting=5000.0, elevation=100.0, number=1)
        self.wf = TraverseWorkflow(
            start_point=self.start,
            start_azimuth=270.0,
            close_to_start=True,
        )
        # Perfect angles, but leg 1 is 100.05 instead of 100.0
        self.wf.add_leg(1, 0, 2, 90.0, 100.05)
        self.wf.add_leg(2, 1, 3, 90.0, 100.0)
        self.wf.add_leg(3, 2, 4, 90.0, 100.0)
        self.wf.add_leg(4, 3, 1, 90.0, 100.0)

    def test_nonzero_linear_misclosure(self):
        result = self.wf.run()
        assert result.linear_misclosure > 0.01

    def test_finite_precision(self):
        result = self.wf.run()
        assert result.precision_ratio != float("inf")
        assert result.precision_ratio > 0

    def test_adjusted_points_differ_from_raw(self):
        result = self.wf.run()
        # At least one adjusted point should differ from raw
        for raw, adj in zip(result.raw_points[1:], result.adjusted_points[1:]):
            if abs(raw.northing - adj.northing) > 1e-9:
                return  # found a difference
            if abs(raw.easting - adj.easting) > 1e-9:
                return
        pytest.fail("Expected adjusted points to differ from raw points")


class TestTraverseWorkflowMatchesManualCompass:
    """Verify workflow result matches manual compass rule application."""

    def test_round_trip(self):
        start = Point(northing=1000.0, easting=5000.0, elevation=100.0, number=1)
        wf = TraverseWorkflow(
            start_point=start,
            start_azimuth=270.0,
            close_to_start=True,
        )
        wf.add_leg(1, 0, 2, 90.0, 100.05)
        wf.add_leg(2, 1, 3, 90.0, 100.0)
        wf.add_leg(3, 2, 4, 90.0, 100.0)
        wf.add_leg(4, 3, 1, 90.0, 100.0)

        result = wf.run()

        # Manually apply compass_rule to raw_points
        from cogokit.adjustments.compass_rule import compass_rule
        manual = compass_rule(result.raw_points, known_end=None)

        # Should match
        assert result.precision_ratio == pytest.approx(manual.precision_ratio)
        assert result.linear_misclosure == pytest.approx(manual.linear_misclosure)
        for wf_pt, manual_pt in zip(result.adjusted_points, manual.adjusted):
            assert wf_pt.northing == pytest.approx(manual_pt.northing, abs=1e-9)
            assert wf_pt.easting == pytest.approx(manual_pt.easting, abs=1e-9)


class TestTraverseWorkflowValidation:
    """Test error handling in TraverseWorkflow."""

    def test_no_legs_raises(self):
        start = Point(northing=0.0, easting=0.0, number=1)
        wf = TraverseWorkflow(start_point=start, start_azimuth=0.0)
        with pytest.raises(ValueError, match="No traverse legs"):
            wf.run()

    def test_no_azimuth_raises(self):
        start = Point(northing=0.0, easting=0.0, number=1)
        wf = TraverseWorkflow(start_point=start)
        wf.add_leg(1, 0, 2, 90.0, 100.0)
        with pytest.raises(ValueError, match="Start azimuth"):
            wf.run()


class TestTraverseRunCLI:
    """Test the traverse-run CLI command."""

    def test_basic_run(self, tmp_path):
        obs_file = tmp_path / "obs.csv"
        obs_file.write_text(
            "# Traverse observations\n"
            "1,0,2,90.0000,100.000,0.0,0.0\n"
            "2,1,3,90.0000,100.000,0.0,0.0\n"
            "3,2,4,90.0000,100.000,0.0,0.0\n"
            "4,3,1,90.0000,100.000,0.0,0.0\n"
        )
        result = runner.invoke(app, [
            "traverse-run",
            str(obs_file),
            "--start-point", "1 1000.000 5000.000 100.000",
            "--start-azimuth", "270.0",
        ])
        assert result.exit_code == 0
        assert "Angular Misclosure" in result.output
        assert "Precision Ratio" in result.output
        assert "Adjusted Coordinates" in result.output

    def test_missing_file(self):
        result = runner.invoke(app, [
            "traverse-run",
            "/nonexistent/file.csv",
            "--start-point", "1 1000 5000 100",
            "--start-azimuth", "0.0",
        ])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_bad_start_point(self, tmp_path):
        obs_file = tmp_path / "obs.csv"
        obs_file.write_text("1,0,2,90.0,100.0\n")
        result = runner.invoke(app, [
            "traverse-run",
            str(obs_file),
            "--start-point", "bad",
            "--start-azimuth", "0.0",
        ])
        assert result.exit_code == 1
