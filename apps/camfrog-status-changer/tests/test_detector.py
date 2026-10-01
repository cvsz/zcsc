from camfrog import detector

def test_preferred_path_is_first():
    assert detector.KNOWN_PATHS[0] == detector.PREFERRED_PATH
    assert "Camfrog Video Chat.exe" in str(detector.PREFERRED_PATH)
