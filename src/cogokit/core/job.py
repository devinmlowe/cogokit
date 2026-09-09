"""Job/project container for surveying data, backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Iterable, Iterator, List, Optional

from .linestring import LineString
from .point import Point
from .units import AngularUnit, LinearUnit

if TYPE_CHECKING:
    from .crs import CRS

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS points (
    number      INTEGER PRIMARY KEY,
    northing    REAL NOT NULL,
    easting     REAL NOT NULL,
    elevation   REAL NOT NULL DEFAULT 0.0,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS linestrings (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    point_numbers TEXT NOT NULL,
    closed        BOOLEAN NOT NULL DEFAULT 0
);
"""


class Job:
    """A surveying job/project that holds a collection of points and metadata.

    Points are stored in an SQLite database (in-memory by default).
    Metadata (name, description, units, crs) is kept in-memory only.
    """

    def __init__(
        self,
        name: str = "Untitled",
        description: str = "",
        linear_unit: LinearUnit = LinearUnit.FOOT,
        angular_unit: AngularUnit = AngularUnit.DMS,
        crs: "CRS | None" = None,
        *,
        db_path: str = ":memory:",
    ) -> None:
        self.name = name
        self.description = description
        self.linear_unit = linear_unit
        self.angular_unit = angular_unit
        self.crs = crs
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    # ---- Point operations ----

    def add_point(self, point: Point) -> None:
        """Add or update a point in the job."""
        self._conn.execute(
            "INSERT OR REPLACE INTO points VALUES (?, ?, ?, ?, ?)",
            (point.number, point.northing, point.easting,
             point.elevation, point.description),
        )
        self._conn.commit()

    def add_points(self, points: Iterable[Point]) -> None:
        """Add or update multiple points in a single transaction."""
        self._conn.executemany(
            "INSERT OR REPLACE INTO points VALUES (?, ?, ?, ?, ?)",
            [
                (p.number, p.northing, p.easting, p.elevation, p.description)
                for p in points
            ],
        )
        self._conn.commit()

    def get_point(self, number: int) -> Optional[Point]:
        """Retrieve a point by number, or None if not found."""
        row = self._conn.execute(
            "SELECT number, northing, easting, elevation, description "
            "FROM points WHERE number = ?",
            (number,),
        ).fetchone()
        if row is None:
            return None
        return Point(
            northing=row[1], easting=row[2], elevation=row[3],
            number=row[0], description=row[4],
        )

    def remove_point(self, number: int) -> Optional[Point]:
        """Remove and return a point by number, or None if not found."""
        point = self.get_point(number)
        if point is not None:
            self._conn.execute("DELETE FROM points WHERE number = ?", (number,))
            self._conn.commit()
        return point

    def has_point(self, number: int) -> bool:
        """Return True if a point with the given number exists."""
        row = self._conn.execute(
            "SELECT 1 FROM points WHERE number = ?", (number,),
        ).fetchone()
        return row is not None

    def points(self) -> List[Point]:
        """Return all points sorted by point number."""
        rows = self._conn.execute(
            "SELECT number, northing, easting, elevation, description "
            "FROM points ORDER BY number",
        ).fetchall()
        return [
            Point(
                northing=r[1], easting=r[2], elevation=r[3],
                number=r[0], description=r[4],
            )
            for r in rows
        ]

    def point_numbers(self) -> List[int]:
        """Return sorted list of all point numbers."""
        rows = self._conn.execute(
            "SELECT number FROM points ORDER BY number",
        ).fetchall()
        return [r[0] for r in rows]

    @property
    def point_count(self) -> int:
        """Return the number of points in the job."""
        row = self._conn.execute("SELECT COUNT(*) FROM points").fetchone()
        return row[0]

    # ---- LineString operations ----

    def add_linestring(self, ls: LineString) -> None:
        """Add or update a linestring in the job."""
        self._conn.execute(
            "INSERT OR REPLACE INTO linestrings (name, point_numbers, closed) "
            "VALUES (?, ?, ?)",
            (ls.name, json.dumps(list(ls.point_numbers)), ls.closed),
        )
        self._conn.commit()

    def get_linestring(self, name: str) -> Optional[LineString]:
        """Retrieve a linestring by name, or None if not found."""
        row = self._conn.execute(
            "SELECT name, point_numbers, closed FROM linestrings WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return LineString(
            name=row[0],
            point_numbers=tuple(json.loads(row[1])),
            closed=bool(row[2]),
        )

    def remove_linestring(self, name: str) -> bool:
        """Remove a linestring by name. Return True if it existed."""
        cursor = self._conn.execute(
            "DELETE FROM linestrings WHERE name = ?", (name,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def has_linestring(self, name: str) -> bool:
        """Return True if a linestring with the given name exists."""
        row = self._conn.execute(
            "SELECT 1 FROM linestrings WHERE name = ?", (name,),
        ).fetchone()
        return row is not None

    def linestrings(self) -> List[LineString]:
        """Return all linestrings sorted by name."""
        rows = self._conn.execute(
            "SELECT name, point_numbers, closed FROM linestrings ORDER BY name",
        ).fetchall()
        return [
            LineString(
                name=r[0],
                point_numbers=tuple(json.loads(r[1])),
                closed=bool(r[2]),
            )
            for r in rows
        ]

    @property
    def linestring_count(self) -> int:
        """Return the number of linestrings in the job."""
        row = self._conn.execute("SELECT COUNT(*) FROM linestrings").fetchone()
        return row[0]

    # ---- Dunder methods ----

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points())

    def __len__(self) -> int:
        return self.point_count

    def __contains__(self, number: int) -> bool:
        return self.has_point(number)

    def __repr__(self) -> str:
        return f"Job('{self.name}', {self.point_count} points)"

    # ---- Lifecycle ----

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "Job":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
