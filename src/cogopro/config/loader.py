"""Config loading, merging, and persistence."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .keybindings import DEFAULT_BINDINGS, KeybindingRegistry
from .model import Config
from .writer import write_toml

GLOBAL_CONFIG_PATH = Path.home() / ".config" / "cogopro" / "config.toml"
PROJECT_CONFIG_PATH = Path(".cogopro.toml")

_config: Config | None = None
_registry: KeybindingRegistry | None = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base. Override values win."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file, returning empty dict if it doesn't exist."""
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_config(
    global_path: Path | None = None,
    project_path: Path | None = None,
) -> Config:
    """Load and merge config from global and project-local files.

    Layer order (last wins): defaults → global → project-local.
    """
    global _config, _registry

    global_path = global_path or GLOBAL_CONFIG_PATH
    project_path = project_path or PROJECT_CONFIG_PATH

    # Start with empty (Config defaults will fill in)
    merged: dict[str, Any] = {}

    # Layer global config
    global_data = _read_toml(global_path)
    if global_data:
        merged = _deep_merge(merged, global_data)

    # Layer project-local config
    project_data = _read_toml(project_path)
    if project_data:
        merged = _deep_merge(merged, project_data)

    _config = Config.from_dict(merged)

    # Build keybinding registry: defaults + user overrides from config
    _registry = KeybindingRegistry(
        defaults=DEFAULT_BINDINGS,
        user_overrides=_config.keybindings,
    )

    return _config


def get_config() -> Config:
    """Get the cached config, loading lazily if needed."""
    global _config
    if _config is None:
        load_config()
    return _config  # type: ignore[return-value]


def get_registry() -> KeybindingRegistry:
    """Get the cached keybinding registry, loading config lazily if needed."""
    global _registry
    if _registry is None:
        load_config()
    return _registry  # type: ignore[return-value]


def reload_config() -> Config:
    """Force a config re-read from disk."""
    global _config, _registry
    _config = None
    _registry = None
    return load_config()


def save_config(config: Config, global_: bool = False, path: Path | None = None) -> Path:
    """Write config to a TOML file.

    Args:
        config: The config to save.
        global_: If True, write to global config path. Otherwise project-local.
        path: Explicit path override (used by tests).

    Returns:
        The path written to.
    """
    if path is None:
        path = GLOBAL_CONFIG_PATH if global_ else PROJECT_CONFIG_PATH
    write_toml(config.to_dict(), path)
    return path


def reset_config_cache() -> None:
    """Clear the cached config and registry (for testing)."""
    global _config, _registry
    _config = None
    _registry = None
