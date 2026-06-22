#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_v0_release_readiness.v1"
ACCEPTABLE_NOT_GO_BLOCKERS = ["real_trained_adapter_no_fake_endpoint"]
REAL_ADAPTER_BUNDLE_BLOCKER_IDS = {
    "endpoint_live_no_fake_json",
    "endpoint_markdown_present",
    "adapter_intake_go",
    "adapter_hash_crosscheck",
    "rc_gate_go",
    "m6_verification_go",
}


TEXT_EVIDENCE_CHECKS = [
    {
        "id": "m0_product_lock",
        "path": "docs/reviews/M0/SIGNOFF_MATRIX.md",
        "required": [
            "| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |",
            "Model catalog strict verification: PASS",
            "Import boundary report: PASS",
        ],
        "blocker": "m0_product_lock_not_verified",
        "release_required": True,
    },
    {
        "id": "m1_current_environment_smoke",
        "path": "artifacts/review/m1_smoke_recertification_evidence.md",
        "required": [
            "Decision: `GO_M1_SMOKE_CURRENT_ENVIRONMENT`",
            "toolchain versions OK",
            "tests/smoke/test_m1_smoke.py 1 passed",
        ],
        "blocker": "m1_current_environment_smoke_not_verified",
        "release_required": True,
    },
    {
        "id": "fe_v6_applied",
        "path": "artifacts/review/fe_v6_evidence.md",
        "required": [
            "Gate: `mib-studio-fe-v6-mockup`",
            "Browser Verification Evidence",
            "run e2e`: passed",
        ],
        "blocker": "fe_v6_not_verified",
        "release_required": True,
    },
    {
        "id": "desktop_e2e_route_repair",
        "path": "artifacts/review/desktop_e2e_route_repair_evidence.md",
        "required": [
            "decision: GO_DESKTOP_E2E_ROUTE_REPAIR_M6_NOT_GO",
            "M1 desktop shell happy path passed",
            "FE v6 route contract builder passed",
            "M2 teacher packet preview passed",
        ],
        "blocker": "desktop_e2e_route_repair_not_verified",
        "release_required": True,
    },
]

