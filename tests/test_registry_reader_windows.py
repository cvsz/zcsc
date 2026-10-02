import builtins
import sys
from types import SimpleNamespace

import camfrog.registry_status as registry_status


class _FakeKey:
    def __init__(self, entry):
        self.entry = entry

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_READ = 0
    KEY_WOW64_64KEY = 0
    KEY_WOW64_32KEY = 0

    def __init__(self, tree):
        self.tree = {path.casefold(): entry for path, entry in tree.items()}

    def OpenKey(self, _hive, path, _reserved, _access):
        try:
            return _FakeKey(self.tree[path.casefold()])
        except KeyError as exc:
            raise FileNotFoundError(path) from exc

    @staticmethod
    def QueryInfoKey(key):
        return len(key.entry.get("children", [])), len(key.entry.get("values", [])), 0

    @staticmethod
    def EnumValue(key, index):
        return key.entry.get("values", [])[index]

    @staticmethod
    def EnumKey(key, index):
        return key.entry.get("children", [])[index]


def _fake_registry():
    root = r"Software\Camfrog"
    return _FakeWinreg(
        {
            root: {"children": ["StatusHistory", "SessionCustomStatus", "CredentialsStatus"]},
            root + r"\StatusHistory": {
                "values": [
                    ("StatusList", "Example Registry Status", 1),
                    ("OAuthCustomStatus", "Do not import this credential value", 1),
                ]
            },
            root + r"\SessionCustomStatus": {
                "values": [("StatusHistory", "Private Session Status", 1)]
            },
            root + r"\CredentialsStatus": {
                "values": [("CustomStatus", "Private Credential Status", 1)]
            },
        }
    )


def test_reader_import_and_non_windows_path_do_not_require_winreg(monkeypatch):
    real_import = builtins.__import__

    def no_winreg_import(name, *args, **kwargs):
        if name == "winreg":
            raise AssertionError("winreg must not be imported on Linux")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_winreg_import)
    monkeypatch.setattr(registry_status, "os", SimpleNamespace(name="posix"))

    result = registry_status.read_camfrog_custom_statuses()

    assert result.scanned_keys == 0
    assert result.statuses == []


def test_reader_uses_fake_winreg_and_excludes_sensitive_keys_and_value_names(monkeypatch):
    monkeypatch.setattr(registry_status, "os", SimpleNamespace(name="nt"))
    monkeypatch.setitem(sys.modules, "winreg", _fake_registry())

    result = registry_status.read_camfrog_custom_statuses()

    assert result.statuses == ["Example Registry Status"]
    assert result.scanned_keys == 2
    assert result.candidate_values == 1
    assert all("Session" not in item.source for item in result.history)
    assert all("Credentials" not in item.source for item in result.history)
