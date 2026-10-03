from pathlib import Path

from camfrog.registry_status import extract_status_strings


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry_history"


def _load_hex_fixture(name):
    encoded = (FIXTURE_DIR / name).read_text(encoding="ascii")
    return bytes.fromhex(encoded)


def test_binary_fixture_carves_utf16_with_odd_metadata_alignment():
    blob = _load_hex_fixture("utf16_odd_alignment.hex")

    values = extract_status_strings(blob, value_type=3)

    assert values == ["Morning Friends", "Coffee Break"]


def test_binary_fixture_keeps_complete_ascii_entry_and_drops_truncated_tail():
    blob = _load_hex_fixture("ascii_truncated_tail.hex")

    values = extract_status_strings(blob, value_type=3)

    assert values == ["History Entry"]


def test_binary_fixture_drops_truncated_utf16le_tail():
    blob = _load_hex_fixture("utf16_truncated_tail.hex")

    values = extract_status_strings(blob, value_type=3)

    assert values == ["Complete Entry"]
