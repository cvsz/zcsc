from system.config_store import DEFAULT_CONFIG


def test_status_commit_and_legacy_fallback_defaults():
    assert DEFAULT_CONFIG["target"]["background_enabled"] is True
    assert DEFAULT_CONFIG["advanced"]["fallback_enabled"] is False
    assert "background_only" not in DEFAULT_CONFIG["advanced"]
