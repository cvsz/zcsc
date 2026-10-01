from system.config_store import ConfigStore


def test_four_independent_message_slots_are_preserved():
    data = ConfigStore.validate({
        "status": {
            "presets": [],
            "editor_messages": ["text1", "text2", "text3", "text4"],
            "rotation": {"enabled": False, "interval_seconds": 30, "mode": "sequential"},
        },
        "advanced": {"minimum_interval_seconds": 5},
    })
    assert data["status"]["editor_messages"] == ["text1", "text2", "text3", "text4"]


def test_legacy_editor_lines_migrate_to_independent_messages():
    data = ConfigStore.validate({
        "status": {
            "presets": [],
            "editor_lines": ["old1", "old2"],
            "rotation": {"enabled": False, "interval_seconds": 30, "mode": "sequential"},
        },
        "advanced": {"minimum_interval_seconds": 5},
    })
    assert data["status"]["editor_messages"] == ["old1", "old2", "", ""]
    assert "editor_lines" not in data["status"]
