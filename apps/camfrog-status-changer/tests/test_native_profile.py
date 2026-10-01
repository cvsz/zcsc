from camfrog.native_profile import KNOWN_PROFILES


def test_known_profile_contains_status_anchors():
    profile = KNOWN_PROFILES["0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06"]
    assert profile.architecture == "x86-64"
    assert profile.anchors["CSToNet_SetSelfStatus.ctor"] == 0x0782AB0
    assert profile.anchors["CSPacket020401.text_status.serializer"] == 0x1E61C40
    assert "CComboBoxTS" in profile.classes
    assert "CButtonStatusTS" in profile.classes
