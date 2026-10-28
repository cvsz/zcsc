import camfrog.detector as detector


def test_preferred_path_wins(monkeypatch, tmp_path):
    preferred = tmp_path / 'Camfrog Video Chat.exe'
    preferred.write_bytes(b'MZ')
    monkeypatch.setattr(detector, 'PREFERRED_PATH', preferred)
    monkeypatch.setattr(detector, 'KNOWN_PATHS', [preferred])
    monkeypatch.setattr(detector, 'find_processes', lambda: (_ for _ in ()).throw(AssertionError('process scan should not run')))
    assert detector.discover_executable() == str(preferred)


def test_process_fallback_when_preferred_missing(monkeypatch, tmp_path):
    preferred = tmp_path / 'missing.exe'
    monkeypatch.setattr(detector, 'PREFERRED_PATH', preferred)
    monkeypatch.setattr(detector, 'KNOWN_PATHS', [preferred])

    class P:
        def exe(self):
            return r'C:\\Other\\Camfrog Video Chat.exe'

    monkeypatch.setattr(detector, 'find_processes', lambda: [P()])
    assert detector.discover_executable() == r'C:\\Other\\Camfrog Video Chat.exe'


def test_process_scan_excludes_manager_and_similarly_named_helpers(monkeypatch):
    class Process:
        def __init__(self, pid, name, executable):
            self.pid = pid
            self.info = {"pid": pid, "name": name, "exe": executable}

    processes = [
        Process(1, "CamfrogStatusChanger.exe", r"C:\\apps\\CamfrogStatusChanger.exe"),
        Process(2, "CamfrogAccountHelper.exe", r"C:\\apps\\CamfrogAccountHelper.exe"),
        Process(3, "Camfrog Video Chat.exe", r"C:\\Camfrog\\Camfrog Video Chat.exe"),
        Process(4, "Camfrog.exe", r"C:\\Camfrog\\Camfrog.exe"),
    ]
    monkeypatch.setattr(detector.psutil, "process_iter", lambda _attrs: processes)

    assert [process.pid for process in detector.find_processes()] == [3, 4]


def test_configured_executable_requires_exact_normalized_path(monkeypatch):
    class Process:
        def __init__(self, pid, executable):
            self.pid = pid
            self.info = {"pid": pid, "name": "Camfrog Video Chat.exe", "exe": executable}

    processes = [
        Process(1, r"C:\\Program Files\\Camfrog\\Camfrog Video Chat.exe"),
        Process(2, r"D:\\Other\\Camfrog Video Chat.exe"),
        Process(3, r"C:\\apps\\CamfrogStatusChanger.exe"),
    ]
    monkeypatch.setattr(detector.psutil, "process_iter", lambda _attrs: processes)

    found = detector.find_processes(r"c:/program files/camfrog/Camfrog Video Chat.exe")
    assert [process.pid for process in found] == [1]


def test_configured_path_never_overrides_client_executable_allowlist(monkeypatch):
    class Process:
        def __init__(self, pid, name, executable):
            self.pid = pid
            self.info = {"pid": pid, "name": name, "exe": executable}

        def is_running(self):
            return True

        def exe(self):
            return self.info["exe"]

        def name(self):
            return self.info["name"]

    helper = Process(21, "camfrog_cef.exe", r"C:\Camfrog\camfrog_cef.exe")
    non_exe = Process(22, "Camfrog Video Chat.com", r"C:\Camfrog\Camfrog Video Chat.com")
    monkeypatch.setattr(detector.os, "getpid", lambda: 999)
    monkeypatch.setattr(detector.psutil, "process_iter", lambda _attrs: [helper, non_exe])
    monkeypatch.setattr(
        detector.psutil,
        "Process",
        lambda pid: helper if pid == 21 else non_exe,
    )

    assert detector.find_processes(r"C:\Camfrog\camfrog_cef.exe") == []
    assert detector.find_process_by_pid(21, r"C:\Camfrog\camfrog_cef.exe") is None
    assert detector.find_process_by_pid(22, r"C:\Camfrog\Camfrog Video Chat.com") is None


def test_discover_does_not_guess_between_multiple_running_client_binaries(monkeypatch, tmp_path):
    class Process:
        def __init__(self, executable):
            self.info = {"exe": executable}

        def exe(self):
            return self.info["exe"]

    monkeypatch.setattr(detector, "PREFERRED_PATH", tmp_path / "missing.exe")
    monkeypatch.setattr(detector, "KNOWN_PATHS", [])
    monkeypatch.setattr(
        detector,
        "find_processes",
        lambda: [Process(r"C:\\Camfrog\\Camfrog.exe"), Process(r"D:\\Camfrog\\Camfrog Video Chat.exe")],
    )

    assert detector.discover_executable() == ""



def test_find_process_by_pid_requires_exact_executable(monkeypatch):
    class Process:
        def __init__(self, pid, executable, running=True):
            self.pid = pid
            self.info = {"pid": pid, "name": "Camfrog Video Chat.exe", "exe": executable}
            self._running = running

        def is_running(self):
            return self._running

        def exe(self):
            return self.info["exe"]

        def name(self):
            return self.info["name"]

    selected = Process(77, r"C:\Camfrog\Camfrog Video Chat.exe")
    monkeypatch.setattr(detector.psutil, "Process", lambda pid: selected if pid == 77 else (_ for _ in ()).throw(detector.psutil.NoSuchProcess(pid)))

    assert detector.find_process_by_pid(77, r"c:/camfrog/Camfrog Video Chat.exe") is selected
    assert detector.find_process_by_pid(77, r"D:/Other/Camfrog Video Chat.exe") is None



def test_process_scan_rejects_non_exe_same_stem_and_cef(monkeypatch):
    class Process:
        def __init__(self, pid, name, executable):
            self.pid = pid
            self.info = {"pid": pid, "name": name, "exe": executable}

    processes = [
        Process(10, "Camfrog Video Chat.com", r"C:\fake\Camfrog Video Chat.com"),
        Process(11, "Camfrog.com", r"C:\fake\Camfrog.com"),
        Process(12, "camfrog_cef.exe", r"C:\Camfrog\camfrog_cef.exe"),
        Process(13, "Camfrog Video Chat.exe", r"C:\Camfrog\Camfrog Video Chat.exe"),
    ]
    monkeypatch.setattr(detector.os, "getpid", lambda: 999)
    monkeypatch.setattr(detector.psutil, "process_iter", lambda _attrs: processes)

    assert [process.pid for process in detector.find_processes()] == [13]


def test_process_scan_explicitly_excludes_current_pid(monkeypatch):
    class Process:
        def __init__(self, pid):
            self.pid = pid
            self.info = {
                "pid": pid,
                "name": "Camfrog Video Chat.exe",
                "exe": r"C:\Camfrog\Camfrog Video Chat.exe",
            }

    monkeypatch.setattr(detector.os, "getpid", lambda: 77)
    monkeypatch.setattr(detector.psutil, "process_iter", lambda _attrs: [Process(77), Process(88)])

    assert [process.pid for process in detector.find_processes()] == [88]


def test_find_process_by_pid_rejects_current_process(monkeypatch):
    monkeypatch.setattr(detector.os, "getpid", lambda: 77)
    monkeypatch.setattr(
        detector.psutil,
        "Process",
        lambda _pid: (_ for _ in ()).throw(AssertionError("current process must be rejected before psutil lookup")),
    )

    assert detector.find_process_by_pid(77, r"C:\Camfrog\Camfrog Video Chat.exe") is None
