from copy import deepcopy
import threading
from types import SimpleNamespace

from status_catalog import STANDARD_STATUSES
from system.config_store import ConfigStore, DEFAULT_CONFIG
from ui.dashboard import AppUI
import ui.dashboard as dashboard


class FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeMenu:
    def __init__(self):
        self.values = []

    def configure(self, **kwargs):
        self.values = kwargs["values"]


class FakeTextBox:
    def __init__(self, value=""):
        self.value = value

    def get(self, *_args):
        return self.value

    def delete(self, *_args):
        self.value = ""

    def insert(self, _index, value):
        self.value = value


def test_saved_status_id_loads_into_bilingual_dropdown(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    data = store.load()
    data["status"]["standard_status_id"] = "welcome"
    store.save(data)
    loaded = store.load()

    app = SimpleNamespace(
        standard_status_id_var=FakeVar(loaded["status"]["standard_status_id"]),
        standard_status_display_var=FakeVar(),
        standard_status_menu=FakeMenu(),
        standard_status_search_var=FakeVar(),
        standard_status_category_key="all",
        config_data={"status": {"favorite_standard_ids": []}},
        language_var=FakeVar("EN"),
        _refresh_standard_status_favorite_button=lambda: None,
    )
    AppUI._refresh_standard_status_dropdown(app)

    assert len(app.standard_status_menu.values) == 50
    assert app.standard_status_display_var.get() == "Welcome everyone"
    assert "Welcome everyone" in app.standard_status_menu.values
    assert app.standard_status_id_var.get() == "welcome"

    app.language_var.set("TH")
    AppUI._refresh_standard_status_dropdown(app)
    assert app.standard_status_display_var.get() == "ยินดีต้อนรับทุกคน"
    assert "ยินดีต้อนรับทุกคน" in app.standard_status_menu.values


def test_config_sync_saves_selected_standard_status_id(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    app = SimpleNamespace(
        config_data=deepcopy(DEFAULT_CONFIG),
        exe_var=FakeVar(),
        autostart_camfrog_var=FakeVar(False),
        restore_state_var=FakeVar(True),
        foreground_fallback_var=FakeVar(False),
        background_control_var=FakeVar(True),
        control_type_var=FakeVar("ComboBox"),
        automation_id_var=FakeVar(),
        title_re_var=FakeVar(".*"),
        fallback_x_var=FakeVar("0.50"),
        fallback_y_var=FakeVar("0.19"),
        presets_box=SimpleNamespace(get=lambda *_args: ""),
        status_message_vars=[FakeVar() for _ in range(4)],
        standard_status_id_var=FakeVar("welcome"),
        rotation_var=FakeVar(False),
        interval_unit_var=FakeVar("minutes"),
        interval_var=FakeVar("10"),
        mode_var=FakeVar("sequential"),
        rotation_source_var=FakeVar("Camfrog Status History (random)"),
        schedule_enabled_var=FakeVar(False),
        schedule_start_var=FakeVar("08:00"),
        schedule_end_var=FakeVar("23:00"),
        quiet_hours_enabled_var=FakeVar(False),
        quiet_start_var=FakeVar("22:00"),
        quiet_end_var=FakeVar("08:00"),
        start_windows_var=FakeVar(False),
        registry_auto_var=FakeVar(True),
        random_color_var=FakeVar(False),
        custom_color_var=FakeVar(False),
        custom_color_value=FakeVar("#00C7BE"),
        marquee_var=FakeVar(False),
        marquee_single_character_var=FakeVar(True),
        marquee_frame_interval_var=FakeVar("5"),
        auto_respond_enabled_var=FakeVar(True),
        auto_respond_private_var=FakeVar(True),
        auto_respond_room_var=FakeVar(True),
        auto_respond_reply_box=FakeTextBox("First line\nSecond line"),
        auto_respond_username_var=FakeVar("TestNick"),
        profile_nickname_var=FakeVar("ProfileNick"),
        auto_respond_cooldown_var=FakeVar("45"),
        auto_respond_poll_var=FakeVar("3"),
        auto_respond_selector_vars={
            "private": {
                "window_title_contains": FakeVar("Private chat"),
                "history_automation_id": FakeVar("private-history"),
                "input_automation_id": FakeVar("private-input"),
                "send_automation_id": FakeVar("private-send"),
            },
            "room": {
                "window_title_contains": FakeVar("Room"),
                "history_automation_id": FakeVar("room-history"),
                "input_automation_id": FakeVar("room-input"),
                "send_automation_id": FakeVar("room-send"),
            },
        },
        room_action_enabled_var=FakeVar(False),
        room_action_var=FakeVar("kick"),
        room_action_target_var=FakeVar(),
        room_action_room_title_var=FakeVar(),
        room_action_owner_var=FakeVar(),
        room_action_target_nicknames={},
        room_action_template_vars={
            action: FakeVar() for action in ("op", "friend", "admin", "owner", "mute", "kick", "ban")
            },
            bad_word_enabled_var=FakeVar(False),
            bad_word_auto_kick_var=FakeVar(False),
        bad_word_terms_box=SimpleNamespace(get=lambda *_args: ""),
        bad_word_cooldown_var=FakeVar("60"),
        room_event_enabled_var=FakeVar(False),
        room_event_phrases_box=SimpleNamespace(get=lambda *_args: ""),
        language_var=FakeVar("EN"),
        controller=SimpleNamespace(),
        _unit_internal=AppUI._unit_internal,
        _mode_internal=AppUI._mode_internal,
        _rotation_source_internal=AppUI._rotation_source_internal,
    )

    store.save(AppUI._sync_ui_to_config(app))

    saved = store.load()
    assert saved["status"]["standard_status_id"] == "welcome"
    assert saved["status"]["rotation"]["source"] == "camfrog_history"
    assert saved["status"]["rotation"]["mode"] == "random"
    assert saved["status"]["styles"]["marquee_single_character"] is True
    assert saved["auto_respond"]["enabled"] is True
    assert saved["auto_respond"]["reply_text"] == "First line\nSecond line"
    assert saved["auto_respond"]["own_username"] == "TestNick"
    assert saved["profile_links"]["nickname"] == "ProfileNick"
    assert saved["auto_respond"]["cooldown_seconds"] == 45
    assert saved["auto_respond"]["private"]["history_automation_id"] == "private-history"
    assert saved["auto_respond"]["room"]["send_automation_id"] == "room-send"


def test_room_action_and_bad_word_settings_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()
    app = SimpleNamespace(
        config_data=deepcopy(DEFAULT_CONFIG),
        exe_var=FakeVar(),
        autostart_camfrog_var=FakeVar(False),
        restore_state_var=FakeVar(True),
        foreground_fallback_var=FakeVar(False),
        background_control_var=FakeVar(False),
        control_type_var=FakeVar("ComboBox"),
        automation_id_var=FakeVar(),
        title_re_var=FakeVar(".*"),
        fallback_x_var=FakeVar("0.50"),
        fallback_y_var=FakeVar("0.19"),
        presets_box=SimpleNamespace(get=lambda *_args: ""),
        status_message_vars=[FakeVar() for _ in range(4)],
        standard_status_id_var=FakeVar("welcome"),
        rotation_var=FakeVar(False),
        interval_unit_var=FakeVar("minutes"),
        interval_var=FakeVar("10"),
        mode_var=FakeVar("sequential"),
        schedule_enabled_var=FakeVar(False),
        schedule_start_var=FakeVar("08:00"),
        schedule_end_var=FakeVar("23:00"),
        quiet_hours_enabled_var=FakeVar(False),
        quiet_start_var=FakeVar("22:00"),
        quiet_end_var=FakeVar("08:00"),
        start_windows_var=FakeVar(False),
        registry_auto_var=FakeVar(True),
        random_color_var=FakeVar(False),
        custom_color_var=FakeVar(False),
        custom_color_value=FakeVar("#00C7BE"),
        marquee_var=FakeVar(False),
        marquee_frame_interval_var=FakeVar("10"),
        auto_respond_enabled_var=FakeVar(False),
        auto_respond_private_var=FakeVar(True),
        auto_respond_room_var=FakeVar(True),
        auto_respond_reply_box=FakeTextBox("Thanks."),
        auto_respond_username_var=FakeVar("TestNick"),
        profile_nickname_var=FakeVar("ProfileNick"),
        auto_respond_cooldown_var=FakeVar("60"),
        auto_respond_poll_var=FakeVar("2"),
        auto_respond_selector_vars={"private": {}, "room": {}},
        room_action_enabled_var=FakeVar(True),
        room_action_var=FakeVar("friend"),
        room_action_target_var=FakeVar("FriendNick"),
        room_action_room_title_var=FakeVar("Example Room"),
        room_action_owner_var=FakeVar("RoomOwner"),
        room_action_target_nicknames={"friend": "FriendNick"},
        room_action_template_vars={
            action: FakeVar(f"/{action} {{username}}")
            for action in ("op", "friend", "admin", "owner", "mute", "kick", "ban")
        },
        bad_word_enabled_var=FakeVar(True),
        bad_word_auto_kick_var=FakeVar(True),
        bad_word_terms_box=SimpleNamespace(get=lambda *_args: "spam\n badword "),
        bad_word_cooldown_var=FakeVar("90"),
        room_event_enabled_var=FakeVar(True),
        room_event_phrases_box=SimpleNamespace(get=lambda *_args: "was granted op\nwas kicked"),
        language_var=FakeVar("EN"),
        controller=SimpleNamespace(),
        _unit_internal=AppUI._unit_internal,
        _mode_internal=AppUI._mode_internal,
        _rotation_source_internal=AppUI._rotation_source_internal,
    )

    store.save(AppUI._sync_ui_to_config(app))

    saved = store.load()
    assert saved["target"]["background_enabled"] is False
    assert saved["room_actions"]["enabled"] is True
    assert saved["room_actions"]["room_title"] == "Example Room"
    assert saved["room_actions"]["owner_nickname"] == "RoomOwner"
    assert saved["room_actions"]["target_nicknames"]["friend"] == "FriendNick"
    assert saved["room_actions"]["command_templates"]["kick"] == "/kick {username}"
    assert saved["bad_word_moderation"] == {
        "enabled": True,
        "auto_kick": True,
        "terms": ["spam", "badword"],
        "cooldown_seconds": 90,
    }
    assert saved["room_event_notifications"]["enabled"] is True
    assert saved["room_event_notifications"]["phrases"] == ["was granted op", "was kicked"]


def test_load_bad_word_starters_preserves_custom_terms_and_avoids_duplicates():
    app = SimpleNamespace(bad_word_terms_box=FakeTextBox("custom phrase\nFUCK"))

    AppUI._load_bad_word_starter_terms(app)

    terms = app.bad_word_terms_box.get("1.0", "end-1c").splitlines()
    assert terms[:2] == ["custom phrase", "FUCK"]
    assert sum(term.casefold() == "fuck" for term in terms) == 1
    assert "เหี้ย" in terms


def test_room_action_selection_restores_target_for_selected_action():
    app = SimpleNamespace(
        _last_room_action_selection="kick",
        room_action_target_nicknames={"kick": "TargetOne", "friend": "FriendNick"},
        room_action_target_var=FakeVar("ChangedKickTarget"),
    )

    AppUI._room_action_selected(app, "friend")

    assert app.room_action_target_nicknames["kick"] == "ChangedKickTarget"
    assert app.room_action_target_var.get() == "FriendNick"


def test_select_and_send_standard_status_uses_active_language():
    values = [FakeVar() for _ in range(4)]
    applied = []
    app = SimpleNamespace(
        language_var=FakeVar("TH"),
        standard_status_id_var=FakeVar("available"),
        status_message_vars=values,
        config_data={"status": {}},
        _sync_ui_to_config=lambda: None,
        _refresh_status_preview=lambda: None,
        _apply_message_clicked=lambda index: applied.append((index, values[index].get())),
        _refresh_standard_status_favorite_button=lambda: None,
    )

    AppUI._standard_status_selected(app, STANDARD_STATUSES[0].dropdown_label("TH"))
    AppUI._apply_standard_status_clicked(app)

    assert app.standard_status_id_var.get() == "available"
    assert values[0].get() == "พร้อมคุย"
    assert applied == [(0, "พร้อมคุย")]


def test_each_message_apply_row_uses_the_normal_send_worker(monkeypatch):
    scheduled = []

    class FakeThread:
        def __init__(self, *, target, args, daemon):
            scheduled.append((target, args, daemon))

        def start(self):
            pass

    class FakeLabel:
        def configure(self, **_kwargs):
            pass

    monkeypatch.setattr(dashboard.threading, "Thread", FakeThread)
    values = [FakeVar(f"message {index}") for index in range(1, 5)]
    app = SimpleNamespace(
        status_message_vars=values,
        _sync_ui_to_config=lambda: None,
        marquee_var=FakeVar(False),
        config_data={},
        rotation=SimpleNamespace(running=False),
        marquee_animation=SimpleNamespace(stop=lambda: None),
        _styled_value=lambda value, advance: value,
        state_label=FakeLabel(),
        language_var=FakeVar("EN"),
        _apply_worker=lambda value: None,
    )

    for index in range(4):
        AppUI._apply_message_clicked(app, index)

    assert scheduled == [
        (app._apply_worker, (f"message {index}",), True)
        for index in range(1, 5)
    ]


def test_history_rotation_uses_camfrog_status_history_rows_only():
    app = SimpleNamespace(
        rotation_source_var=FakeVar("Camfrog Status History (random)"),
        _history_values=["Old status", "Old status", "New status", "  "],
        _rotation_source_internal=AppUI._rotation_source_internal,
    )
    config = {
        "status": {
            "rotation": {"source": "camfrog_history"},
            "editor_messages": ["message slot 1"],
        }
    }

    assert AppUI._rotation_messages(app, config) == ["Old status", "New status"]


def test_enter_from_each_message_row_uses_the_same_send_handler():
    applied = []
    app = SimpleNamespace(_apply_message_clicked=applied.append)

    for index in range(4):
        assert AppUI._apply_message_from_enter(app, None, index) == "break"

    assert applied == [0, 1, 2, 3]


def test_stage_only_standard_status_uses_separate_no_commit_worker(monkeypatch):
    scheduled = []

    class FakeThread:
        def __init__(self, *, target, args, daemon):
            scheduled.append((target, args, daemon))

        def start(self):
            pass

    class FakeLabel:
        def configure(self, **_kwargs):
            pass

    monkeypatch.setattr(dashboard.threading, "Thread", FakeThread)
    app = SimpleNamespace(
        standard_status_id_var=FakeVar("welcome"),
        language_var=FakeVar("EN"),
        status_message_vars=[FakeVar() for _ in range(4)],
        _sync_ui_to_config=lambda: None,
        state_label=FakeLabel(),
        _stage_status_worker=lambda value: None,
        _apply_message_clicked=lambda _index: (_ for _ in ()).throw(
            AssertionError("Stage-only must not call the normal commit path")
        ),
    )

    AppUI._stage_standard_status_clicked(app)

    assert app.status_message_vars[0].get() == "Welcome everyone"
    assert scheduled == [(app._stage_status_worker, ("Welcome everyone",), True)]


def test_stage_worker_calls_only_the_no_commit_controller_method():
    calls = []
    shown = []
    result = SimpleNamespace(ok=True, message="draft staged")
    app = SimpleNamespace(
        controller=SimpleNamespace(
            stage_status_text=lambda value: calls.append(("stage", value)) or result,
            set_status=lambda value: calls.append(("send", value)),
        ),
        after=lambda _delay, callback: callback(),
        _show_result=shown.append,
    )

    AppUI._stage_status_worker(app, "draft")

    assert calls == [("stage", "draft")]
    assert shown == [result]


def test_rotation_background_styling_uses_config_not_tk_variables():
    sent = []

    class Label:
        def configure(self, **kwargs):
            self.text = kwargs["text"]

    app = SimpleNamespace(
        config_data={
            "status": {
                "styles": {
                    "random_color": False,
                    "custom_color_enabled": True,
                    "custom_color": "#123ABC",
                    "marquee": False,
                    "marquee_width": 28,
                    "color_template": "<{color}>{text}",
                    "palette": [],
                }
            }
        },
        _style_lock=threading.Lock(),
        _marquee_offset=0,
        controller=SimpleNamespace(set_status=lambda value: sent.append(value) or SimpleNamespace(ok=True, message="sent")),
        after=lambda _delay, callback: callback(),
        state_label=Label(),
    )

    AppUI._apply_status_background(app, "row 1")

    assert sent == ["<#123ABC>row 1"]
    assert app.state_label.text == "sent"


def test_auto_start_resumes_automation_without_launch_when_disabled():
    resumed = []
    launched = []
    app = SimpleNamespace(
        config_data={"camfrog": {"auto_start": False}},
        exe_var=FakeVar(r"C:\Camfrog\Camfrog Video Chat.exe"),
        _begin_start_or_connect=lambda on_complete=None: launched.append(on_complete),
        after=lambda delay, callback: callback(),
    )

    AppUI._auto_start_camfrog_if_configured(app, lambda: resumed.append("resume"))

    assert resumed == ["resume"]
    assert launched == []


def test_auto_start_launches_then_defers_automation_resume():
    resumed = []
    launched = []
    events = []
    app = SimpleNamespace(
        config_data={"camfrog": {"auto_start": True}},
        exe_var=FakeVar(r"C:\Camfrog\Camfrog Video Chat.exe"),
        _sync_ui_to_config=lambda: events.append("sync"),
        _begin_start_or_connect=lambda on_complete=None: (events.append("launch"), launched.append(on_complete)),
        after=lambda delay, callback: callback(),
    )

    AppUI._auto_start_camfrog_if_configured(app, lambda: resumed.append("resume"))

    # UI config must be synchronized before the connection attempt begins.
    assert events == ["sync", "launch"]
    assert len(launched) == 1
    assert resumed == []
    launched[0]()
    assert resumed == ["resume"]


def test_auto_start_does_not_sync_ui_when_not_configured():
    events = []
    app = SimpleNamespace(
        config_data={"camfrog": {"auto_start": False}},
        exe_var=FakeVar(r"C:\Camfrog\Camfrog Video Chat.exe"),
        _sync_ui_to_config=lambda: events.append("sync"),
        _begin_start_or_connect=lambda on_complete=None: events.append("launch"),
        after=lambda delay, callback: callback(),
    )

    AppUI._auto_start_camfrog_if_configured(app, lambda: None)

    assert events == []


def test_auto_start_without_executable_resumes_without_launch():
    resumed = []
    launched = []
    app = SimpleNamespace(
        config_data={"camfrog": {"auto_start": True}},
        exe_var=FakeVar(""),
        _begin_start_or_connect=lambda on_complete=None: launched.append(on_complete),
        after=lambda delay, callback: None,
    )

    AppUI._auto_start_camfrog_if_configured(app, lambda: resumed.append("resume"))

    assert resumed == ["resume"]
    assert launched == []
