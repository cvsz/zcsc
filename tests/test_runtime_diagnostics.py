from __future__ import annotations

from types import SimpleNamespace

from scripts.diagnose_camfrog_runtime import classify_process


class Process:
    def __init__(self, pid: int, name: str, executable: str):
        self.pid = pid
        self.info = {"pid": pid, "name": name, "exe": executable}

    def name(self):
        return self.info["name"]

    def exe(self):
        return self.info["exe"]


def test_diagnostics_classifies_real_client_and_ignores_helpers(monkeypatch):
    monkeypatch.setattr("scripts.diagnose_camfrog_runtime.os.getpid", lambda: 9000)
    configured = r"C:\Users\cvsz.ZEAZ\AppData\Local\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"

    client = classify_process(
        Process(2192, "Camfrog Video Chat.exe", configured),
        configured,
    )
    cef = classify_process(
        Process(1440, "camfrog_cef.exe", r"C:\Users\cvsz.ZEAZ\AppData\Local\Programs\Camfrog Video Chat\camfrog_cef.exe"),
        configured,
    )
    zcsc = classify_process(
        Process(16508, "CamfrogStatusChanger.exe", r"C:\Users\cvsz.ZEAZ\zcsc\dist\CamfrogStatusChanger.exe"),
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
