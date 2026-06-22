from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verify = load_module("scripts/verify_v0_release_readiness.py", "verify_v0_release_readiness")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_required_text_evidence(root: Path) -> None:
    write_text(
        root / "artifacts/review/fe_v6_evidence.md",
        "Gate: `mib-studio-fe-v6-mockup`\nBrowser Verification Evidence\nrun e2e`: passed\n",
    )
    write_text(
        root / "artifacts/review/desktop_e2e_route_repair_evidence.md",
        "\n".join(
            [
                "decision: GO_DESKTOP_E2E_ROUTE_REPAIR_M6_NOT_GO",
                "M1 desktop shell happy path passed",
                "FE v6 route contract builder passed",
                "M2 teacher packet preview passed",
            ]
        ),
    )


def write_prereq_audit(root: Path) -> None:
    write_json(
        root / "artifacts/review/m6_real_adapter_prereq_audit.json",
        {
            "schema_version": "mib_real_adapter_rc_gate_runner.v1",
            "status": "NOT_READY_PRECHECK_FAILED",
            "decision": "NOT_READY",
            "errors": ["host_cuda_visible: nvidia-smi missing"],
            "preflight": [{"id": "host_cuda_visible", "ok": False}],
        },
    )


def test_current_not_go_is_verified_when_only_real_adapter_endpoint_is_missing(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_prereq_audit(tmp_path)
    write_json(
        tmp_path / "artifacts/review/m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "NOT_GO",
            "verification_ok": True,
            "blockers": ["real_trained_adapter_no_fake_endpoint"],
            "unexpected_blockers": [],
        },
    )

    report = verify.evaluate(tmp_path)

    assert report["decision"] == "NOT_GO"
    assert report["blockers"] == ["real_trained_adapter_no_fake_endpoint"]
    assert report["unexpected_blockers"] == []
    assert report["summary"]["fe_v6_applied"] is True
    assert report["summary"]["desktop_e2e_route_repair_verified"] is True
    assert report["summary"]["real_adapter_missing_prereq_ids"] == ["host_cuda_visible"]


def test_release_go_requires_m6_rc_go(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_prereq_audit(tmp_path)
    write_json(
        tmp_path / "artifacts/review/m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "GO",
            "verification_ok": True,
            "blockers": [],
            "unexpected_blockers": [],
        },
    )

    report = verify.evaluate(tmp_path)

    assert report["decision"] == "GO"
    assert report["release_ready"] is True
    assert report["blockers"] == []


def test_missing_fe_v6_evidence_is_unexpected_release_blocker(tmp_path: Path) -> None:
    write_prereq_audit(tmp_path)
    write_json(
        tmp_path / "artifacts/review/m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "NOT_GO",
            "verification_ok": True,
            "blockers": ["real_trained_adapter_no_fake_endpoint"],
            "unexpected_blockers": [],
        },
    )

    report = verify.evaluate(tmp_path)

    assert report["decision"] == "NOT_GO"
    assert "fe_v6_not_verified" in report["blockers"]
    assert "desktop_e2e_route_repair_not_verified" in report["blockers"]
    assert "fe_v6_not_verified" in report["unexpected_blockers"]


def test_m6_unexpected_blockers_are_propagated(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_prereq_audit(tmp_path)
    write_json(
        tmp_path / "artifacts/review/m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "NOT_GO",
            "verification_ok": False,
            "blockers": ["real_trained_adapter_no_fake_endpoint", "export_secret_scan_failed"],
            "unexpected_blockers": ["export_secret_scan_failed"],
        },
    )

    report = verify.evaluate(tmp_path)

    assert report["decision"] == "NOT_GO"
    assert "export_secret_scan_failed" in report["blockers"]
    assert report["unexpected_blockers"] == ["export_secret_scan_failed"]
