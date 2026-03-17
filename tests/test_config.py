"""Tests for configuration system: model, loader, writer."""

import tomllib

import pytest

from cogokit.config.loader import (
    _deep_merge,
    load_config,
    reset_config_cache,
    save_config,
)
from cogokit.config.model import Config
from cogokit.config.writer import dumps


class TestConfigModel:
    """Test Config dataclass construction and access."""

    def test_defaults(self):
        cfg = Config()
        assert cfg.units.linear == "foot"
        assert cfg.units.angular == "dms"
        assert cfg.display.default_layout == "side-by-side"
        assert cfg.display.show_graph is True
        assert cfg.display.label_mode == 0
        assert cfg.display.theme == "dark"
        assert cfg.paths.import_dir == "."
        assert cfg.paths.export_dir == "."
        assert cfg.keybindings == {}

    def test_from_dict_empty(self):
        cfg = Config.from_dict({})
        assert cfg.units.linear == "foot"

    def test_from_dict_partial(self):
        cfg = Config.from_dict({"units": {"linear": "meter"}})
        assert cfg.units.linear == "meter"
        assert cfg.units.angular == "dms"  # default preserved

    def test_from_dict_full(self):
        data = {
            "units": {"linear": "meter", "angular": "gradians"},
            "display": {"default_layout": "stacked", "show_graph": False, "label_mode": 2, "theme": "light"},
            "paths": {"import_dir": "/data", "export_dir": "/out"},
            "keybindings": {"quit": "ctrl+q"},
        }
        cfg = Config.from_dict(data)
        assert cfg.units.linear == "meter"
        assert cfg.display.theme == "light"
        assert cfg.paths.import_dir == "/data"
        assert cfg.keybindings["quit"] == "ctrl+q"

    def test_from_dict_ignores_unknown_keys(self):
        cfg = Config.from_dict({"units": {"linear": "meter", "unknown_key": "val"}})
        assert cfg.units.linear == "meter"

    def test_to_dict_roundtrip(self):
        cfg = Config()
        d = cfg.to_dict()
        cfg2 = Config.from_dict(d)
        assert cfg2.to_dict() == d

    def test_get_dotted(self):
        cfg = Config()
        assert cfg.get("units.linear") == "foot"
        assert cfg.get("display.theme") == "dark"
        assert cfg.get("paths.export_dir") == "."

    def test_get_section(self):
        cfg = Config()
        obj = cfg.get("units")
        assert obj.linear == "foot"

    def test_get_keybindings(self):
        cfg = Config.from_dict({"keybindings": {"quit": "ctrl+q"}})
        assert cfg.get("keybindings.quit") == "ctrl+q"
        assert cfg.get("keybindings") == {"quit": "ctrl+q"}

    def test_get_unknown_raises(self):
        cfg = Config()
        with pytest.raises(KeyError):
            cfg.get("nonexistent.key")
        with pytest.raises(KeyError):
            cfg.get("units.nonexistent")

    def test_set_string(self):
        cfg = Config()
        cfg.set("units.linear", "meter")
        assert cfg.units.linear == "meter"

    def test_set_bool(self):
        cfg = Config()
        cfg.set("display.show_graph", "false")
        assert cfg.display.show_graph is False
        cfg.set("display.show_graph", "true")
        assert cfg.display.show_graph is True

    def test_set_int(self):
        cfg = Config()
        cfg.set("display.label_mode", "2")
        assert cfg.display.label_mode == 2

    def test_set_keybinding(self):
        cfg = Config()
        cfg.set("keybindings.custom_action", "ctrl+x")
        assert cfg.keybindings["custom_action"] == "ctrl+x"

    def test_set_unknown_raises(self):
        cfg = Config()
        with pytest.raises(KeyError):
            cfg.set("units", "invalid")  # no dot
        with pytest.raises(KeyError):
            cfg.set("bad_section.key", "val")


class TestDeepMerge:
    """Test dict deep merge."""

    def test_simple_override(self):
        assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self):
        base = {"units": {"linear": "foot", "angular": "dms"}}
        override = {"units": {"linear": "meter"}}
        result = _deep_merge(base, override)
        assert result == {"units": {"linear": "meter", "angular": "dms"}}

    def test_add_new_key(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_base_unchanged(self):
        base = {"a": 1}
        _deep_merge(base, {"a": 2})
        assert base == {"a": 1}  # original not mutated


class TestTomlWriter:
    """Test TOML serialization."""

    def test_string(self):
        assert dumps({"key": "value"}) == 'key = "value"\n'

    def test_int(self):
        assert dumps({"n": 42}) == "n = 42\n"

    def test_bool(self):
        assert dumps({"flag": True}) == "flag = true\n"
        assert dumps({"flag": False}) == "flag = false\n"

    def test_table(self):
        result = dumps({"section": {"key": "val"}})
        assert "[section]" in result
        assert 'key = "val"' in result

    def test_roundtrip_with_tomllib(self):
        cfg = Config()
        toml_str = dumps(cfg.to_dict())
        parsed = tomllib.loads(toml_str)
        cfg2 = Config.from_dict(parsed)
        assert cfg2.to_dict() == cfg.to_dict()

    def test_write_file(self, tmp_path):
        from cogokit.config.writer import write_toml

        path = tmp_path / "test.toml"
        write_toml({"key": "value"}, path)
        assert path.read_text() == 'key = "value"\n'

    def test_write_creates_parents(self, tmp_path):
        from cogokit.config.writer import write_toml

        path = tmp_path / "sub" / "dir" / "test.toml"
        write_toml({"key": "val"}, path)
        assert path.exists()


class TestConfigLoader:
    """Test config loading and layered merging."""

    def setup_method(self):
        reset_config_cache()

    def test_load_no_files(self, tmp_path):
        cfg = load_config(
            global_path=tmp_path / "global.toml",
            project_path=tmp_path / "project.toml",
        )
        assert cfg.units.linear == "foot"  # defaults

    def test_load_global_only(self, tmp_path):
        global_file = tmp_path / "global.toml"
        global_file.write_text('[units]\nlinear = "meter"\n')
        cfg = load_config(
            global_path=global_file,
            project_path=tmp_path / "project.toml",
        )
        assert cfg.units.linear == "meter"
        assert cfg.units.angular == "dms"  # default preserved

    def test_load_project_overrides_global(self, tmp_path):
        global_file = tmp_path / "global.toml"
        global_file.write_text('[units]\nlinear = "meter"\n')
        project_file = tmp_path / "project.toml"
        project_file.write_text('[units]\nlinear = "us_survey_foot"\n')
        cfg = load_config(global_path=global_file, project_path=project_file)
        assert cfg.units.linear == "us_survey_foot"

    def test_keybinding_overrides(self, tmp_path):
        project_file = tmp_path / "project.toml"
        project_file.write_text('[keybindings]\ncycle_layout = "ctrl+k"\n')
        cfg = load_config(
            global_path=tmp_path / "global.toml",
            project_path=project_file,
        )
        assert cfg.keybindings.get("cycle_layout") == "ctrl+k"

    def test_save_and_reload(self, tmp_path):
        cfg = Config()
        cfg.set("units.linear", "meter")
        path = tmp_path / "saved.toml"
        save_config(cfg, path=path)

        reset_config_cache()
        cfg2 = load_config(global_path=path, project_path=tmp_path / "none.toml")
        assert cfg2.units.linear == "meter"
