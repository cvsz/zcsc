import logging
from pathlib import Path
from types import SimpleNamespace

import system.logging_setup as logging_setup


def test_configure_logging_falls_back_to_temp_when_appdata_is_unwritable(monkeypatch, tmp_path):
    app_data = tmp_path / "appdata" / "CamfrogStatusChanger"
    temp_root = tmp_path / "temp"
    expected_log = temp_root / "CamfrogStatusChanger" / "logs" / "app.log"
    monkeypatch.setattr(logging_setup, "app_data_dir", lambda: app_data)
    monkeypatch.setattr(logging_setup, "tempfile", SimpleNamespace(gettempdir=lambda: str(temp_root)), raising=False)
    original_mkdir = Path.mkdir

    def deny_appdata_logs(path, *args, **kwargs):
        if path == app_data / "logs":
            raise PermissionError("simulated APPDATA denial")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", deny_appdata_logs)
    root_logger = logging.getLogger()
    prior_handlers = list(root_logger.handlers)
    prior_level = root_logger.level

    try:
        actual_log = logging_setup.configure_logging()
        logging.getLogger("startup-test").error("fallback log marker")
        for handler in root_logger.handlers:
            handler.flush()

        assert actual_log == expected_log
        assert "fallback log marker" in expected_log.read_text(encoding="utf-8")
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            if handler not in prior_handlers:
                handler.close()
        for handler in prior_handlers:
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)
        root_logger.setLevel(prior_level)
