from camfrog.registry_status import _clean_status


def test_accept_human_statuses():
    assert _clean_status("Example Status One") == "Example Status One"
    assert _clean_status("Example Organization") == "Example Organization"
    assert _clean_status("Busy") == "Busy"
    assert _clean_status("Available") == "Available"


def test_reject_metadata_and_sensitive_looking_values():
    bad = [
        "1050", "0", "1366", "1790823392",
        "00000000000000000000000000000000",
        "fixture@example.invalid", "--REDACTED--!@#%", "--NOT-REAL--!@#%",
    ]
    for value in bad:
        assert _clean_status(value) is None
