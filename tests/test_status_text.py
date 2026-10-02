from status_text import compose_two_lines, comparable_status


def test_two_lines_basic():
    assert compose_two_lines(["text1", "text2"]) == "text1\r\ntext2"


def test_one_line_when_second_empty():
    assert compose_two_lines(["text1", ""]) == "text1"


def test_preserves_blank_first_line_when_second_present():
    assert compose_two_lines(["", "text2"]) == "\r\ntext2"


def test_embedded_newline_inside_field_is_flattened():
    assert compose_two_lines(["a\nb", "c"]) == "a b\r\nc"


def test_deprecated_two_line_helper_preserves_all_four_message_rows():
    assert compose_two_lines(["one", "two", "three", "four"]) == "one\r\ntwo\r\nthree\r\nfour"


def test_comparison_normalizes_crlf_and_lf():
    assert comparable_status("a\r\nb") == comparable_status("a\nb")


def test_comparison_strips_trailing_nuls():
    assert comparable_status("status\x00\x00") == comparable_status("status")


def test_comparison_normalizes_unicode_to_nfc():
    assert comparable_status("e\u0301") == comparable_status("\u00e9")
