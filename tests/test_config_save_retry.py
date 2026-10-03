import json
from types import SimpleNamespace

import pytest

import system.config_store as config_store
from system.config_store import ConfigStore


def _replace_os(monkeypatch, replace):
    real_os = config_store.os
    monkeypatch.setattr(
        config_store,
        "os",
        SimpleNamespace(replace=replace, fsync=real_os.fsync),
    )


def test_config_save_retries_transient_permission_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    store.ensure_defaults()
    data = store.load()
    data["status"]["presets"] = ["saved after retry"]
    real_replace = config_store.os.replace
    calls = []

    def flaky_replace(source, destination):
        calls.append((source, destination))
        if len(calls) < 3:
            raise PermissionError("temporary scanner lock")
        real_replace(source, destination)

    sleeps = []
    monkeypatch.setattr(config_store, "time", SimpleNamespace(sleep=lambda delay: sleeps.append(delay)))
    _replace_os(monkeypatch, flaky_replace)

    store.save(data)

    assert len(calls) == 3
    assert sleeps == [0.05, 0.1]
    assert store.load()["status"]["presets"] == ["saved after retry"]
    assert not store.path.with_suffix(".tmp").exists()


def test_config_save_keeps_original_and_complete_temp_after_retry_exhaustion(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    store.ensure_defaults()
    original_bytes = store.path.read_bytes()
    data = store.load()
    data["status"]["presets"] = ["new complete value"]
    calls = []

    def locked_replace(source, destination):
        calls.append((source, destination))
        raise PermissionError("persistent scanner lock")

    monkeypatch.setattr(config_store, "time", SimpleNamespace(sleep=lambda _delay: None))
    _replace_os(monkeypatch, locked_replace)

    with pytest.raises(PermissionError, match="persistent scanner lock"):
        store.save(data)

    temp_path = store.path.with_suffix(".tmp")
    assert len(calls) == 4
    assert store.path.read_bytes() == original_bytes
    assert json.loads(temp_path.read_text(encoding="utf-8"))["status"]["presets"] == ["new complete value"]
