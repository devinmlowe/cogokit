"""Flexible CSV import/export for survey points."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, TextIO, Union

from ..core.job import Job
from ..core.point import Point

# Canonical column names and their common aliases
_ALIASES: Dict[str, str] = {
    # number
    "number": "number",
    "pt": "number",
    "point": "number",
    "point_number": "number",
    "pointnumber": "number",
    "id": "number",
    # northing
    "northing": "northing",
    "north": "northing",
    "n": "northing",
    "y": "northing",
    # easting
    "easting": "easting",
    "east": "easting",
    "e": "easting",
    "x": "easting",
    # elevation
    "elevation": "elevation",
    "elev": "elevation",
    "z": "elevation",
    "height": "elevation",
    # description
    "description": "description",
    "desc": "description",
    "comment": "description",
}

_DEFAULT_COLUMNS = ["number", "northing", "easting", "elevation", "description"]

_FIELD_GETTERS = {
    "number": lambda p, prec: str(p.number),
    "northing": lambda p, prec: f"{p.northing:.{prec}f}",
    "easting": lambda p, prec: f"{p.easting:.{prec}f}",
    "elevation": lambda p, prec: f"{p.elevation:.{prec}f}",
    "description": lambda p, prec: p.description,
}


def _resolve_column(name: str) -> str:
    """Map a column name (or alias) to a canonical column name."""
    return _ALIASES.get(name.lower().strip(), name.lower().strip())


def read_csv(
    source: Union[str, Path, TextIO],
    columns: Optional[List[str]] = None,
    has_header: bool = True,
) -> Job:
    """Read points from a CSV file into a Job.

    Parameters:
        source: File path or file-like object.
        columns: Explicit column order. If None and has_header is True,
            columns are auto-detected from the header row using alias matching.
        has_header: Whether the first row is a header. Ignored if columns is provided
            and the first row does not match known column names.
    """
    job = Job()

    if isinstance(source, (str, Path)):
        path = Path(source)
        job.name = path.stem
        f: TextIO = open(path, "r", newline="")
        should_close = True
    else:
        f = source
        should_close = False

    try:
        reader = csv.reader(f)

        if columns is not None:
            col_map = [_resolve_column(c) for c in columns]
            if has_header:
                # Skip header row if present
                try:
                    next(reader)
                except StopIteration:
                    return job
        elif has_header:
            try:
                header = next(reader)
            except StopIteration:
                return job
            col_map = [_resolve_column(h) for h in header]
        else:
            col_map = [_resolve_column(c) for c in _DEFAULT_COLUMNS]

        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            point = _row_to_point(row, col_map)
            if point is not None:
                job.add_point(point)
    finally:
        if should_close:
            f.close()

    return job


def write_csv(
    job: Job,
    destination: Union[str, Path, TextIO],
    columns: Optional[List[str]] = None,
    precision: int = 4,
) -> None:
    """Write job points to a CSV file.

    Parameters:
        job: Job containing points to export.
        destination: Output file path or file-like object.
        columns: Column order. Defaults to number, northing, easting, elevation, description.
        precision: Decimal places for coordinate values.
    """
    cols = columns if columns is not None else _DEFAULT_COLUMNS

    if isinstance(destination, (str, Path)):
        f: TextIO = open(destination, "w", newline="")
        should_close = True
    else:
        f = destination
        should_close = False

    try:
        writer = csv.writer(f)
        writer.writerow(cols)
        for p in job.points():
            row = [_FIELD_GETTERS.get(c, lambda p, pr: "")(p, precision) for c in cols]
            writer.writerow(row)
    finally:
        if should_close:
            f.close()


def _row_to_point(row: List[str], col_map: List[str]) -> Optional[Point]:
    """Convert a CSV row to a Point using the column mapping."""
    data: Dict[str, str] = {}
    for i, col_name in enumerate(col_map):
        if i < len(row):
            data[col_name] = row[i].strip()

    try:
        number = int(data.get("number", ""))
    except (ValueError, TypeError):
        return None

    try:
        northing = float(data.get("northing", ""))
        easting = float(data.get("easting", ""))
    except (ValueError, TypeError):
        return None

    try:
        elevation = float(data.get("elevation", "0"))
    except (ValueError, TypeError):
        elevation = 0.0

    description = data.get("description", "")

    return Point(
        northing=northing,
        easting=easting,
        elevation=elevation,
        number=number,
        description=description,
    )
