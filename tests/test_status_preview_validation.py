from types import SimpleNamespace

from ui.dashboard import AppUI


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeLabel:
    def __init__(self):
        self.text = ""

    def configure(self, *, text):
        self.text = text


class PreviewApp(SimpleNamespace):
    _message_values = AppUI._message_values


def make_preview_app(message, color_template, language="EN"):
    return PreviewApp(
        status_preview_label=FakeLabel(),
        status_message_vars=[FakeVar(message)],
        config_data={"status": {"styles": {"color_template": color_template}}},
        language_var=FakeVar(language),
        random_color_var=FakeVar(True),
        custom_color_var=FakeVar(False),
        custom_color_value=FakeVar("#00C7BE"),
        marquee_var=FakeVar(False),
        marquee_single_character_var=FakeVar(False),
        _marquee_offset=0,
    )


def test_status_preview_reports_invalid_color_template():
    app = make_preview_app("HELLO", "[color={color}][/color]")

    AppUI._refresh_status_preview(app)

    assert "Invalid color template" in app.status_preview_label.text
    assert "HELLO" in app.status_preview_label.text


def test_empty_status_preview_still_reports_invalid_color_template():
    app = make_preview_app("", "{unknown}{text}")

    AppUI._refresh_status_preview(app)

    assert "Invalid color template" in app.status_preview_label.text


def test_thai_status_preview_reports_invalid_color_template_in_thai():
    app = make_preview_app("สวัสดี", "{text}{text}", language="TH")

    AppUI._refresh_status_preview(app)

    assert "เทมเพลตสีไม่ถูกต้อง" in app.status_preview_label.text
