from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    script_path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_build_entrypoints_share_the_python_builder() -> None:
    main_entrypoint = (ROOT / "build_exe.bat").read_text(encoding="utf-8")
    compatibility_entrypoint = (ROOT / "build_exe_fixed.bat").read_text(encoding="utf-8")

    assert "scripts\\build_windows.py" in main_entrypoint
    assert "build_exe.bat" in compatibility_entrypoint
    assert "PyInstaller" not in main_entrypoint + compatibility_entrypoint


def test_windows_workflow_calls_the_same_builder_without_inline_packaging() -> None:
    workflow = (ROOT / ".github/workflows/camfrog-status-changer.yml").read_text(
        encoding="utf-8"
    )

    assert "scripts/build_windows.py" in workflow
    assert "PyInstaller" not in workflow
    assert "release_manifest.ps1" not in workflow


def test_build_command_preserves_paths_with_spaces_and_thai() -> None:
    builder = _load_script("build_windows")
    project_root = Path("C:/work/Camfrog ไทย project")
    dist_dir = project_root / ".tmp" / "staged output"
    work_dir = project_root / "build" / "private work"
    spec_dir = project_root / ".tmp" / "spec files"

    command = builder.build_command(project_root, dist_dir, work_dir, spec_dir)

    assert "--add-data" in command
    assert str(project_root / "bad_word_starters.json") + ";." in command
    assert str(project_root / "app.ico") + ";." in command
    assert str(dist_dir) == command[command.index("--distpath") + 1]
    assert str(work_dir) == command[command.index("--workpath") + 1]
    assert str(spec_dir) == command[command.index("--specpath") + 1]


def test_release_manifest_supports_unicode_paths_and_hashes_the_artifact(tmp_path: Path) -> None:
    manifest_writer = _load_script("write_release_manifest")
    artifact = tmp_path / "Camfrog build ไทย" / "CamfrogStatusChanger.exe"
    manifest_path = artifact.parent / "release-manifest.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"verified windows executable placeholder")

    manifest = manifest_writer.write_manifest(
        artifact,
        manifest_path,
        version="2.2.5-test",
        built_utc="2026-10-02T00:00:00Z",
    )

    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    assert manifest["size_bytes"] == artifact.stat().st_size
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"])
    assert manifest["artifact"] == artifact.name


def test_runtime_dependency_lock_is_hash_pinned_for_direct_dependencies() -> None:
    source_lines = (ROOT / "requirements.in").read_text(encoding="utf-8").splitlines()
    lock = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    direct_requirements = [
        line.strip()
        for line in source_lines
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert direct_requirements
    for requirement in direct_requirements:
        package, version_and_marker = requirement.split("==", maxsplit=1)
        version = version_and_marker.split(";", maxsplit=1)[0].strip()
        match = re.search(
            rf"(?ims)^{re.escape(package)}=={re.escape(version)}(?:\s*;|\b).*?(?=^[^\s#]|\Z)",
            lock,
            flags=re.IGNORECASE,
        )
        assert match is not None, f"{package}=={version} is missing from requirements.txt"
        assert "--hash=sha256:" in match.group(0), f"{package} is not hash-pinned"


def test_build_dependency_lock_is_hash_pinned_and_contains_packaging_tools() -> None:
    lock = (ROOT / "requirements-build.lock").read_text(encoding="utf-8")
    for package in ("pytest", "pyinstaller", "pip-audit"):
        match = re.search(
            rf"(?ims)^{package}==[^\n]+.*?(?=^[^\s#]|\Z)",
            lock,
        )
        assert match is not None, f"{package} is missing from the build lock"
        assert "--hash=sha256:" in match.group(0), f"{package} is not hash-pinned"


def test_every_runtime_and_build_lock_entry_has_sha256_hashes() -> None:
    for lock_name in ("requirements.txt", "requirements-build.lock"):
        lock = (ROOT / lock_name).read_text(encoding="utf-8")
        entries = list(
            re.finditer(r"(?m)^[A-Za-z0-9_.-]+==[^\n]+", lock)
        )

        assert entries, f"{lock_name} has no pinned package entries"
        for index, entry in enumerate(entries):
            end = entries[index + 1].start() if index + 1 < len(entries) else len(lock)
            package_block = lock[entry.start() : end]
            assert re.search(r"--hash=sha256:[0-9a-f]{64}", package_block), (
                f"{entry.group(0)} in {lock_name} has no SHA-256 wheel/source hash"
            )


def test_fake_windows_build_audits_locked_deps_and_preserves_adjacent_build_files(
    monkeypatch, tmp_path: Path
) -> None:
    builder = _load_script("build_windows")
    root = tmp_path / "Camfrog Build ไทย"
    root.mkdir()
    (root / "version.py").write_text('VERSION = "2.2.5-test"\n', encoding="utf-8")
    build_directory = root / "build"
    build_directory.mkdir()
    adjacent_camfrog = build_directory / "Camfrog Video Chat.exe"
    adjacent_camfrog.write_bytes(b"preserve this unrelated analysis artifact")
    commands: list[list[str]] = []

    def fake_runner(command, cwd: Path) -> None:
        commands.append(list(command))
        if "PyInstaller" in command:
            output_dir = Path(command[command.index("--distpath") + 1])
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "CamfrogStatusChanger.exe").write_bytes(b"fake executable")

    monkeypatch.setattr(builder.sys, "platform", "win32")
    executable, manifest_path = builder.build(root, fake_runner)

    assert any(command[1:3] == ["-m", "pip_audit"] for command in commands)
    assert commands[0][1:5] == ["-m", "pip", "install", "--require-hashes"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == manifest["sha256"]
    assert manifest["size_bytes"] == executable.stat().st_size
    assert adjacent_camfrog.read_bytes() == b"preserve this unrelated analysis artifact"
    assert not (root / ".tmp" / "CamfrogStatusChanger-dist").exists()


def test_manifest_publish_failure_restores_the_previous_executable(
    monkeypatch, tmp_path: Path
) -> None:
    builder = _load_script("build_windows")
    manifest_writer = _load_script("write_release_manifest")
    output = tmp_path / "dist with ไทย"
    output.mkdir()
    current_executable = output / "CamfrogStatusChanger.exe"
    current_executable.write_bytes(b"previous executable")
    current_manifest = output / "release-manifest.json"
    old_manifest = manifest_writer.write_manifest(
        current_executable,
        current_manifest,
        version="previous",
        built_utc="2026-10-01T00:00:00Z",
    )

    staging = tmp_path / "staging"
    staging.mkdir()
    staged_executable = staging / "CamfrogStatusChanger.exe"
    staged_executable.write_bytes(b"new executable")
    staged_manifest = staging / "release-manifest.json"
    manifest_writer.write_manifest(
        staged_executable,
        staged_manifest,
        version="next",
        built_utc="2026-10-02T00:00:00Z",
    )

    original_replace = builder.os.replace
    manifest_replace_failed = False

    def fail_first_manifest_replace(source, destination) -> None:
        nonlocal manifest_replace_failed
        if Path(destination) == current_manifest and not manifest_replace_failed:
            manifest_replace_failed = True
            raise OSError("simulated manifest replacement failure")
        original_replace(source, destination)

    monkeypatch.setattr(builder.os, "replace", fail_first_manifest_replace)
    with pytest.raises(OSError, match="simulated manifest replacement failure"):
        builder._publish_pair(staged_executable, staged_manifest, output)

    assert manifest_replace_failed
    assert current_executable.read_bytes() == b"previous executable"
    assert json.loads(current_manifest.read_text(encoding="utf-8")) == old_manifest
