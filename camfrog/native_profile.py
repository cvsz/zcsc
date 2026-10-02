from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NativeProfile:
    name: str
    sha256: str
    architecture: str
    image_base: int
    anchors: dict[str, int]
    classes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["image_base"] = hex(self.image_base)
        data["anchors"] = {k: hex(v) for k, v in self.anchors.items()}
        return data


KNOWN_PROFILES: dict[str, NativeProfile] = {
    "0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06": NativeProfile(
        name="Camfrog x64 2026-08-28 status profile",
        sha256="0b744602c004536dcf81e9965e8cb17358eb276b3876a1e70c50f72777c27e06",
        architecture="x86-64",
        image_base=0x140000000,
        anchors={
            # Static-analysis RVAs only. They are diagnostic markers, not invoked.
            "Messages.ChangeStatus.vtable_assign": 0x0273D93,
            "CSToNet_SetSelfStatus.ctor": 0x0782AB0,
            "CSToNet_SetSelfStatus.vtable_assign": 0x0782AF1,
            "CSNet_SetSelfStatus.ctor": 0x0782C30,
            "CSNet_SetSelfStatus.vtable_assign": 0x0782C7C,
            "CSNet_ChangeStatusEx.ctor_a": 0x0527D70,
            "CSNet_ChangeStatusEx.vtable_assign_a": 0x0527DB4,
            "CSNet_ChangeStatusEx.ctor_b": 0x078BE30,
            "CSPacket020401.text_status.serializer": 0x1E61C40,
            "CSPacket020402.custom_status.serializer": 0x1E813B0,
        },
        classes=("CComboBoxTS", "CEdit4ComboInnerTS", "CButtonStatusTS"),
    ),
}


def sha256_file(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identify_profile(executable: str) -> tuple[NativeProfile | None, str]:
    path = Path(executable)
    if not executable or not path.is_file():
        return None, ""
    digest = sha256_file(path)
    return KNOWN_PROFILES.get(digest.lower()), digest.lower()
