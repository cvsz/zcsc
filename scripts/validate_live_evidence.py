#!/usr/bin/env python3
"""Validate operator-produced RC12 live validation evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GATE_IDS = (
    "server_visible_status",
    "minimized_status",
    "reconnect_persistence",
    "rotation_10_cycles",
    "focus_and_mouse_safety",
    "selector_stability",
    "startup_tray_single_instance",
    "defender_scan",
    "policy_review",
    "controlled_room_e2e",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read_source_version(version_file: Path) -> str:
    text = version_file.read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"VERSION not found in {version_file}")
    return match.group(1)


def validate_evidence(data: dict, *, expected_version: str, expected_git_sha: str | None = None) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}

    version = source.get("version")
    git_sha = source.get("git_sha")
    if version != expected_version:
        errors.append(f"source.version must equal {expected_version}")
    if not isinstance(git_sha, str) or not GIT_SHA_RE.fullmatch(git_sha):
        errors.append("source.git_sha must be a full 40-character lowercase Git SHA")
    elif expected_git_sha and git_sha != expected_git_sha:
        errors.append(f"source.git_sha must equal expected commit {expected_git_sha}")

    camfrog = data.get("camfrog")
    if not isinstance(camfrog, dict):
        errors.append("camfrog must be an object")
        camfrog = {}
    camfrog_sha = camfrog.get("sha256")
    if not isinstance(camfrog_sha, str) or not SHA256_RE.fullmatch(camfrog_sha):
        errors.append("camfrog.sha256 must be a lowercase SHA-256 digest")
    if not str(camfrog.get("executable_path") or "").strip():
        errors.append("camfrog.executable_path is required")

    gates = data.get("gates")
    if not isinstance(gates, list):
        errors.append("gates must be an array")
        gates = []

    seen: dict[str, str] = {}
    for gate in gates:
        if not isinstance(gate, dict):
            errors.append("each gate must be an object")
            continue
        gate_id = gate.get("id")
        status = gate.get("status")
        if gate_id in seen:
            errors.append(f"duplicate gate id: {gate_id}")
            continue
        if gate_id not in EXPECTED_GATE_IDS:
            errors.append(f"unexpected gate id: {gate_id}")
            continue
        if status not in {"pass", "fail", "skip"}:
            errors.append(f"{gate_id}: invalid status {status!r}")
            continue
        seen[gate_id] = status

    missing = [gate for gate in EXPECTED_GATE_IDS if gate not in seen]
    if missing:
        errors.append("missing gates: " + ", ".join(missing))

    not_passed = [gate for gate in EXPECTED_GATE_IDS if seen.get(gate) != "pass"]
    if not_passed:
        errors.append("required gates not passed: " + ", ".join(not_passed))

    declared = data.get("production_gate_passed")
    actual = not not_passed and not missing
    if declared is not actual:
        errors.append(
            f"production_gate_passed must be {str(actual).lower()} for the recorded gate statuses"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--version-file", type=Path, default=ROOT / "version.py")
    parser.add_argument(
        "--expected-git-sha",
        default=None,
        help="Optional exact 40-character commit SHA required in the evidence.",
    )
    args = parser.parse_args()

    try:
        expected_version = read_source_version(args.version_file)
        data = json.loads(args.evidence.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("evidence root must be a JSON object")
        errors = validate_evidence(
            data,
            expected_version=expected_version,
            expected_git_sha=args.expected_git_sha,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if errors:
        print("LIVE VALIDATION FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("LIVE VALIDATION PASSED")
    print(f"version={expected_version}")
    print(f"git_sha={data['source']['git_sha']}")
    print(f"camfrog_sha256={data['camfrog']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
