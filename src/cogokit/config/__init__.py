"""Application configuration: layered TOML config, keybinding registry."""

from .keybindings import (
    ACTION_DESCRIPTIONS,
    DEFAULT_BINDINGS,
    KeybindingRegistry,
)
from .loader import (
    get_config,
    get_registry,
    load_config,
    reload_config,
    reset_config_cache,
    save_config,
)
from .model import Config, DisplayConfig, EnvironmentConfig, PathsConfig, UnitsConfig
from .writer import dumps, write_toml

__all__ = [
    "ACTION_DESCRIPTIONS",
    "Config",
    "DEFAULT_BINDINGS",
    "DisplayConfig",
    "EnvironmentConfig",
    "KeybindingRegistry",
    "PathsConfig",
    "UnitsConfig",
    "dumps",
    "get_config",
    "get_registry",
    "load_config",
    "reload_config",
    "reset_config_cache",
    "save_config",
    "write_toml",
]
