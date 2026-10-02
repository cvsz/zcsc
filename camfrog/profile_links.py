from __future__ import annotations

import webbrowser
from urllib.parse import quote

PROFILE_DIRECTORY_URL = "https://profiles.camfrog.com/en/"
PROFILE_URL_PREFIX = "https://profiles.camfrog.com/en/"
MAX_PROFILE_NICKNAME_LENGTH = 64


def profile_url_for_nickname(nickname: str) -> str:
    """Build an HTTPS URL for one Camfrog nickname path segment."""
    value = str(nickname or "").replace("\x00", "").strip()
    if not value:
        raise ValueError("Enter a Camfrog nickname first.")
    if len(value) > MAX_PROFILE_NICKNAME_LENGTH:
        raise ValueError(f"Camfrog nicknames must be {MAX_PROFILE_NICKNAME_LENGTH} characters or fewer.")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("The nickname cannot contain path separators.")
    return PROFILE_URL_PREFIX + quote(value, safe="")


def open_camfrog_profile(nickname: str) -> bool:
    return bool(webbrowser.open(profile_url_for_nickname(nickname), new=2))


def open_camfrog_profile_directory() -> bool:
    return bool(webbrowser.open(PROFILE_DIRECTORY_URL, new=2))
