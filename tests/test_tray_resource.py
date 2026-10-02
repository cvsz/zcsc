from types import SimpleNamespace

from system.tray import resource_path
from ui.dashboard import AppUI


def test_tray_resource_path_points_to_requested_name():
    assert resource_path("app.ico").name == "app.ico"


def test_tray_is_available_only_while_icon_thread_runs():
    alive_thread = SimpleNamespace(is_alive=lambda: True)
    dead_thread = SimpleNamespace(is_alive=lambda: False)

    assert AppUI._tray_available(SimpleNamespace(_tray_icon=object(), _tray_thread=alive_thread))
    assert not AppUI._tray_available(SimpleNamespace(_tray_icon=object(), _tray_thread=dead_thread))
    assert not AppUI._tray_available(SimpleNamespace(_tray_icon=None, _tray_thread=alive_thread))


def test_close_exits_when_tray_is_unavailable():
    events = []
    app = SimpleNamespace(
        _exiting=False,
        _tray_available=lambda: False,
        _exit_app=lambda: events.append("exit"),
        withdraw=lambda: events.append("withdraw"),
    )

    AppUI._on_close(app)

    assert events == ["exit"]


def test_close_hides_when_tray_is_running():
    events = []
    app = SimpleNamespace(
        _exiting=False,
        _tray_available=lambda: True,
        _exit_app=lambda: events.append("exit"),
        withdraw=lambda: events.append("withdraw"),
    )

    AppUI._on_close(app)

    assert events == ["withdraw"]


def test_stopped_tray_restores_a_hidden_dashboard():
    events = []
    app = SimpleNamespace(
        _exiting=False,
        _tray_icon=object(),
        _monitor_tray=AppUI._monitor_tray,
        _tray_available=lambda: False,
        state=lambda: "withdrawn",
        deiconify=lambda: events.append("deiconify"),
        lift=lambda: events.append("lift"),
        after=lambda delay, callback: events.append(("after", delay, callback)),
    )

    AppUI._monitor_tray(app)

    assert events[0:2] == ["deiconify", "lift"]
    assert events[2][0:2] == ("after", 1000)
