"""Job/project container for surveying data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional

from .point import Point
from .units import AngularUnit, LinearUnit

if TYPE_CHECKING:
    from .crs import CRS


@dataclass
class Job:
    """A surveying job/project that holds a collection of points and metadata."""

    name: str = "Untitled"
    description: str = ""
    linear_unit: LinearUnit = LinearUnit.FOOT
    angular_unit: AngularUnit = AngularUnit.DMS
    crs: CRS | None = None
    _points: Dict[int, Point] = field(default_factory=dict, repr=False)

    @property
    def point_count(self) -> int:
        return len(self._points)

    def add_point(self, point: Point) -> None:
        """Add or update a point in the job."""
        self._points[point.number] = point

    def get_point(self, number: int) -> Optional[Point]:
        """Retrieve a point by number, or None if not found."""
        return self._points.get(number)

    def remove_point(self, number: int) -> Optional[Point]:
        """Remove and return a point by number, or None if not found."""
        return self._points.pop(number, None)

    def has_point(self, number: int) -> bool:
        return number in self._points

    def points(self) -> List[Point]:
        """Return all points sorted by point number."""
        return sorted(self._points.values(), key=lambda p: p.number)

    def point_numbers(self) -> List[int]:
        """Return sorted list of all point numbers."""
        return sorted(self._points.keys())

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points())

    def __len__(self) -> int:
        return self.point_count

    def __contains__(self, number: int) -> bool:
        return self.has_point(number)

    def __repr__(self) -> str:
        return f"Job('{self.name}', {self.point_count} points)"
