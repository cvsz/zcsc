from system.config_store import ConfigStore, DEFAULT_CONFIG


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


def test_standard_status_selection_round_trips_through_config(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    store = ConfigStore()

    data = store.load()
    data["status"]["standard_status_id"] = "welcome"
    store.save(data)

    assert store.load()["status"]["standard_status_id"] == "welcome"


def test_invalid_standard_status_id_uses_catalog_default():
    data = ConfigStore._merge(DEFAULT_CONFIG, {"status": {"standard_status_id": "invalid"}})

    assert ConfigStore.validate(data)["status"]["standard_status_id"] == "available"


def test_bad_word_auto_kick_is_opt_in_and_strict_boolean():
    data = ConfigStore._merge(DEFAULT_CONFIG, {"bad_word_moderation": {"auto_kick": "true"}})

    assert ConfigStore.validate(data)["bad_word_moderation"]["auto_kick"] is False

    data = ConfigStore._merge(DEFAULT_CONFIG, {"bad_word_moderation": {"auto_kick": True}})
    assert ConfigStore.validate(data)["bad_word_moderation"]["auto_kick"] is True


def test_default_bad_word_terms_include_thai_and_english_but_moderation_stays_opt_in(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    moderation = ConfigStore().load()["bad_word_moderation"]

    assert "fuck" in moderation["terms"]
    assert "เหี้ย" in moderation["terms"]
    assert len(moderation["terms"]) >= 100
    assert moderation["enabled"] is False
    assert moderation["auto_kick"] is False


def test_explicitly_empty_bad_word_terms_remain_empty():
    data = ConfigStore._merge(DEFAULT_CONFIG, {"bad_word_moderation": {"terms": []}})

    assert ConfigStore.validate(data)["bad_word_moderation"]["terms"] == []


def test_room_event_notifications_are_opt_in_and_phrases_are_sanitized():
    data = ConfigStore._merge(DEFAULT_CONFIG, {
        "room_event_notifications": {
            "enabled": "true",
            "phrases": ["  op   granted ", "OP GRANTED", "", "kicked\x00 user", "x"],
            "cooldown_seconds": -5,
        }
    })

    clean = ConfigStore.validate(data)["room_event_notifications"]

    assert clean["enabled"] is False
    assert clean["phrases"] == ["op granted", "kicked user"]
    assert clean["cooldown_seconds"] == 1


def test_room_control_profile_fields_are_sanitized():
    data = ConfigStore._merge(DEFAULT_CONFIG, {
        "room_actions": {
            "room_title": "  Example Room\x00 ",
            "owner_nickname": " RoomOwner_1 ",
            "target_nicknames": {
                "friend": " Friend-7 ",
                "kick": "Bad Nick",
            },
        },
    })

    clean = ConfigStore.validate(data)["room_actions"]

    assert clean["room_title"] == "Example Room"
    assert clean["owner_nickname"] == "RoomOwner_1"
    assert clean["target_nicknames"]["friend"] == "Friend-7"
    assert clean["target_nicknames"]["kick"] == ""


def test_favorites_and_rotation_schedule_are_sanitized():
    data = ConfigStore._merge(DEFAULT_CONFIG, {
        "status": {
            "favorite_standard_ids": ["welcome", "invalid", "welcome"],
            "rotation": {
                "schedule_enabled": True,
                "schedule_start": "25:00",
                "schedule_end": "18:30",
                "quiet_hours_enabled": True,
                "quiet_start": "22:15",
                "quiet_end": "08:00",
            },
        },
    })

    clean = ConfigStore.validate(data)

    assert clean["status"]["favorite_standard_ids"] == ["welcome"]
    assert clean["status"]["rotation"]["schedule_enabled"] is True
    assert clean["status"]["rotation"]["schedule_start"] == "08:00"
    assert clean["status"]["rotation"]["schedule_end"] == "18:30"
    assert clean["status"]["rotation"]["quiet_start"] == "22:15"
    assert clean["status"]["rotation"]["quiet_end"] == "08:00"


def test_auto_respond_requires_explicit_boolean_flags():
    data = ConfigStore._merge(DEFAULT_CONFIG, {
        "auto_respond": {
            "enabled": "true",
            "private_enabled": "false",
            "room_enabled": 1,
            "cooldown_seconds": "not-a-number",
            "poll_interval_seconds": 99,
        }
    })

    clean = ConfigStore.validate(data)

    assert clean["auto_respond"]["enabled"] is False
    assert clean["auto_respond"]["private_enabled"] is False
    assert clean["auto_respond"]["room_enabled"] is False
    assert clean["auto_respond"]["cooldown_seconds"] == 60
    assert clean["auto_respond"]["poll_interval_seconds"] == 10


def test_auto_respond_config_preserves_multiline_reply_and_background_toggle():
    data = ConfigStore._merge(DEFAULT_CONFIG, {
        "auto_respond": {"reply_text": " First line \r\nSecond   line "},
        "target": {"background_enabled": False},
    })

    clean = ConfigStore.validate(data)

    assert clean["auto_respond"]["reply_text"] == "First line\nSecond line"
    assert clean["target"]["background_enabled"] is False
