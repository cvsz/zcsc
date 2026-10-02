from pathlib import Path

from camfrog.window_locator import score_candidate


def test_camfrog_window_scores_above_generic_window():
    good = score_candidate("Camfrog Video Chat", "MainWindow", True, 300000)
    weak = score_candidate("", "Window", False, 1000)
    assert good > weak


def test_status_changer_window_is_penalized():
    app = score_candidate("Camfrog Status Changer", "TkTopLevel", True, 300000)
    camfrog = score_candidate("Camfrog Video Chat", "MainWindow", True, 300000)
    assert camfrog > app


def test_manual_and_rotation_use_different_rate_limit_modes():
    source = (Path(__file__).parents[1] / "ui" / "dashboard.py").read_text(encoding="utf-8")
    assert "set_status(value,respect_rate_limit=False,force_enter_commit=True)" in source
    assert "set_status(styled,respect_rate_limit=True)" in source


def test_manual_apply_forces_enter_commit():
    source = (Path(__file__).parents[1] / "ui" / "dashboard.py").read_text(encoding="utf-8")
    assert "force_enter_commit=True" in source


def test_controller_does_not_stop_at_background_when_enter_is_forced():
    source = (Path(__file__).parents[1] / "camfrog" / "controller.py").read_text(encoding="utf-8")
    assert "and not force_enter_commit" in source
    assert 'stage="foreground-enter-committed" if force_enter_commit else "foreground-submitted"' in source


def test_foreground_uses_exact_edit_enter_before_global_fallback():
    source = (Path(__file__).parents[1] / "camfrog" / "foreground_fallback.py").read_text(encoding="utf-8")
    assert 'edit.type_keys("{ENTER}"' in source
    assert 'send_keys("{ENTER}", pause=0.05)' in source
