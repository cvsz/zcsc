from system.config_store import ConfigStore, DEFAULT_CONFIG


def test_merge_preserves_defaults():
    merged = ConfigStore._merge(DEFAULT_CONFIG, {"camfrog": {"auto_start": True}})
    assert merged["camfrog"]["auto_start"] is True
    assert "window_title_regex" in merged["camfrog"]
    assert merged["target"]["control_type"] == "ComboBox"


def test_fresh_config_uses_blank_user_status_values():
    assert DEFAULT_CONFIG["status"]["presets"] == []
    assert DEFAULT_CONFIG["status"]["editor_messages"] == ["", "", "", ""]


def test_profile_link_nickname_is_sanitized_and_bounded():
    data = ConfigStore.validate(ConfigStore._merge(DEFAULT_CONFIG, {
        "profile_links": {"nickname": "  Sea\x00User  "},
    }))
    assert data["profile_links"]["nickname"] == "SeaUser"

    data["profile_links"]["nickname"] = "x" * 100
    assert ConfigStore.validate(data)["profile_links"]["nickname"] == "x" * 64
