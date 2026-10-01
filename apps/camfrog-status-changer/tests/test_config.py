from system.config_store import ConfigStore, DEFAULT_CONFIG

def test_four_message_slots():
    c=ConfigStore.validate(DEFAULT_CONFIG.copy())
    assert len(c["status"]["editor_messages"])==4
