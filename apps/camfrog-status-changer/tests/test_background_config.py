from system.config_store import DEFAULT_CONFIG


def test_background_defaults_are_non_intrusive():
    assert DEFAULT_CONFIG["target"]["background_enabled"] is True
    assert DEFAULT_CONFIG["advanced"]["background_only"] is True
    assert DEFAULT_CONFIG["advanced"]["fallback_enabled"] is False
