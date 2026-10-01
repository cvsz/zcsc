from camfrog import detector


def test_preferred_path_is_first():
    assert detector.KNOWN_PATHS[0] == detector.PREFERRED_PATH
    assert "Camfrog Video Chat.exe" in str(detector.PREFERRED_PATH)


def test_status_changer_process_is_not_camfrog():
    assert not detector._is_camfrog_process_info({"pid": 100, "name": "CamfrogStatusChanger.exe", "exe": r"C:\Tools\CamfrogStatusChanger.exe"}, current_pid=200)


def test_real_camfrog_process_is_detected():
    assert detector._is_camfrog_process_info({"pid": 100, "name": "Camfrog Video Chat.exe", "exe": r"C:\Users\cvsz\AppData\Local\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"}, current_pid=200)


def test_current_pid_is_excluded():
    assert not detector._is_camfrog_process_info({"pid": 100, "name": "Camfrog Video Chat.exe", "exe": r"C:\Camfrog Video Chat.exe"}, current_pid=100)
