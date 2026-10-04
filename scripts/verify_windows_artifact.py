#!/usr/bin/env python3
"""Verify a built Windows executable and its release manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.write_release_manifest import sha256_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION_RE = re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.MULTILINE)
IMAGE_FILE_MACHINE_AMD64 = 0x8664
PE32_PLUS_MAGIC = 0x20B


def read_source_version(path: Path) -> str:
    match = VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"VERSION not found in {path}")
    return match.group(1)


def inspect_pe(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("Artifact is not a DOS/PE executable")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 26 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("Artifact has no valid PE signature")
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    optional_magic = struct.unpack_from("<H", data, pe_offset + 24)[0]
    if machine != IMAGE_FILE_MACHINE_AMD64:
        raise ValueError(f"Expected x64 machine 0x8664, got 0x{machine:04x}")
    if optional_magic != PE32_PLUS_MAGIC:
        raise ValueError(f"Expected PE32+ optional header 0x20b, got 0x{optional_magic:04x}")
    return {
        "machine": f"0x{machine:04x}",
        "pe_format": "PE32+",
    }


def verify(
    artifact: Path,
    manifest_path: Path,
    *,
    version_file: Path,
) -> dict[str, object]:
    if not artifact.is_file():
        raise FileNotFoundError(f"Missing executable artifact: {artifact}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing release manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_version = read_source_version(version_file)
    actual_hash = sha256_file(artifact)
    actual_size = artifact.stat().st_size

    checks = {
        "artifact_name": manifest.get("artifact") == artifact.name,
        "version": manifest.get("version") == expected_version,
        "sha256": manifest.get("sha256") == actual_hash,
        "size_bytes": manifest.get("size_bytes") == actual_size,
        "platform": manifest.get("platform") == "windows-x64",
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError("Release manifest verification failed: " + ", ".join(failed))

    pe = inspect_pe(artifact)
    return {
        "verified": True,
        "artifact": artifact.name,
        "version": expected_version,
        "sha256": actual_hash,
        "size_bytes": actual_size,
        "platform": "windows-x64",
        **pe,
        "git_sha": os.environ.get("GITHUB_SHA", ""),
        "verified_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT / "dist" / "CamfrogStatusChanger.exe",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "dist" / "release-manifest.json",
    )
    parser.add_argument(
        "--version-file",
        type=Path,
        default=ROOT / "version.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "windows-artifact-verification.json",
    )
    args = parser.parse_args()
    try:
        report = verify(
            args.artifact,
            args.manifest,
            version_file=args.version_file,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] Artifact verification failed: {exc}")
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
