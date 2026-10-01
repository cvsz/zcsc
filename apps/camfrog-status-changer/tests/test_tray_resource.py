from system.tray import resource_path


def test_tray_resource_path_points_to_requested_name():
    assert resource_path("app.ico").name == "app.ico"
