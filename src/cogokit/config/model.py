"""Configuration data model with layered defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnitsConfig:
    """Default measurement units."""

    linear: str = "foot"  # meter, foot, us_survey_foot
    angular: str = "dms"  # degrees, radians, dms, gradians


@dataclass
class DisplayConfig:
    """TUI display and layout preferences."""

    default_layout: str = "side-by-side"  # side-by-side, stacked, overlay
    show_graph: bool = True
    label_mode: int = 0  # 0=numbers, 1=numbers+desc, 2=none
    theme: str = "dark"  # dark, light, system


@dataclass
class PathsConfig:
    """Default file paths."""

    import_dir: str = "."
    export_dir: str = "."


@dataclass
class EnvironmentConfig:
    """Environment and formatting preferences."""

    decimal_precision: int = 4
    coordinate_format: str = "ne"  # "ne" or "en"
    default_crs: str = ""


@dataclass
class Config:
    """Application configuration with dotted-key access.

    Supports layered loading: hardcoded defaults → global file → project-local file.
    """

    units: UnitsConfig = field(default_factory=UnitsConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    keybindings: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create a Config from a (possibly partial) dict, filling defaults."""
        units_data = data.get("units", {})
        display_data = data.get("display", {})
        paths_data = data.get("paths", {})
        environment_data = data.get("environment", {})
        keybindings_data = data.get("keybindings", {})

        return cls(
            units=UnitsConfig(**{k: v for k, v in units_data.items() if k in UnitsConfig.__dataclass_fields__}),
            display=DisplayConfig(**{k: v for k, v in display_data.items() if k in DisplayConfig.__dataclass_fields__}),
            paths=PathsConfig(**{k: v for k, v in paths_data.items() if k in PathsConfig.__dataclass_fields__}),
            environment=EnvironmentConfig(**{k: v for k, v in environment_data.items() if k in EnvironmentConfig.__dataclass_fields__}),
            keybindings=dict(keybindings_data),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for TOML output."""
        return {
            "units": {
                "linear": self.units.linear,
                "angular": self.units.angular,
            },
            "display": {
                "default_layout": self.display.default_layout,
                "show_graph": self.display.show_graph,
                "label_mode": self.display.label_mode,
                "theme": self.display.theme,
            },
            "paths": {
                "import_dir": self.paths.import_dir,
                "export_dir": self.paths.export_dir,
            },
            "environment": {
                "decimal_precision": self.environment.decimal_precision,
                "coordinate_format": self.environment.coordinate_format,
                "default_crs": self.environment.default_crs,
            },
            "keybindings": dict(self.keybindings),
        }

    def get(self, dotted_key: str) -> Any:
        """Get a value by dotted key, e.g. 'units.linear'."""
        parts = dotted_key.split(".", 1)
        if len(parts) == 1:
            section = parts[0]
            if section == "keybindings":
                return dict(self.keybindings)
            obj = getattr(self, section, None)
            if obj is None:
                raise KeyError(f"Unknown config section: {section}")
            return obj
        section, key = parts
        if section == "keybindings":
            if key in self.keybindings:
                return self.keybindings[key]
            raise KeyError(f"Unknown keybinding: {key}")
        obj = getattr(self, section, None)
        if obj is None:
            raise KeyError(f"Unknown config section: {section}")
        if not hasattr(obj, key):
            raise KeyError(f"Unknown config key: {dotted_key}")
        return getattr(obj, key)

    def set(self, dotted_key: str, value: str) -> None:
        """Set a value by dotted key, coercing types from string input."""
        parts = dotted_key.split(".", 1)
        if len(parts) != 2:
            raise KeyError(f"Expected section.key format, got: {dotted_key}")
        section, key = parts

        if section == "keybindings":
            self.keybindings[key] = value
            return

        obj = getattr(self, section, None)
        if obj is None:
            raise KeyError(f"Unknown config section: {section}")
        if not hasattr(obj, key):
            raise KeyError(f"Unknown config key: {dotted_key}")

        # Coerce string value to the field's type
        current = getattr(obj, key)
        if isinstance(current, bool):
            coerced = value.lower() in ("true", "1", "yes", "on")
        elif isinstance(current, int):
            coerced = int(value)
        elif isinstance(current, float):
            coerced = float(value)
        else:
            coerced = value

        object.__setattr__(obj, key, coerced)
