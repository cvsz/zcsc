#!/usr/bin/env python3
"""Create the SHA-256 manifest for a Camfrog Status Changer executable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_version(version_file: Path) -> str:
    match = VERSION_RE.search(version_file.read_text(encoding="utf-8"))
    return match.group(1) if match else "unknown"


def write_manifest(
    artifact_path: Path,
    manifest_path: Path,
    *,
    version: str | None = None,
    version_file: Path | None = None,
    built_utc: str | None = None,
) -> dict[str, object]:
    artifact_path = Path(artifact_path)
    manifest_path = Path(manifest_path)
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Missing executable artifact: {artifact_path}")

    project_version = version
    if project_version is None:
        project_version = read_version(version_file or ROOT / "version.py")
    manifest: dict[str, object] = {
        "artifact": artifact_path.name,
        "version": project_version,
        "sha256": sha256_file(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
        "built_utc": built_utc
        or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "platform": "windows-x64",
        "native_profile_mode": "version-gated-static-profile; internal-RVA-invocation-disabled",
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = manifest_path.with_name(f"{manifest_path.name}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, manifest_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT / "dist" / "CamfrogStatusChanger.exe",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "release-manifest.json",
    )
    parser.add_argument("--version-file", type=Path, default=ROOT / "version.py")
    arguments = parser.parse_args()
    manifest = write_manifest(
        arguments.artifact,
        arguments.output,
        version_file=arguments.version_file,
    )
    print(f"Version: {manifest['version']}")
    print(f"SHA256: {manifest['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
