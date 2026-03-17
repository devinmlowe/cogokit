"""Simple TOML serializer for config output.

Handles the shapes produced by Config.to_dict(): top-level scalar keys
and one-level [table] sections containing scalars.  No arrays-of-tables,
inline tables, or multi-line strings needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _format_value(value: Any) -> str:
    """Format a single TOML value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")


def dumps(data: dict[str, Any]) -> str:
    """Serialize a dict to a TOML string."""
    lines: list[str] = []

    # Top-level scalar keys first
    for key, value in data.items():
        if not isinstance(value, dict):
            lines.append(f"{key} = {_format_value(value)}")

    # Then [table] sections
    for key, value in data.items():
        if isinstance(value, dict):
            if lines:
                lines.append("")
            lines.append(f"[{key}]")
            for sub_key, sub_value in value.items():
                lines.append(f"{sub_key} = {_format_value(sub_value)}")

    lines.append("")  # trailing newline
    return "\n".join(lines)


def write_toml(data: dict[str, Any], path: Path) -> None:
    """Write a dict to a TOML file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(data), encoding="utf-8")
