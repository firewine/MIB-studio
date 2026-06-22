#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECKS = [
    {
        "id": "fe_v6_mockup",
        "path": "artifacts/review/fe_v6_evidence.md",
        "required": ["Gate: `mib-studio-fe-v6-mockup`", "Browser Verification Evidence", "run e2e`: passed"],
        "rc_required": True,
    },
    {
        "id": "docker_real_backend_deps",
        "path": "artifacts/review/docker_real_backend_deps_evidence.md",
        "required": ["Decision: `GO_DEPENDENCY_PACKAGING_ONLY`", "temp_image_backend_import_probe: pass"],
        "rc_required": True,
    },
    {
        "id": "adapter_structural_validation",
        "path": "artifacts/review/export_adapter_validation_evidence.md",
        "required": ["Decision: `GO_STRUCTURAL_ADAPTER_VALIDATION`", "M6-RC remains `NOT_GO`"],
        "rc_required": True,
    },
    {
        "id": "adapter_lineage_validation",
        "path": "artifacts/review/export_adapter_lineage_evidence.md",
        "required": ["Decision: `GO_EXPORT_LINEAGE_VALIDATION`", "M6-RC remains `NOT_GO`"],
        "rc_required": True,
    },
    {
        "id": "adapter_load_guard",
        "path": "artifacts/review/exported_adapter_load_guard_evidence.md",
        "required": ["Decision: `GO_TEST_GUARD_ONLY_M6_NOT_GO`", "fake_backend_requires_explicit_env: true"],
        "rc_required": True,
    },
    {
        "id": "phi_fixture_endpoint_path",
        "path": "artifacts/review/phi_strict_cache_runtime_evidence.md",
        "required": ["Decision: `PARTIAL_GO_ENDPOINT_PATH_WITH_FIXTURE_ADAPTER`", "MIB_RUNTIME_ALLOW_FAKE_BACKEND=1"],
        "rc_required": False,
    },
    {
        "id": "real_adapter_blocker_record",
        "path": "artifacts/review/real_adapter_inference_evidence.md",
        "required": ["Decision: `NOT_GO_REAL_ADAPTER_INFERENCE_BLOCKED`", "real_trained_adapter_found: false"],
        "rc_required": False,
    },
]


def read_text(path: str) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8")


def evaluate_check(item: dict[str, object]) -> dict[str, object]:
    path = str(item["path"])
    text = read_text(path)
    missing = [needle for needle in item["required"] if needle not in text]  # type: ignore[index]
    return {
        "id": item["id"],
        "path": path,
        "present": bool(text),
        "ok": bool(text) and not missing,
        "rc_required": bool(item["rc_required"]),
        "missing_markers": missing,
    }


