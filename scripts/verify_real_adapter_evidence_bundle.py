#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_real_adapter_evidence_bundle_verification.v1"

FILES = {
    "endpoint_json": "real_trained_adapter_endpoint_evidence.json",
    "endpoint_markdown": "real_trained_adapter_endpoint_evidence.md",
    "adapter_intake": "real_adapter_artifact_intake.json",
    "rc_gate": "m6_real_adapter_rc_gate_run.json",
    "m6": "m6_rc_evidence_verification.json",
    "v0": "v0_release_readiness_audit.json",
}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "expected JSON object"
    return data, None


def check_row(check_id: str, ok: bool, detail: str, *, path: Path | None = None, missing_markers: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": ok,
        "detail": detail,
        "path": str(path) if path else None,
        "missing_markers": missing_markers or [],
    }


def endpoint_check(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    data, error = read_json(path)
    if error:
        return check_row("endpoint_live_no_fake_json", False, error, path=path, missing_markers=["structured endpoint JSON sidecar"]), None
    assert data is not None
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
    return check_row("endpoint_live_no_fake_json", not missing, "ok" if not missing else "endpoint JSON failed strict live checks", path=path, missing_markers=missing), data


def endpoint_markdown_check(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return check_row("endpoint_markdown_present", False, "missing", path=path, missing_markers=["endpoint markdown"])
    text = path.read_text(encoding="utf-8", errors="replace")
    forbidden = ["MIB_RUNTIME_ALLOW_FAKE_BACKEND=1", "MIB_RUNTIME_ALLOW_FAKE_BACKEND: present", "self_test: true"]
    found = [marker for marker in forbidden if marker in text]
    required = [
        "Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`",
        "MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent",
        "/agents/{agent_id}/run: 200",
        "/v1/chat/completions: 200",
        "real_trained_adapter: true",
        "adapter_intake_verified: true",
        "self_test: false",
    ]
    missing = [marker for marker in required if marker not in text]
    markers = [f"missing:{marker}" for marker in missing] + [f"forbidden:{marker}" for marker in found]
    return check_row("endpoint_markdown_markers", not markers, "ok" if not markers else "endpoint markdown markers failed", path=path, missing_markers=markers)


def intake_check(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    data, error = read_json(path)
    if error:
        return check_row("adapter_intake_go", False, error, path=path, missing_markers=["adapter intake JSON"]), None
    assert data is not None
    requirements = {
        "schema_version": data.get("schema_version") == "mib_real_adapter_artifact_intake.v1",
        "status": data.get("status") == "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
        "adapter_sha256": is_sha256(data.get("adapter_sha256")),
        "artifact_manifest_sha256": is_sha256(data.get("artifact_manifest_sha256")),
        "errors_empty": data.get("errors") in ([], None),
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("adapter_intake_go", not missing, "ok" if not missing else "adapter intake is not GO", path=path, missing_markers=missing), data


def rc_gate_check(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    data, error = read_json(path)
    if error:
        return check_row("rc_gate_go", False, error, path=path, missing_markers=["RC gate runner JSON"]), None
    assert data is not None
    steps = data.get("steps")
    step_ids = [row.get("id") for row in steps] if isinstance(steps, list) and all(isinstance(row, dict) for row in steps) else []
    returncodes_ok = isinstance(steps, list) and all(isinstance(row, dict) and row.get("returncode") == 0 for row in steps)
    requirements = {
        "schema_version": data.get("schema_version") == "mib_real_adapter_rc_gate_runner.v1",
        "status": data.get("status") == "GO_M6_REAL_ADAPTER_RC_GATE",
        "decision": data.get("decision") == "GO",
        "m6_rc_claimed_go": data.get("m6_rc_claimed_go") is True,
        "errors_empty": data.get("errors") == [],
        "steps": step_ids == ["adapter_intake", "endpoint_capture", "m6_go_verification"],
        "step_returncodes": returncodes_ok,
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("rc_gate_go", not missing, "ok" if not missing else "RC gate runner is not GO", path=path, missing_markers=missing), data


def m6_check(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    data, error = read_json(path)
    if error:
        return check_row("m6_verification_go", False, error, path=path, missing_markers=["M6 verification JSON"]), None
    assert data is not None
    endpoint_rows = [
        row
        for row in data.get("checks", [])
        if isinstance(row, dict) and row.get("id") == "real_trained_adapter_no_fake_endpoint"
    ]
    endpoint_ok = any(row.get("ok") is True and row.get("source") == "live_docker_capture" and row.get("self_test") is False for row in endpoint_rows)
    requirements = {
        "schema_version": data.get("schema_version") == "mib_m6_rc_evidence_verification.v1",
        "decision": data.get("decision") == "GO",
        "verification_ok": data.get("verification_ok") is True,
        "blockers_empty": data.get("blockers") == [],
        "unexpected_blockers_empty": data.get("unexpected_blockers") == [],
        "endpoint_check": endpoint_ok,
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("m6_verification_go", not missing, "ok" if not missing else "M6 verification is not GO", path=path, missing_markers=missing), data


def v0_check(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    data, error = read_json(path)
    if error:
        return check_row("v0_readiness_go", False, error, path=path, missing_markers=["v0 readiness JSON"]), None
    assert data is not None
    requirements = {
        "schema_version": data.get("schema_version") == "mib_v0_release_readiness.v1",
        "decision": data.get("decision") == "GO",
        "verification_ok": data.get("verification_ok") is True,
        "release_ready": data.get("release_ready") is True,
        "blockers_empty": data.get("blockers") == [],
        "unexpected_blockers_empty": data.get("unexpected_blockers") == [],
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("v0_readiness_go", not missing, "ok" if not missing else "v0 readiness is not GO", path=path, missing_markers=missing), data


def cross_hash_check(endpoint: dict[str, Any] | None, intake: dict[str, Any] | None) -> dict[str, Any]:
    if not endpoint or not intake:
        return check_row("adapter_hash_crosscheck", False, "endpoint or intake JSON missing", missing_markers=["endpoint_json", "adapter_intake_json"])
    requirements = {
        "adapter_sha256": endpoint.get("adapter_sha256") == intake.get("adapter_sha256"),
        "artifact_manifest_sha256": endpoint.get("artifact_manifest_sha256") == intake.get("artifact_manifest_sha256"),
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("adapter_hash_crosscheck", not missing, "ok" if not missing else "adapter hashes differ across endpoint and intake evidence", missing_markers=missing)


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    paths = {key: bundle_dir / filename for key, filename in FILES.items()}
    checks: list[dict[str, Any]] = []
    endpoint_row, endpoint = endpoint_check(paths["endpoint_json"])
    intake_row, intake = intake_check(paths["adapter_intake"])
    rc_gate_row, rc_gate = rc_gate_check(paths["rc_gate"])
    m6_row, m6 = m6_check(paths["m6"])
    v0_row, v0 = v0_check(paths["v0"])
    checks.extend(
        [
            endpoint_row,
            endpoint_markdown_check(paths["endpoint_markdown"]),
            intake_row,
            cross_hash_check(endpoint, intake),
            rc_gate_row,
            m6_row,
            v0_row,
        ]
    )
    blockers = [row["id"] for row in checks if not row["ok"]]
    decision = "GO_REAL_ADAPTER_EVIDENCE_BUNDLE" if not blockers else "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "bundle_dir": str(bundle_dir),
        "decision": decision,
        "release_bundle_ready": not blockers,
        "m6_rc_claimed_go": decision == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE",
        "checks": checks,
        "blockers": blockers,
        "summary": {
            "endpoint_source": endpoint.get("source") if endpoint else None,
            "endpoint_self_test": endpoint.get("self_test") if endpoint else None,
            "adapter_sha256": endpoint.get("adapter_sha256") if endpoint else None,
            "artifact_manifest_sha256": endpoint.get("artifact_manifest_sha256") if endpoint else None,
            "rc_gate_status": rc_gate.get("status") if rc_gate else None,
            "m6_decision": m6.get("decision") if m6 else None,
            "v0_decision": v0.get("decision") if v0 else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a real adapter CUDA evidence bundle before M6-RC/v0 closeout.")
    parser.add_argument("--bundle-dir", default="artifacts/review")
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    args = parser.parse_args()

    report = verify_bundle(Path(args.bundle_dir))
    expected_decision = "GO_REAL_ADAPTER_EVIDENCE_BUNDLE" if args.expected_decision == "GO" else "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    report["expected_decision"] = expected_decision
    report["decision_matches_expected"] = report["decision"] == expected_decision
    report["verification_ok"] = report["decision_matches_expected"]
    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json_output": args.json_output, "decision": report["decision"], "verification_ok": report["verification_ok"]}, sort_keys=True))
    return 0 if report["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
