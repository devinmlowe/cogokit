"""Read/write delimited ASCII point files."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import List, Optional, TextIO, Union

from ..core.job import Job
from ..core.point import Point


class Delimiter(Enum):
    SPACE = " "
    TAB = "\t"
    COMMA = ","


def read_points(source: Union[str, Path, TextIO], delimiter: Optional[Delimiter] = None) -> Job:
    """Read points from a delimited text file into a Job.

    Format per line: PointNum Northing Easting Elevation [Description]

    If delimiter is None, auto-detects: tries comma, then tab, then splits on
    whitespace (space-delimited, the original COGO+ format).
    """
    job = Job()

    if isinstance(source, (str, Path)):
        path = Path(source)
        job.name = path.stem
        with open(path, "r") as f:
            lines = f.readlines()
    else:
        lines = source.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = _split_line(line, delimiter)
        if len(parts) < 4:
            continue

        try:
            number = int(parts[0])
            northing = float(parts[1])
            easting = float(parts[2])
            elevation = float(parts[3])
            description = parts[4] if len(parts) > 4 else ""
        except (ValueError, IndexError):
            continue

        job.add_point(Point(
            number=number,
            northing=northing,
            easting=easting,
            elevation=elevation,
            description=description,
        ))

    return job


def write_points(
    job: Job,
    destination: Union[str, Path, TextIO],
    delimiter: Delimiter = Delimiter.SPACE,
    precision: int = 4,
) -> None:
    """Write job points to a delimited text file.

    Format per line: PointNum Northing Easting Elevation Description
    """
    sep = delimiter.value

    def format_line(p: Point) -> str:
        parts = [
            str(p.number),
            f"{p.northing:.{precision}f}",
            f"{p.easting:.{precision}f}",
            f"{p.elevation:.{precision}f}",
        ]
        if p.description:
            parts.append(p.description)
        return sep.join(parts)

    text = "\n".join(format_line(p) for p in job.points()) + "\n"

    if isinstance(destination, (str, Path)):
        with open(destination, "w") as f:
            f.write(text)
    else:
        destination.write(text)


def _split_line(line: str, delimiter: Optional[Delimiter]) -> List[str]:
    """Split a line using the specified or auto-detected delimiter."""
    if delimiter is not None:
        return [p.strip() for p in line.split(delimiter.value)]

    # Auto-detect: comma > tab > whitespace
    if "," in line:
        return [p.strip() for p in line.split(",")]
    if "\t" in line:
        return [p.strip() for p in line.split("\t")]
    return line.split()
