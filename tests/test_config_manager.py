"""Tests for core.config.ConfigManager."""
import json

from core.config import DEFAULT_CONFIG, ConfigManager


def test_default_config_when_no_file(tmp_path):
    cfg_file = tmp_path / "ide_config.json"
    cm = ConfigManager(str(cfg_file))
    assert cfg_file.exists() is False  # not created on load
    assert cm.get("theme") == "dark"
    assert cm.get("editor", "font_size") == 12


def test_load_partial_config_merges_with_defaults(tmp_path):
    cfg_file = tmp_path / "ide_config.json"
    cfg_file.write_text(json.dumps({"theme": "light"}))
    cm = ConfigManager(str(cfg_file))
    assert cm.get("theme") == "light"
    # Defaults should still be present
    assert cm.get("editor", "font_size") == 12
    assert cm.get("autocomplete", "enabled") is True


def test_load_invalid_json_does_not_crash(tmp_path):
    cfg_file = tmp_path / "ide_config.json"
    cfg_file.write_text("{not valid json")
    cm = ConfigManager(str(cfg_file))
    # Falls back to defaults
    assert cm.get("theme") == "dark"


def test_save_writes_valid_json(tmp_path):
    cfg_file = tmp_path / "ide_config.json"
    cm = ConfigManager(str(cfg_file))
    cm.set("monokai", "theme")
    cm.save()
    raw = cfg_file.read_text()
    data = json.loads(raw)
    assert data["theme"] == "monokai"


def test_get_returns_none_for_missing_path(tmp_path):
    cm = ConfigManager(str(tmp_path / "ide_config.json"))
    assert cm.get("nonexistent", "key") is None
    assert cm.get("editor", "nonexistent") is None


def test_set_creates_nested_keys(tmp_path):
    cm = ConfigManager(str(tmp_path / "ide_config.json"))
    cm.set("custom_value", "openai", "timeout")
    assert cm.get("openai", "timeout") == "custom_value"


def test_save_then_load_roundtrip(tmp_path):
    cfg_file = tmp_path / "ide_config.json"
    cm1 = ConfigManager(str(cfg_file))
    cm1.set("light", "theme")
    cm1.set(20, "editor", "font_size")
    cm1.save()

    cm2 = ConfigManager(str(cfg_file))
    assert cm2.get("theme") == "light"
    assert cm2.get("editor", "font_size") == 20


def test_merge_preserves_nested_defaults(tmp_path):
    """Loading a config with partial editor block should not erase other editor keys."""
    cfg_file = tmp_path / "ide_config.json"
    cfg_file.write_text(
        json.dumps({"editor": {"font_family": "Fira Code"}})
    )
    cm = ConfigManager(str(cfg_file))
    assert cm.get("editor", "font_family") == "Fira Code"
    # Other editor defaults are preserved
    assert cm.get("editor", "font_size") == 12
    assert cm.get("editor", "show_line_numbers") is True


def test_default_config_has_expected_keys():
    """Sanity check on the DEFAULT_CONFIG shape."""
    expected_top_keys = {
        "theme", "current_language", "editor", "autocomplete",
        "intelicode", "python", "venv", "languages",
        "workspace", "recent_folders", "window", "openai",
    }
    assert expected_top_keys.issubset(set(DEFAULT_CONFIG.keys()))
