from ui.dashboard import windows_path

def test_windows_path_normalizes_slashes():
    assert windows_path("C:/Users/example/AppData/Local/Programs/Camfrog Video Chat/Camfrog Video Chat.exe") == r"C:\Users\example\AppData\Local\Programs\Camfrog Video Chat\Camfrog Video Chat.exe"
