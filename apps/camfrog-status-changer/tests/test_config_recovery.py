import os
from pathlib import Path

from system.config_store import ConfigStore


def test_corrupt_config_is_backed_up_and_recovered(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    store.dir.mkdir(parents=True)
    store.path.write_text("{broken", encoding="utf-8")
    data = store.load()
    assert data["schema_version"] == 2
    assert store.path.exists()
    assert list(store.dir.glob("config.corrupt-*.json"))


def test_config_clamps_rotation_and_target(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    data = store.validate({
        "schema_version": 1,
        "advanced": {"minimum_interval_seconds": 1, "max_status_length": 160, "apply_timeout_seconds": 99},
        "status": {"presets": [" A ", "a", ""], "rotation": {"interval_seconds": 1, "mode": "bad"}},
        "target": {"fallback_relative_x": 4, "fallback_relative_y": -2},
    })
    assert data["advanced"]["minimum_interval_seconds"] == 5
    assert data["advanced"]["apply_timeout_seconds"] == 30
    assert data["status"]["rotation"]["interval_seconds"] == 5
    assert data["status"]["rotation"]["mode"] == "sequential"
    assert data["status"]["presets"] == ["A"]
    assert data["target"]["fallback_relative_x"] == 1.0
    assert data["target"]["fallback_relative_y"] == 0.0
