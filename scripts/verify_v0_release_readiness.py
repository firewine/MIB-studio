#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_v0_release_readiness.v1"
ACCEPTABLE_NOT_GO_BLOCKERS = ["real_trained_adapter_no_fake_endpoint"]


TEXT_EVIDENCE_CHECKS = [
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
    checks.append(m6_rc_check(root))
    checks.append(prereq_audit_check(root))

    blockers = derive_blockers(checks)
    decision = "GO" if not blockers else "NOT_GO"
    unexpected_blockers = sorted(blocker for blocker in blockers if blocker not in ACCEPTABLE_NOT_GO_BLOCKERS)
    m6_check = next(check for check in checks if check["id"] == "m6_rc_evidence_verification")
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
            "fe_v6_applied": checks[0]["ok"] is True,
            "desktop_e2e_route_repair_verified": checks[1]["ok"] is True,
            "m6_rc_decision": m6_check.get("decision"),
            "m6_rc_verification_ok": m6_check.get("verification_ok") is True,
            "real_adapter_prereq_status": prereq_check.get("status"),
            "real_adapter_missing_prereq_ids": prereq_check.get("missing_prereq_ids", []),
        },
        "notes": [
            "Release GO requires current M6-RC evidence verification decision GO.",
            "Current NOT_GO is acceptable only when real_trained_adapter_no_fake_endpoint is the sole blocker.",
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
