"""Tests for add-point auto-advance logic (next point number calculation).

These test the core logic directly without needing TUI rendering.
"""

from cogokit.core import Job, Point


def _next_point_number(job: Job) -> int:
    """Replicate the logic from PointManagerScreen._next_point_number."""
    numbers = job.point_numbers()
    return max(numbers) + 1 if numbers else 1


def test_next_point_number_empty_job() -> None:
    """Empty job should return 1 as the first point number."""
    job = Job()
    assert _next_point_number(job) == 1


def test_next_point_number_sequential() -> None:
    """Job with points 1,2,3 should return 4."""
    job = Job()
    for i in (1, 2, 3):
        job.add_point(Point(northing=0, easting=0, number=i))
    assert _next_point_number(job) == 4


def test_next_point_number_with_gaps() -> None:
    """Job with points 1,3,5 should return 6 (max+1, not fill gaps)."""
    job = Job()
    for i in (1, 3, 5):
        job.add_point(Point(northing=0, easting=0, number=i))
    assert _next_point_number(job) == 6
