from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_live_evidence.py"
    spec = importlib.util.spec_from_file_location("validate_live_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _passing_evidence(module):
    return {
        "schema_version": 1,
        "source": {"version": "2.2.5-rc12", "git_sha": "a" * 40},
        "camfrog": {
            "executable_path": r"C:\Program Files\Camfrog\Camfrog Video Chat.exe",
            "sha256": "b" * 64,
        },
        "gates": [
            {"id": gate, "status": "pass", "notes": ""}
            for gate in module.EXPECTED_GATE_IDS
        ],
        "production_gate_passed": True,
    }


def test_live_evidence_validator_accepts_all_required_passes():
    validator = _load_validator()
    evidence = _passing_evidence(validator)
    assert validator.validate_evidence(
        evidence,
        expected_version="2.2.5-rc12",
        expected_git_sha="a" * 40,
    ) == []


def test_live_evidence_validator_rejects_skip_and_false_ready_flag():
    validator = _load_validator()
    evidence = _passing_evidence(validator)
    evidence["gates"][0]["status"] = "skip"
    evidence["production_gate_passed"] = True
    errors = validator.validate_evidence(
        evidence,
        expected_version="2.2.5-rc12",
        expected_git_sha="a" * 40,
    )
    assert any("required gates not passed" in error for error in errors)
    assert any("production_gate_passed must be false" in error for error in errors)


def test_live_evidence_validator_rejects_wrong_commit_and_bad_hash():
    validator = _load_validator()
    evidence = _passing_evidence(validator)
    evidence["source"]["git_sha"] = "c" * 40
    evidence["camfrog"]["sha256"] = "not-a-hash"
    errors = validator.validate_evidence(
        evidence,
        expected_version="2.2.5-rc12",
        expected_git_sha="a" * 40,
    )
    assert any("expected commit" in error for error in errors)
    assert any("camfrog.sha256" in error for error in errors)


def test_collector_documents_all_live_gates_and_privacy_boundary():
    text = (ROOT / "scripts" / "collect_live_evidence.ps1").read_text(encoding="utf-8")
    validator = _load_validator()
    for gate in validator.EXPECTED_GATE_IDS:
        assert f'"{gate}"' in text
    assert "Do not paste passwords, tokens, private chat text" in text
    assert "production_gate_passed" in text
