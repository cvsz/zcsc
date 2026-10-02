import json
import sys
from pathlib import Path

import registry_history_dump
from camfrog.registry_status import RegistryHistoryItem, RegistryStatusResult


def _result(*, scanned_keys=1, statuses=None):
    rows = statuses or [
        RegistryHistoryItem(
            "Example custom status",
            r"HKCU\Software\Camfrog\StatusHistory [StatusList]",
            "StatusList",
            3,
        )
    ]
    return RegistryStatusResult(
        [row.text for row in rows],
        [row.source for row in rows],
        scanned_keys=scanned_keys,
        candidate_values=len(rows),
        history=rows,
    )


def _install_dump(monkeypatch, tmp_path, result):
    output_dir = tmp_path / "new" / "CamfrogStatusChanger"

    class FakeConfigStore:
        def __init__(self):
            self.dir = output_dir

    monkeypatch.setattr(registry_history_dump, "ConfigStore", FakeConfigStore)
    monkeypatch.setattr(registry_history_dump, "read_camfrog_custom_statuses", lambda: result)
    monkeypatch.setattr(sys, "argv", ["registry_history_dump.py"])
    return output_dir


def test_dump_creates_missing_store_directory_and_writes_json(monkeypatch, tmp_path, capsys):
    output_dir = _install_dump(monkeypatch, tmp_path, _result())

    assert registry_history_dump.main() == 0

    output_path = output_dir / "camfrog-history-sources-safe.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["scanned_keys"] == 1
    assert payload["statuses"][0]["text"] == "Example custom status"
    assert capsys.readouterr().out.strip() == str(output_path)


def test_dump_returns_nonzero_and_does_not_write_when_no_registry_keys_scanned(
    monkeypatch, tmp_path, capsys
):
    output_dir = _install_dump(monkeypatch, tmp_path, _result(scanned_keys=0, statuses=[]))

    result = registry_history_dump.main()

    assert result != 0
    assert "no registry keys were scanned" in capsys.readouterr().err.casefold()
    assert not (output_dir / "camfrog-history-sources-safe.json").exists()


def test_dump_catches_registry_scan_failure(monkeypatch, tmp_path, capsys):
    output_dir = _install_dump(monkeypatch, tmp_path, _result())

    def fail_scan():
        raise PermissionError("registry access denied")

    monkeypatch.setattr(registry_history_dump, "read_camfrog_custom_statuses", fail_scan)

    assert registry_history_dump.main() != 0
    assert "registry scan failed" in capsys.readouterr().err.casefold()
    assert not output_dir.exists()


def test_dump_catches_storage_initialization_failure(monkeypatch, capsys):
    class FailingConfigStore:
        def __init__(self):
            raise PermissionError("storage unavailable")

    monkeypatch.setattr(registry_history_dump, "ConfigStore", FailingConfigStore)
    monkeypatch.setattr(sys, "argv", ["registry_history_dump.py"])

    assert registry_history_dump.main() != 0
    assert "could not initialize registry dump storage" in capsys.readouterr().err.casefold()


def test_dump_catches_output_write_failure(monkeypatch, tmp_path, capsys):
    _install_dump(monkeypatch, tmp_path, _result())
    original_write_text = Path.write_text

    def fail_output_write(path, *args, **kwargs):
        if path.name == "camfrog-history-sources-safe.json":
            raise PermissionError("output denied")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_output_write)

    assert registry_history_dump.main() != 0
    assert "could not write" in capsys.readouterr().err.casefold()


def test_redaction_is_opt_in_and_covers_all_dump_text_fields(monkeypatch, tmp_path):
    private_text = "Contact alice@example.invalid, +1 (555) 123-4567, https://example.invalid/a"
    row = RegistryHistoryItem(
        private_text,
        rf"HKCU\Software\Camfrog\{private_text}",
        "alice@example.invalid",
        3,
    )
    output_dir = _install_dump(monkeypatch, tmp_path, _result(statuses=[row]))
    output_path = output_dir / "camfrog-history-sources-safe.json"

    assert registry_history_dump.main() == 0
    unredacted = output_path.read_text(encoding="utf-8")
    assert "alice@example.invalid" in unredacted
    assert "+1 (555) 123-4567" in unredacted
    assert "https://example.invalid/a" in unredacted

    monkeypatch.setattr(sys, "argv", ["registry_history_dump.py", "--redact"])
    assert registry_history_dump.main() == 0
    redacted = output_path.read_text(encoding="utf-8")
    assert "alice@example.invalid" not in redacted
    assert "+1 (555) 123-4567" not in redacted
    assert "https://example.invalid/a" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_URL]" in redacted
