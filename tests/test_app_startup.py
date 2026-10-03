import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import app


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"ui": {"language": "TH"}}, "TH"),
        ({"ui": {"language": "EN"}}, "EN"),
        ({"ui": None}, "EN"),
        ({"ui": []}, "EN"),
        ({"ui": "TH"}, "EN"),
        ({"ui": 1}, "EN"),
        (None, "EN"),
        (["TH"], "EN"),
    ],
)
def test_startup_language_tolerates_wrong_config_shapes(config, expected):
    assert app._startup_language(config) == expected


def test_startup_dialog_uses_one_hidden_root_and_always_destroys_it(monkeypatch):
    calls = []

    class FakeRoot:
        def withdraw(self):
            calls.append(("withdraw",))

        def destroy(self):
            calls.append(("destroy",))

    root = FakeRoot()
    tkinter = ModuleType("tkinter")
    tkinter.Tk = lambda: root
    tkinter.messagebox = SimpleNamespace(
        showerror=lambda title, message, parent: calls.append(("showerror", title, message, parent))
    )
    monkeypatch.setitem(sys.modules, "tkinter", tkinter)

    app._show_startup_dialog("showerror", "Startup", "Failed")

    assert calls == [
        ("withdraw",),
        ("showerror", "Startup", "Failed", root),
        ("destroy",),
    ]


@pytest.mark.parametrize("failure_at", ["ensure_defaults", "load"])
def test_pre_ui_config_failure_is_logged_and_shown(monkeypatch, tmp_path, failure_at):
    import system.config_store as config_store

    monkeypatch.setenv("APPDATA", str(tmp_path))
    shown = []

    class BrokenStore:
        def ensure_defaults(self):
            if failure_at == "ensure_defaults":
                raise OSError("simulated config directory failure")

        def load(self):
            if failure_at == "load":
                raise ValueError("simulated config load failure")
            return {"ui": {"language": "TH"}}

    monkeypatch.setattr(config_store, "ConfigStore", BrokenStore)
    monkeypatch.setattr(app, "ConfigStore", BrokenStore, raising=False)
    monkeypatch.setattr(app, "_show_startup_dialog", lambda *args: shown.append(args), raising=False)
    root_logger = logging.getLogger()
    prior_handlers = list(root_logger.handlers)
    prior_level = root_logger.level

    try:
        assert app.main() == 1
        log_path = tmp_path / "CamfrogStatusChanger" / "logs" / "app.log"
        assert log_path.exists()
        contents = log_path.read_text(encoding="utf-8")
        assert "Fatal application startup failure" in contents
        assert "simulated config" in contents
        assert shown and shown[0][0] == "showerror"
        assert "app.log" in shown[0][2]
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            if handler not in prior_handlers:
                handler.close()
        for handler in prior_handlers:
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)
        root_logger.setLevel(prior_level)


def test_logging_setup_failure_uses_emergency_temp_log_and_dialog(monkeypatch, tmp_path):
    import system.logging_setup as logging_setup

    log_path = tmp_path / "fallback" / "app.log"
    monkeypatch.setattr(logging_setup, "configure_logging", lambda: (_ for _ in ()).throw(PermissionError("logs unavailable")))
    monkeypatch.setattr(app, "configure_logging", logging_setup.configure_logging, raising=False)
    monkeypatch.setattr(app, "_startup_log_paths", lambda: [log_path], raising=False)
    shown = []
    monkeypatch.setattr(app, "_show_startup_dialog", lambda *args: shown.append(args), raising=False)

    assert app.main() == 1

    assert log_path.exists()
    assert "Fatal application startup failure" in log_path.read_text(encoding="utf-8")
    assert "logs unavailable" in log_path.read_text(encoding="utf-8")
    assert shown and shown[0][0] == "showerror"


def test_emergency_log_falls_back_when_appdata_log_is_unwritable(monkeypatch, tmp_path):
    primary = tmp_path / "appdata" / "logs" / "app.log"
    fallback = tmp_path / "temp" / "CamfrogStatusChanger" / "logs" / "app.log"
    monkeypatch.setattr(app, "_startup_log_paths", lambda: [primary, fallback], raising=False)
    original_open = Path.open

    def deny_primary(path, *args, **kwargs):
        if path == primary:
            raise PermissionError("simulated APPDATA lock")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_primary)

    written = app._write_emergency_log("startup failure details")

    assert written == fallback
    assert "startup failure details" in fallback.read_text(encoding="utf-8")


def test_duplicate_instance_message_uses_safe_language_and_returns_two(monkeypatch, tmp_path):
    import system.config_store as config_store
    import system.single_instance as single_instance

    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake_store = lambda: SimpleNamespace(
        ensure_defaults=lambda: None,
        load=lambda: {"ui": None},
    )
    monkeypatch.setattr(config_store, "ConfigStore", fake_store)
    monkeypatch.setattr(app, "ConfigStore", fake_store, raising=False)
    fake_instance = lambda: SimpleNamespace(
        acquire=lambda: False,
        release=lambda: None,
    )
    monkeypatch.setattr(single_instance, "SingleInstance", fake_instance)
    monkeypatch.setattr(app, "SingleInstance", fake_instance, raising=False)
    shown = []
    monkeypatch.setattr(app, "_show_startup_dialog", lambda *args: shown.append(args), raising=False)
    monkeypatch.setattr(
        app,
        "messagebox",
        SimpleNamespace(showinfo=lambda title, message: shown.append(("showinfo", title, message))),
        raising=False,
    )
    root_logger = logging.getLogger()
    prior_handlers = list(root_logger.handlers)
    prior_level = root_logger.level

    try:
        assert app.main() == 2
        assert shown and shown[0][0] == "showinfo"
        assert "already running" in shown[0][2]
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            if handler not in prior_handlers:
                handler.close()
        for handler in prior_handlers:
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)
        root_logger.setLevel(prior_level)