WORKING_RECORDED_GO_MARKERS = [
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


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def text_check(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    path = root / str(spec["path"])
    text = read_text(path)
    missing = [marker for marker in spec["required"] if marker not in text]
    ok = bool(text) and not missing
    return {
        "id": spec["id"],
        "path": str(spec["path"]),
        "present": bool(text),
        "ok": ok,
        "release_required": spec["release_required"],
        "missing_markers": missing,
        "blocker": None if ok else spec["blocker"],
    }


def m6_rc_check(root: Path) -> dict[str, Any]:
    path = root / "artifacts/review/m6_rc_evidence_verification.json"
    data = read_json(path)
    if data is None:
        return {
            "id": "m6_rc_evidence_verification",
            "path": "artifacts/review/m6_rc_evidence_verification.json",
            "present": False,
            "ok": False,
            "release_required": True,
            "decision": None,
            "verification_ok": False,
            "blockers": ["m6_rc_evidence_unavailable"],
            "unexpected_blockers": ["m6_rc_evidence_unavailable"],
        }

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        blockers = ["m6_rc_blockers_not_reported"]
    unexpected = data.get("unexpected_blockers")
    if not isinstance(unexpected, list):
        unexpected = ["m6_rc_unexpected_blockers_not_reported"]
    verification_ok = data.get("verification_ok") is True
    decision = data.get("decision")
    release_ok = verification_ok and decision == "GO" and not blockers
    return {
        "id": "m6_rc_evidence_verification",
        "path": "artifacts/review/m6_rc_evidence_verification.json",
        "present": True,
        "ok": release_ok,
        "release_required": True,
        "decision": decision,
        "verification_ok": verification_ok,
        "blockers": blockers,
        "unexpected_blockers": unexpected,
    }


def prereq_audit_check(root: Path) -> dict[str, Any]:
    path = root / "artifacts/review/m6_real_adapter_prereq_audit.json"
    data = read_json(path)
    if data is None:
        return {
            "id": "m6_real_adapter_prereq_audit",
            "path": "artifacts/review/m6_real_adapter_prereq_audit.json",
            "present": False,
            "ok": False,
            "release_required": False,
            "status": None,
            "decision": None,
            "errors": ["prereq audit missing"],
            "missing_prereq_ids": [],
        }
    errors = data.get("errors")
    if not isinstance(errors, list):
        errors = []
    preflight = data.get("preflight")
    missing_prereq_ids: list[str] = []
    if isinstance(preflight, list):
        for row in preflight:
            if isinstance(row, dict) and row.get("ok") is not True and isinstance(row.get("id"), str):
                missing_prereq_ids.append(row["id"])
    return {
        "id": "m6_real_adapter_prereq_audit",
        "path": "artifacts/review/m6_real_adapter_prereq_audit.json",
        "present": True,
        "ok": data.get("status") == "READY_TO_RUN" and data.get("decision") == "READY",
        "release_required": False,
        "status": data.get("status"),
        "decision": data.get("decision"),
        "errors": errors,
        "missing_prereq_ids": missing_prereq_ids,
    }


def real_adapter_bundle_check(root: Path) -> dict[str, Any]:
    path = root / "artifacts/review/real_adapter_evidence_bundle_verification.json"
    data = read_json(path)
    if data is None:
        return {
            "id": "real_adapter_evidence_bundle_verification",
            "path": "artifacts/review/real_adapter_evidence_bundle_verification.json",
            "present": False,
            "ok": False,
            "release_required": True,
            "decision": None,
            "verification_ok": False,
            "release_bundle_ready": False,
            "bundle_blockers": ["bundle_report_missing"],
            "blocker": "real_adapter_evidence_bundle_unavailable",
        }
    bundle_blockers = data.get("blockers")
    if not isinstance(bundle_blockers, list):
        bundle_blockers = ["bundle_blockers_not_reported"]
    decision = data.get("decision")
    ok = (
        data.get("schema_version") == "mib_real_adapter_evidence_bundle_verification.v1"
        and decision == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
        and data.get("verification_ok") is True
        and data.get("release_bundle_ready") is True
        and bundle_blockers == []
    )
    if ok:
        blocker = None
    elif all(isinstance(item, str) and item in REAL_ADAPTER_BUNDLE_BLOCKER_IDS for item in bundle_blockers):
        blocker = "real_trained_adapter_no_fake_endpoint"
    else:
        blocker = "real_adapter_evidence_bundle_not_verified"
    return {
        "id": "real_adapter_evidence_bundle_verification",
        "path": "artifacts/review/real_adapter_evidence_bundle_verification.json",
        "present": True,
        "ok": ok,
        "release_required": True,
        "decision": decision,
        "verification_ok": data.get("verification_ok") is True,
        "release_bundle_ready": data.get("release_bundle_ready") is True,
        "bundle_blockers": bundle_blockers,
        "blocker": blocker,
    }


def working_state_check(root: Path) -> dict[str, Any]:
    path = root / "docs/WORKING.md"
    text = read_text(path)
    missing = [marker for marker in WORKING_RECORDED_GO_MARKERS if marker not in text]
    ok = bool(text) and not missing
    return {
        "id": "working_recorded_milestone_state",
        "path": "docs/WORKING.md",
        "present": bool(text),
        "ok": ok,
        "release_required": True,
        "missing_markers": missing,
        "blocker": None if ok else "recorded_milestone_state_incomplete",
    }


def m6_review_docs_check(root: Path, m6_decision: object) -> dict[str, Any]:
    signoff_path = root / "docs/reviews/M6/SIGNOFF_MATRIX.md"
    cto_path = root / "docs/reviews/M6/CTO_DECISION.md"
    signoff = read_text(signoff_path)
    cto = read_text(cto_path)
    if m6_decision == "GO":
        requirements = {
            "signoff_final_go": "| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |" in signoff,
            "cto_decision_go": "Decision: GO" in cto,
        }
    else:
        requirements = {
            "signoff_final_not_go": "| M6 Export / v0 RC | GO | GO | GO | NO_GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |" in signoff,
            "cto_decision_not_go": "Decision: NOT_GO" in cto,
            "cto_real_adapter_blocker": "real trained CUDA `lora_adapter` endpoint" in cto
            and "MIB_RUNTIME_ALLOW_FAKE_BACKEND" in cto,
        }
    ok = bool(signoff and cto) and all(requirements.values())
    return {
        "id": "m6_review_docs_current",
        "path": "docs/reviews/M6/",
        "present": bool(signoff and cto),
        "ok": ok,
        "release_required": True,
        "requirements": requirements,
        "blocker": None if ok else "m6_review_docs_not_current",
    }


def derive_blockers(checks: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for check in checks:
        if not check.get("release_required") or check.get("ok") is True:
            continue
        if check["id"] == "m6_rc_evidence_verification":
            for blocker in check.get("blockers", []):
                if isinstance(blocker, str):
                    blockers.append(blocker)
            continue
        blocker = check.get("blocker")
        if isinstance(blocker, str):
            blockers.append(blocker)
    return sorted(set(blockers))


def evaluate(root: Path) -> dict[str, Any]:
    checks = [text_check(root, spec) for spec in TEXT_EVIDENCE_CHECKS]
    checks.append(working_state_check(root))
    m6_check = m6_rc_check(root)
    checks.append(m6_check)
    bundle_check = real_adapter_bundle_check(root)
    checks.append(bundle_check)
    checks.append(m6_review_docs_check(root, m6_check.get("decision")))
    checks.append(prereq_audit_check(root))

    blockers = derive_blockers(checks)
    decision = "GO" if not blockers else "NOT_GO"
    unexpected_blockers = sorted(blocker for blocker in blockers if blocker not in ACCEPTABLE_NOT_GO_BLOCKERS)
    prereq_check = next(check for check in checks if check["id"] == "m6_real_adapter_prereq_audit")
    if isinstance(m6_check.get("unexpected_blockers"), list):
        unexpected_blockers = sorted(set(unexpected_blockers + [str(item) for item in m6_check["unexpected_blockers"]]))

    return {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "release_ready": decision == "GO",
        "acceptable_not_go_blockers": ACCEPTABLE_NOT_GO_BLOCKERS,
        "blockers": blockers,
        "unexpected_blockers": unexpected_blockers,
        "checks": checks,
        "summary": {
            "m0_product_lock_verified": next(check for check in checks if check["id"] == "m0_product_lock")["ok"] is True,
            "m1_current_environment_smoke_verified": next(check for check in checks if check["id"] == "m1_current_environment_smoke")["ok"] is True,
            "fe_v6_applied": next(check for check in checks if check["id"] == "fe_v6_applied")["ok"] is True,
            "desktop_e2e_route_repair_verified": next(check for check in checks if check["id"] == "desktop_e2e_route_repair")["ok"] is True,
            "working_recorded_milestone_state_verified": next(check for check in checks if check["id"] == "working_recorded_milestone_state")["ok"] is True,
            "m6_review_docs_current": next(check for check in checks if check["id"] == "m6_review_docs_current")["ok"] is True,
            "real_adapter_evidence_bundle_ready": bundle_check.get("ok") is True,
            "real_adapter_evidence_bundle_decision": bundle_check.get("decision"),
            "real_adapter_evidence_bundle_blockers": bundle_check.get("bundle_blockers", []),
            "m6_rc_decision": m6_check.get("decision"),
            "m6_rc_verification_ok": m6_check.get("verification_ok") is True,
            "real_adapter_prereq_status": prereq_check.get("status"),
            "real_adapter_missing_prereq_ids": prereq_check.get("missing_prereq_ids", []),
        },
        "notes": [
            "Release GO requires current M6-RC evidence verification decision GO.",
            "M0-M6 milestone evidence markers are release-required and become unexpected blockers if missing.",
            "Current NOT_GO is acceptable only when real_trained_adapter_no_fake_endpoint is the sole blocker.",
            "v0 release GO requires GO_REAL_ADAPTER_EVIDENCE_BUNDLE from the real adapter bundle verifier.",
            "Prereq audit is diagnostic; it explains what must be supplied before the live M6-RC gate can run.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify v0 release readiness from current SSOT-backed evidence.")
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--json-output", default="artifacts/review/v0_release_readiness_audit.json")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = evaluate(root)
    report["expected_decision"] = args.expected_decision
    report["decision_matches_expected"] = report["decision"] == args.expected_decision
    report["verification_ok"] = report["decision_matches_expected"] and (
        args.expected_decision == "GO" or not report["unexpected_blockers"]
    )

    output = Path(args.json_output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
