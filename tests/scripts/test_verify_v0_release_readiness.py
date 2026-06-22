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
        root / "docs/reviews/M0/SIGNOFF_MATRIX.md",
        "\n".join(
            [
                "| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |",
                "Model catalog strict verification: PASS",
                "Import boundary report: PASS",
            ]
        ),
    )
    write_text(
        root / "artifacts/review/m1_smoke_recertification_evidence.md",
        "\n".join(
            [
                "Decision: `GO_M1_SMOKE_CURRENT_ENVIRONMENT`",
                "toolchain versions OK",
                "tests/smoke/test_m1_smoke.py 1 passed",
            ]
        ),
    )
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
    write_text(
        root / "docs/WORKING.md",
        "\n".join(
            [
                "M1_Final_Smoke_Verified: true",
                "M1_Smoke_Current_Environment: true",
                "M2_000_to_M2_004_Verified: true",
                "M3_000_to_M3_005_Verified: true",
                "M4_001_to_M4_003_Verified: true",
                "M5_001_to_M5_003_Verified: true",
                "M6_001_Verified: true",
                "M6_002_Verified: true",
                "FE_V6_Mockup_Verified: true",
                "V0_Release_Readiness_Audit: true",
            ]
        ),
    )
    write_m6_review_docs(root, decision="NOT_GO")


def write_m6_review_docs(root: Path, *, decision: str) -> None:
    if decision == "GO":
        write_text(
            root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
            "| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |\n",
        )
        write_text(root / "docs/reviews/M6/CTO_DECISION.md", "Decision: GO\n")
        return
    write_text(
        root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
        "| M6 Export / v0 RC | GO | GO | GO | NO_GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |\n",
    )
    write_text(
        root / "docs/reviews/M6/CTO_DECISION.md",
        "Decision: NOT_GO\nreal trained CUDA `lora_adapter` endpoint\nMIB_RUNTIME_ALLOW_FAKE_BACKEND\n",
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


def write_bundle_verification(root: Path, *, decision: str) -> None:
    if decision == "GO":
        write_json(
            root / "artifacts/review/real_adapter_evidence_bundle_verification.json",
            {
                "schema_version": "mib_real_adapter_evidence_bundle_verification.v1",
                "decision": "GO_REAL_ADAPTER_EVIDENCE_BUNDLE",
                "verification_ok": True,
                "release_bundle_ready": True,
                "blockers": [],
            },
        )
        return
    write_json(
        root / "artifacts/review/real_adapter_evidence_bundle_verification.json",
        {
            "schema_version": "mib_real_adapter_evidence_bundle_verification.v1",
            "decision": "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE",
            "verification_ok": True,
            "release_bundle_ready": False,
            "blockers": ["endpoint_live_no_fake_json", "adapter_intake_go", "rc_gate_go", "m6_verification_go"],
        },
    )


def test_current_not_go_is_verified_when_only_real_adapter_endpoint_is_missing(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="NOT_GO")
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
    assert report["summary"]["m0_product_lock_verified"] is True
    assert report["summary"]["m1_current_environment_smoke_verified"] is True
    assert report["summary"]["fe_v6_applied"] is True
    assert report["summary"]["desktop_e2e_route_repair_verified"] is True
    assert report["summary"]["working_recorded_milestone_state_verified"] is True
    assert report["summary"]["m6_review_docs_current"] is True
    assert report["summary"]["real_adapter_evidence_bundle_ready"] is False
    assert report["summary"]["real_adapter_evidence_bundle_decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert report["summary"]["real_adapter_missing_prereq_ids"] == ["host_cuda_visible"]


def test_release_go_requires_m6_rc_go(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_m6_review_docs(tmp_path, decision="GO")
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="GO")
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
    assert report["summary"]["real_adapter_evidence_bundle_ready"] is True


def test_release_go_requires_real_adapter_bundle_go(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_m6_review_docs(tmp_path, decision="GO")
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="NOT_GO")
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

    assert report["decision"] == "NOT_GO"
    assert report["release_ready"] is False
    assert report["blockers"] == ["real_trained_adapter_no_fake_endpoint"]
    assert report["unexpected_blockers"] == []


def test_missing_fe_v6_evidence_is_unexpected_release_blocker(tmp_path: Path) -> None:
    write_text(
        tmp_path / "docs/reviews/M0/SIGNOFF_MATRIX.md",
        "| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |\nModel catalog strict verification: PASS\nImport boundary report: PASS\n",
    )
    write_text(
        tmp_path / "artifacts/review/m1_smoke_recertification_evidence.md",
        "Decision: `GO_M1_SMOKE_CURRENT_ENVIRONMENT`\ntoolchain versions OK\ntests/smoke/test_m1_smoke.py 1 passed\n",
    )
    write_text(
        tmp_path / "docs/WORKING.md",
        "\n".join(verify.WORKING_RECORDED_GO_MARKERS),
    )
    write_m6_review_docs(tmp_path, decision="NOT_GO")
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="NOT_GO")
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


def test_missing_recorded_milestone_state_is_unexpected_release_blocker(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_text(
        tmp_path / "docs/WORKING.md",
        "\n".join(marker for marker in verify.WORKING_RECORDED_GO_MARKERS if "M4_001_to_M4_003" not in marker),
    )
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="NOT_GO")
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
    assert "recorded_milestone_state_incomplete" in report["blockers"]
    assert "recorded_milestone_state_incomplete" in report["unexpected_blockers"]


def test_m6_unexpected_blockers_are_propagated(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_prereq_audit(tmp_path)
    write_bundle_verification(tmp_path, decision="NOT_GO")
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


def test_missing_bundle_report_is_unexpected_release_blocker(tmp_path: Path) -> None:
    write_required_text_evidence(tmp_path)
    write_m6_review_docs(tmp_path, decision="GO")
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

    assert "real_adapter_evidence_bundle_unavailable" in report["blockers"]
    assert "real_adapter_evidence_bundle_unavailable" in report["unexpected_blockers"]
