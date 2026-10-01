from ui.dashboard import AppUI


def test_title_assignment_guard_redirects_non_callable():
    app = object.__new__(AppUI)
    AppUI.__setattr__(app, "title", object())
    assert "title" not in app.__dict__
    assert "title_label" in app.__dict__
