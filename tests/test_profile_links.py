import pytest

import camfrog.profile_links as profile_links
from camfrog.profile_links import (
    PROFILE_DIRECTORY_URL,
    open_camfrog_profile,
    open_camfrog_profile_directory,
    profile_url_for_nickname,
)


def test_profile_url_quotes_nickname_as_one_path_component():
    assert profile_url_for_nickname("Example User") == "https://profiles.camfrog.com/en/Example%20User"
    assert profile_url_for_nickname("ชื่อ&you") == "https://profiles.camfrog.com/en/%E0%B8%8A%E0%B8%B7%E0%B9%88%E0%B8%AD%26you"


@pytest.mark.parametrize("nickname", ["", "   ", ".", "..", "a/b", "a\\b"])
def test_profile_url_rejects_empty_or_path_like_nickname(nickname):
    with pytest.raises(ValueError):
        profile_url_for_nickname(nickname)


def test_open_profile_uses_default_browser_in_new_tab(monkeypatch):
    opened = []
    monkeypatch.setattr(profile_links.webbrowser, "open", lambda url, new: opened.append((url, new)) or True)

    assert open_camfrog_profile("A&B") is True
    assert opened == [("https://profiles.camfrog.com/en/A%26B", 2)]


def test_open_profile_directory_uses_the_official_directory_url(monkeypatch):
    opened = []
    monkeypatch.setattr(profile_links.webbrowser, "open", lambda url, new: opened.append((url, new)) or True)

    assert open_camfrog_profile_directory() is True
    assert opened == [(PROFILE_DIRECTORY_URL, 2)]