def real_endpoint_check(path: str) -> dict[str, object]:
    text = read_text(path)
    json_result = real_endpoint_json_check(Path(path).with_suffix(".json"))
    if json_result["present"]:
        return json_result
    required_markers = [
        "Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`",
        "MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent",
        "/agents/{agent_id}/run: 200",
        "/v1/chat/completions: 200",
        "real_trained_adapter: true",
        "adapter_intake_verified: true",
    ]
    missing = [marker for marker in required_markers if marker not in text]
    fake_backend_present = "MIB_RUNTIME_ALLOW_FAKE_BACKEND=1" in text or "MIB_RUNTIME_ALLOW_FAKE_BACKEND: present" in text
    self_test = "self_test: true" in text
    return {
        "id": "real_trained_adapter_no_fake_endpoint",
        "path": path,
        "present": bool(text),
        "ok": False,
        "rc_required": True,
        "missing_markers": ["structured endpoint JSON sidecar"] + missing,
        "fake_backend_present": fake_backend_present,
        "self_test": self_test,
        "source": "markdown_only" if text else None,
    }


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def real_endpoint_json_check(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {
            "id": "real_trained_adapter_no_fake_endpoint",
            "path": str(path),
            "present": False,
            "ok": False,
            "rc_required": True,
            "missing_markers": ["structured endpoint JSON sidecar"],
            "self_test": False,
            "source": None,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "id": "real_trained_adapter_no_fake_endpoint",
            "path": str(path),
            "present": True,
            "ok": False,
            "rc_required": True,
            "missing_markers": [f"invalid JSON: {exc}"],
            "self_test": False,
            "source": None,
        }
    requirements = {
        "schema_version": data.get("schema_version") == "mib_real_adapter_endpoint_evidence.v1",
        "source": data.get("source") == "live_docker_capture",
        "decision": data.get("decision") == "GO_REAL_TRAINED_ADAPTER_ENDPOINT",
        "self_test": data.get("self_test") is False,
        "adapter_intake_verified": data.get("adapter_intake_verified") is True,
        "adapter_sha256": is_sha256(data.get("adapter_sha256")),
        "artifact_manifest_sha256": is_sha256(data.get("artifact_manifest_sha256")),
        "fake_backend_env_absent": data.get("fake_backend_env_absent") is True,
        "readonly_model_cache_mount": data.get("readonly_model_cache_mount") is True,
        "health_status": data.get("health_status") == 200,
        "native_status": data.get("native_status") == 200,
        "openai_status": data.get("openai_status") == 200,
        "native_openai_output_equal": data.get("native_openai_output_equal") is True,
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return {
        "id": "real_trained_adapter_no_fake_endpoint",
        "path": str(path),
        "present": True,
        "ok": not missing,
        "rc_required": True,
        "missing_markers": missing,
        "fake_backend_present": data.get("fake_backend_env_absent") is False,
        "self_test": data.get("self_test") is True,
        "source": data.get("source"),
    }


def review_doc_check(expected_decision: str) -> dict[str, object]:
    fe_review = read_text("docs/reviews/M6/FE_REVIEW.md")
    signoff = read_text("docs/reviews/M6/SIGNOFF_MATRIX.md")
    cto = read_text("docs/reviews/M6/CTO_DECISION.md")
    if expected_decision == "GO":
        requirements = {
            "fe_review_go": "Decision: GO" in fe_review,
            "signoff_final_go": "| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |" in signoff,
            "cto_decision_go": "Decision: GO" in cto,
        }
    else:
        requirements = {
            "fe_review_go": "Decision: GO" in fe_review,
            "signoff_fe_go": "| M6 Export / v0 RC | GO |" in signoff,
            "signoff_decision_not_go": "| NOT_GO |" in signoff,
            "cto_decision_not_go": "Decision: NOT_GO" in cto,
            "cto_real_adapter_blocker": "real trained adapter" in cto and "MIB_RUNTIME_ALLOW_FAKE_BACKEND" in cto,
        }
    return {
        "id": "m6_review_docs_current",
        "path": "docs/reviews/M6/",
        "present": bool(fe_review and signoff and cto),
        "ok": all(requirements.values()),
        "rc_required": True,
        "expected_decision": expected_decision,
        "requirements": requirements,
    }


def evaluate(expected_decision: str, real_endpoint_evidence: str) -> dict[str, object]:
    checks = [evaluate_check(item) for item in CHECKS]
    checks.append(real_endpoint_check(real_endpoint_evidence))
    checks.append(review_doc_check(expected_decision))

    blockers = []
    for item in checks:
        if item["rc_required"] and not item["ok"]:
            blockers.append(item["id"])

    decision = "GO" if not blockers else "NOT_GO"
    acceptable_not_go_blockers = ["real_trained_adapter_no_fake_endpoint"]
    unexpected_blockers = [item for item in blockers if item not in acceptable_not_go_blockers]
    verification_ok = decision == expected_decision
    if expected_decision == "NOT_GO":
        verification_ok = verification_ok and not unexpected_blockers
    return {
        "schema_version": "mib_m6_rc_evidence_verification.v1",
        "decision": decision,
        "expected_decision": expected_decision,
        "decision_matches_expected": decision == expected_decision,
        "acceptable_not_go_blockers": acceptable_not_go_blockers,
        "unexpected_blockers": unexpected_blockers,
        "verification_ok": verification_ok,
        "checks": checks,
        "blockers": blockers,
        "notes": [
            "Fixture endpoint evidence that uses MIB_RUNTIME_ALLOW_FAKE_BACKEND=1 is not RC GO evidence.",
            "M6-RC GO requires real trained adapter endpoint evidence without MIB_RUNTIME_ALLOW_FAKE_BACKEND.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--real-endpoint-evidence", default="artifacts/review/real_trained_adapter_endpoint_evidence.md")
    parser.add_argument("--json-output", default="artifacts/review/m6_rc_evidence_verification.json")
    args = parser.parse_args()

    report = evaluate(args.expected_decision, args.real_endpoint_evidence)
    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
