from camfrog.registry_status import extract_status_strings


def test_binary_like_registry_dump_does_not_import_garbage():
    values = [
        "Example Status One", "Example Organization", "Busy", "Available",
        "1050", "0", "1366", "639", "1790823392",
        "00000000000000000000000000000000", "fixture@example.invalid",
        "--REDACTED--!@#%", "=}W", "5X.g",
    ]
    result = []
    for value in values:
        result.extend(extract_status_strings(value))
    assert "Example Status One" in result
    assert "Example Organization" in result
    assert "Busy" in result
    assert "Available" in result
    assert "1050" not in result
    assert "fixture@example.invalid" not in result
    assert "00000000000000000000000000000000" not in result
