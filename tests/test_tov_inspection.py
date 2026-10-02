import json
from types import SimpleNamespace

import pytest

from camfrog.controller import CamfrogController


class FakeControl:
    def __init__(self, title, control_type, automation_id="", class_name=""):
        self._title = title
        self.element_info = SimpleNamespace(
            control_type=control_type,
            automation_id=automation_id,
            class_name=class_name,
        )

    def window_text(self):
        return self._title


class FakeWindow:
    def __init__(self, pid, title, controls=()):
        self._pid = pid
        self._title = title
        self._controls = list(controls)
        self.element_info = SimpleNamespace(control_type="Window")

    def process_id(self):
        return self._pid

    def window_text(self):
        return self._title

    def descendants(self):
        return self._controls


class FakeDesktop:
    def __init__(self, windows):
        self._windows = windows

    def windows(self, visible_only=False):
        assert visible_only is True
        return self._windows


def test_video_overlay_inspection_checks_configured_camfrog_process_and_omits_values(monkeypatch):
    controls = [
        FakeControl("Enable Text Over Video Settings", "CheckBox", "tov_enable_button"),
        FakeControl("Background:", "Text"),
        FakeControl("Sensitive overlay text", "Edit", "tov_text_edit"),
        FakeControl("#22AA44", "ComboBox", "tov_text_color_combo"),
        FakeControl("Apply", "Button"),
        FakeControl("Apply", "Edit", "tov_text_edit_2"),
    ]
    settings = FakeWindow(18, "Settings - Video & Audio - Text Over Video", controls)
    main = FakeWindow(17, "Camfrog Video Chat")
    unrelated = FakeWindow(99, "Camfrog Settings", [FakeControl("Other value", "Edit")])
    controller = CamfrogController({})
    monkeypatch.setattr(controller, "client_processes", lambda: [SimpleNamespace(pid=18)])
    controller._desktop = lambda: FakeDesktop([unrelated, main, settings])

    result = controller.inspect_video_overlay_controls()
    serialized = json.dumps(result)

    assert len(result) == 1
    assert result[0]["window_title"] == "Camfrog Settings"
    assert result[0]["process_id"] == 18
    assert result[0]["has_tov_markers"] is True
    assert any(control["automation_id"] == "tov_enable_button" for control in result[0]["controls"])
    assert any(control["title"] == "Background:" for control in result[0]["controls"])
    assert any(control["title"] == "Apply" for control in result[0]["controls"])
    assert "Sensitive overlay text" not in serialized
    assert "#22AA44" not in serialized
    assert serialized.count("Apply") == 1
    assert "Other value" not in serialized


def test_video_overlay_inspection_falls_back_to_sanitized_main_window_metadata(monkeypatch):
    controller = CamfrogController({})
    monkeypatch.setattr(controller, "client_processes", lambda: [SimpleNamespace(pid=17)])
    controller._desktop = lambda: FakeDesktop([
        FakeWindow(17, "Camfrog Video Chat", [FakeControl("private room / overlay text", "Edit", "text_entry")]),
        FakeWindow(99, "Camfrog Settings"),
    ])

    result = controller.inspect_video_overlay_controls()
    serialized = json.dumps(result)

    assert len(result) == 1
    assert result[0]["match_reason"] == "camfrog_window"
    assert "private room / overlay text" not in serialized
    assert result[0]["controls"][0]["title"] == ""


def test_video_overlay_inspection_reports_no_visible_camfrog_windows(monkeypatch):
    controller = CamfrogController({})
    monkeypatch.setattr(controller, "client_processes", lambda: [SimpleNamespace(pid=17)])
    controller._desktop = lambda: FakeDesktop([FakeWindow(99, "Camfrog Settings")])

    with pytest.raises(RuntimeError, match="no visible windows"):
        controller.inspect_video_overlay_controls()


def test_video_overlay_inspection_requires_a_running_camfrog_process(monkeypatch):
    controller = CamfrogController({})
    monkeypatch.setattr(controller, "client_processes", lambda: [])

    with pytest.raises(RuntimeError, match="No Camfrog process"):
        controller.inspect_video_overlay_controls()
