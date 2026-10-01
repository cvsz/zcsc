from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NativeProfile:
    name: str
    sha256: str
    architecture: str
    image_base: int
    anchors: dict[str, int]
    classes: tuple[str, ...]


KNOWN_PROFILES = {
    "0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06": NativeProfile(
        name="Camfrog x64 2026-08-28 status profile",
        sha256="0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06",
        architecture="x86-64",
        image_base=0x140000000,
        anchors={
            "Messages.ChangeStatus.vtable_assign": 0x0273D93,
            "CSToNet_SetSelfStatus.ctor": 0x0782AB0,
            "CSNet_SetSelfStatus.ctor": 0x0782C30,
            "CSNet_ChangeStatusEx.ctor_a": 0x0527D70,
            "CSNet_ChangeStatusEx.ctor_b": 0x078BE30,
            "CSPacket020401.text_status.serializer": 0x1E61C40,
            "CSPacket020402.custom_status.serializer": 0x1E813B0,
        },
        classes=("CComboBoxTS", "CEdit4ComboInnerTS", "CButtonStatusTS"),
    )
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identify_profile(executable: str):
    path = Path(executable)
    if not executable or not path.is_file():
        return None, ""
    digest = sha256_file(str(path)).lower()
    return KNOWN_PROFILES.get(digest), digest
