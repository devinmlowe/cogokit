"""Tests for graph view-model construction."""

from cogopro.core.job import Job
from cogopro.core.point import Point
from cogopro.tui.viewmodels.graph_vm import build_graph_vm


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
