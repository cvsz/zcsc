from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts.diagnose_camfrog_runtime import (
    classify_process,
    read_config_path,
    redact_user_profile,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class Process:
    def __init__(self, pid: int, name: str, executable: str):
        self.pid = pid
        self.info = {"pid": pid, "name": name, "exe": executable}

    def name(self):
        return self.info["name"]

    def exe(self):
        return self.info["exe"]


def test_diagnostics_never_accepts_cef_even_when_configured_path_matches():
    configured = r"C:\Users\TestUser\AppData\Local\Camfrog\camfrog_cef.exe"
    row = classify_process(
        Process(1440, "camfrog_cef.exe", configured),
        configured,
    )
    assert row["eligible"] is False
    assert row["role"] == "camfrog-cef-helper"


def test_read_config_path_does_not_create_or_repair_configuration(tmp_path):
    path = tmp_path / "CamfrogStatusChanger" / "config.json"
    assert read_config_path(path) == ("missing", "")
    assert not path.exists()

    path.parent.mkdir(parents=True)
    path.write_text("{invalid json", encoding="utf-8")
    original = path.read_bytes()
    assert read_config_path(path) == ("invalid", "")
    assert path.read_bytes() == original
    assert list(path.parent.glob("config.corrupt-*.json")) == []


def test_read_config_path_reads_executable_without_mutation(tmp_path):
    path = tmp_path / "CamfrogStatusChanger" / "config.json"
    path.parent.mkdir(parents=True)
    configured = r"C:\Users\TestUser\AppData\Local\Camfrog\Camfrog Video Chat.exe"
    path.write_text(json.dumps({"camfrog": {"executable": configured}}), encoding="utf-8")
    assert read_config_path(path) == ("configured", configured)
    assert json.loads(path.read_text(encoding="utf-8"))["camfrog"]["executable"] == configured


def test_diagnostic_redacts_user_profile():
    path = r"C:\Users\TestUser\AppData\Local\Camfrog\Camfrog Video Chat.exe"
    redacted = redact_user_profile(path)
    assert "TestUser" not in redacted
    assert r"\Users\<USER>\AppData" in redacted


def test_cli_invocation_bootstraps_repo_root_and_does_not_create_missing_config(tmp_path):
    env = os.environ.copy()
    env["APPDATA"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "diagnose_camfrog_runtime.py")],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    output = json.loads(result.stdout)
    assert output["config_status"] == "missing"
    assert not (tmp_path / "CamfrogStatusChanger" / "config.json").exists()


def test_diagnostics_classifies_real_client_and_ignores_helpers(monkeypatch):
    monkeypatch.setattr("scripts.diagnose_camfrog_runtime.os.getpid", lambda: 9000)
    configured = r"C:\Users\TestUser\AppData\Local\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"

    client = classify_process(
        Process(2192, "Camfrog Video Chat.exe", configured),
        configured,
    )
    cef = classify_process(
        Process(1440, "camfrog_cef.exe", r"C:\Users\TestUser\AppData\Local\Programs\Camfrog Video Chat\camfrog_cef.exe"),
        configured,
    )
    zcsc = classify_process(
        Process(16508, "CamfrogStatusChanger.exe", r"C:\Users\TestUser\zcsc\dist\CamfrogStatusChanger.exe"),
        configured,
    )

    assert client["eligible"] is True
    assert client["role"] == "camfrog-client"
    assert cef["eligible"] is False
    assert cef["role"] == "camfrog-cef-helper"
    assert zcsc["eligible"] is False
    assert zcsc["role"] == "zcsc"


def test_diagnostics_rejects_same_name_from_wrong_path_when_configured(monkeypatch):
    monkeypatch.setattr("scripts.diagnose_camfrog_runtime.os.getpid", lambda: 9000)
    configured = r"C:\Camfrog\Camfrog Video Chat.exe"

    row = classify_process(
        Process(42, "Camfrog Video Chat.exe", r"D:\Other\Camfrog Video Chat.exe"),
        configured,
    )

    assert row["eligible"] is False
    assert "path differs" in row["reason"]
