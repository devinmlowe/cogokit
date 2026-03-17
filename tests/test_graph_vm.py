"""Tests for graph view-model construction."""

from cogokit.core.job import Job
from cogokit.core.linestring import LineString
from cogokit.core.point import Point
from cogokit.tui.viewmodels.graph_vm import build_graph_vm


class TestBuildGraphVM:
    """Test build_graph_vm maps domain objects correctly."""

    def _make_job_with_points(self) -> Job:
        job = Job(name="Test")
        job.add_point(Point(northing=100.0, easting=200.0, number=1, description="HUB"))
        job.add_point(Point(northing=300.0, easting=400.0, number=2, description="IP"))
        job.add_point(Point(northing=500.0, easting=600.0, number=3))
        return job

    def test_coordinate_mapping(self):
        """Easting maps to x, northing maps to y."""
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        pt1 = vm.points[0]
        assert pt1.x == 200.0  # easting
        assert pt1.y == 100.0  # northing

    def test_point_count(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert len(vm.points) == 3

    def test_labels(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert vm.points[0].label == "1"
        assert vm.points[1].label == "2"

    def test_descriptions(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert vm.points[0].description == "HUB"
        assert vm.points[2].description == ""

    def test_no_selection(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert all(not p.selected for p in vm.points)

    def test_selection(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job, selected_numbers={2})
        assert not vm.points[0].selected
        assert vm.points[1].selected
        assert not vm.points[2].selected

    def test_multiple_selection(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job, selected_numbers={1, 3})
        selected = [p for p in vm.points if p.selected]
        assert len(selected) == 2

    def test_empty_job(self):
        job = Job(name="Empty")
        vm = build_graph_vm(job)
        assert len(vm.points) == 0
        assert len(vm.lines) == 0

    def test_point_number_preserved(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert vm.points[0].point_number == 1
        assert vm.points[1].point_number == 2

    def test_lines_empty_by_default(self):
        job = self._make_job_with_points()
        vm = build_graph_vm(job)
        assert vm.lines == []


class TestGraphVMLineStrings:
    """Test linestring resolution in build_graph_vm."""

    def _make_triangle_job(self) -> Job:
        job = Job()
        job.add_point(Point(northing=0.0, easting=0.0, number=1))
        job.add_point(Point(northing=100.0, easting=0.0, number=2))
        job.add_point(Point(northing=100.0, easting=100.0, number=3))
        return job

    def test_linestring_resolution(self):
        job = self._make_triangle_job()
        job.add_linestring(LineString(name="line", point_numbers=(1, 2, 3)))
        vm = build_graph_vm(job)
        assert len(vm.lines) == 1
        line = vm.lines[0]
        assert line.xs == [0.0, 0.0, 100.0]
        assert line.ys == [0.0, 100.0, 100.0]
        assert line.label == "line"

    def test_linestring_closed_loop(self):
        job = self._make_triangle_job()
        job.add_linestring(LineString(name="parcel", point_numbers=(1, 2, 3), closed=True))
        vm = build_graph_vm(job)
        assert len(vm.lines) == 1
        line = vm.lines[0]
        # Closed loop appends first point at end
        assert line.xs == [0.0, 0.0, 100.0, 0.0]
        assert line.ys == [0.0, 100.0, 100.0, 0.0]

    def test_linestring_missing_points(self):
        job = self._make_triangle_job()
        # Point 99 does not exist — should be skipped
        job.add_linestring(LineString(name="partial", point_numbers=(1, 99, 3)))
        vm = build_graph_vm(job)
        assert len(vm.lines) == 1
        line = vm.lines[0]
        assert line.xs == [0.0, 100.0]
        assert line.ys == [0.0, 100.0]

    def test_linestring_all_missing_points(self):
        job = Job()
        job.add_linestring(LineString(name="empty", point_numbers=(99, 100)))
        vm = build_graph_vm(job)
        # Fewer than 2 resolved points — line omitted
        assert len(vm.lines) == 0

    def test_multiple_linestrings(self):
        job = self._make_triangle_job()
        job.add_linestring(LineString(name="a", point_numbers=(1, 2)))
        job.add_linestring(LineString(name="b", point_numbers=(2, 3)))
        vm = build_graph_vm(job)
        assert len(vm.lines) == 2
