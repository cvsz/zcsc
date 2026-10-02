from camfrog.registry_status import extract_status_strings


def test_carves_utf16_history_from_binary_blob():
    blob = b"\x01\x02" + "Example Status One\x00Example Organization\x00Busy\x00Available\x00".encode("utf-16-le") + b"\x10\x11"
    got = extract_status_strings(blob)
    assert "Example Status One" in got
    assert "Example Organization" in got
    assert "Busy" in got
    assert "Available" in got


def test_does_not_import_numeric_and_email_fragments():
    blob = b"1050\x001366\fixture@example.invalid\x00Available\x00"
    got = extract_status_strings(blob)
    assert "Available" in got
    assert "1050" not in got
    assert "1366" not in got
    assert "fixture@example.invalid" not in got
