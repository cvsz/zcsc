#!/usr/bin/env python3
"""Run the single supported, staged Windows test and executable build."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import struct
import tempfile
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.write_release_manifest import sha256_file, write_manifest  # noqa: E402

APP_NAME = "CamfrogStatusChanger"
COMPILE_TARGETS = (
    "app.py",
    "automation",
    "camfrog",
    "system",
    "ui",
    "scripts",
    "version.py",
    "self_test.py",
)
CommandRunner = Callable[[Sequence[str], Path], None]


def build_command(
    root: Path,
    dist_dir: Path,
    work_dir: Path,
    spec_dir: Path,
) -> list[str]:
    root = Path(root)
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--exclude-module",
        "PIL._avif",
        "--name",
        APP_NAME,
        "--icon",
        str(root / "app.ico"),
        "--add-data",
        f"{root / 'bad_word_starters.json'};.",
        "--add-data",
        f"{root / 'app.ico'};.",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        str(root / "app.py"),
    ]


def run_command(command: Sequence[str], cwd: Path) -> None:
    print(f"$ {subprocess.list2cmdline(list(command))}")
    subprocess.run(list(command), check=True, cwd=str(cwd))


def _remove_staging_directory(path: Path, root: Path) -> None:
    root_resolved = root.resolve()
    if path.is_symlink():
        raise RuntimeError(f"Refusing to remove a staging symlink: {path}")
    resolved = path.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise RuntimeError(f"Refusing to remove a path outside the checkout: {path}")
    if path.exists():
        shutil.rmtree(path)


def _publish_pair(
    staged_executable: Path,
    staged_manifest: Path,
    output_directory: Path,
) -> None:
    manifest = json.loads(staged_manifest.read_text(encoding="utf-8"))
    expected_hash = sha256_file(staged_executable)
    if manifest.get("sha256") != expected_hash:
        raise ValueError("Staged release manifest does not match the executable")

    output_directory.mkdir(parents=True, exist_ok=True)
    output_executable = output_directory / staged_executable.name
    output_manifest = output_directory / "release-manifest.json"
    with tempfile.TemporaryDirectory(
        prefix=f".{APP_NAME}-publish-", dir=output_directory
    ) as temporary_name:
        temporary_directory = Path(temporary_name)
        temporary_executable = temporary_directory / staged_executable.name
        temporary_manifest = temporary_directory / "release-manifest.json"
        previous_executable = temporary_directory / "previous.exe"
        shutil.copy2(staged_executable, temporary_executable)
        shutil.copy2(staged_manifest, temporary_manifest)
        if sha256_file(temporary_executable) != manifest["sha256"]:
            raise ValueError("Copied executable failed SHA-256 verification")
        if output_executable.is_file():
            shutil.copy2(output_executable, previous_executable)

        executable_published = False
        try:
            os.replace(temporary_executable, output_executable)
            executable_published = True
            os.replace(temporary_manifest, output_manifest)
        except OSError:
            if executable_published:
                if previous_executable.is_file():
                    os.replace(previous_executable, output_executable)
                else:
                    output_executable.unlink(missing_ok=True)
            raise


def validate_build_interpreter() -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError(
            "Windows release builds require CPython 3.12 x64; "
            f"current interpreter is {sys.version.split()[0]} at {sys.executable}. "
            "Use: py -3.12 scripts\\build_windows.py"
        )
    if struct.calcsize("P") != 8:
        raise RuntimeError(
            "Windows release builds require 64-bit CPython 3.12. "
            f"Current interpreter is {struct.calcsize('P') * 8}-bit."
        )


def build(root: Path = ROOT, runner: CommandRunner = run_command) -> tuple[Path, Path]:
    root = Path(root).resolve()
    if sys.platform != "win32":
        raise RuntimeError("The Camfrog executable build requires Windows")
    validate_build_interpreter()

    runner(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "-r",
            str(root / "requirements-build.lock"),
        ],
        root,
    )
    runner(
        [sys.executable, "-m", "pip_audit", "-r", str(root / "requirements-build.lock")],
        root,
    )
    runner([sys.executable, "-m", "pytest", "-q"], root)
    runner(
        [sys.executable, "-m", "compileall", "-q", *COMPILE_TARGETS],
        root,
    )

    staged_dist = root / ".tmp" / f"{APP_NAME}-dist"
    work_dir = root / "build" / f"{APP_NAME}-work"
    spec_dir = root / ".tmp" / f"{APP_NAME}-spec"
    for directory in (staged_dist, work_dir, spec_dir):
        _remove_staging_directory(directory, root)
        directory.mkdir(parents=True, exist_ok=True)

    runner(build_command(root, staged_dist, work_dir, spec_dir), root)
    staged_executable = staged_dist / f"{APP_NAME}.exe"
    if not staged_executable.is_file():
        raise FileNotFoundError(f"PyInstaller did not create {staged_executable}")

    staged_manifest = staged_dist / "release-manifest.json"
    write_manifest(staged_executable, staged_manifest, version_file=root / "version.py")
    _publish_pair(staged_executable, staged_manifest, root / "dist")

    for directory in (staged_dist, work_dir, spec_dir):
        _remove_staging_directory(directory, root)
    return root / "dist" / f"{APP_NAME}.exe", root / "dist" / "release-manifest.json"


def main() -> int:
    try:
        executable, manifest = build()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"[ERROR] Windows build failed: {error}", file=sys.stderr)
        return 1
    print("BUILD SUCCESS")
    print(f"EXE:      {executable}")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
