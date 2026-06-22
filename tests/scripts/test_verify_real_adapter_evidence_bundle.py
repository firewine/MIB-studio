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


bundle = load_module("scripts/verify_real_adapter_evidence_bundle.py", "verify_real_adapter_evidence_bundle")


ADAPTER_SHA = "a" * 64
MANIFEST_SHA = "b" * 64


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_complete_bundle(root: Path) -> None:
    root.mkdir(exist_ok=True)
    (root / "real_trained_adapter_endpoint_evidence.md").write_text(
        """# Real Trained Adapter Endpoint Evidence

Decision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`

```yaml
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
/agents/{agent_id}/run: 200
/v1/chat/completions: 200
real_trained_adapter: true
adapter_intake_verified: true
self_test: false
```
""",
        encoding="utf-8",
    )
    write_json(
        root / "real_trained_adapter_endpoint_evidence.json",
        {
            "schema_version": "mib_real_adapter_endpoint_evidence.v1",
            "source": "live_docker_capture",
            "decision": "GO_REAL_TRAINED_ADAPTER_ENDPOINT",
            "self_test": False,
            "adapter_intake_verified": True,
            "adapter_sha256": ADAPTER_SHA,
            "artifact_manifest_sha256": MANIFEST_SHA,
            "fake_backend_env_absent": True,
            "readonly_model_cache_mount": True,
            "health_status": 200,
            "native_status": 200,
            "openai_status": 200,
            "native_openai_output_equal": True,
        },
    )
    write_json(
        root / "real_adapter_artifact_intake.json",
        {
            "schema_version": "mib_real_adapter_artifact_intake.v1",
            "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
            "adapter_sha256": ADAPTER_SHA,
            "artifact_manifest_sha256": MANIFEST_SHA,
            "errors": [],
        },
    )
    write_json(
        root / "m6_real_adapter_rc_gate_run.json",
        {
            "schema_version": "mib_real_adapter_rc_gate_runner.v1",
            "status": "GO_M6_REAL_ADAPTER_RC_GATE",
            "decision": "GO",
            "m6_rc_claimed_go": True,
            "errors": [],
            "steps": [
                {"id": "adapter_intake", "returncode": 0},
                {"id": "endpoint_capture", "returncode": 0},
                {"id": "m6_go_verification", "returncode": 0},
            ],
        },
    )
    write_json(
        root / "m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "GO",
            "verification_ok": True,
            "blockers": [],
            "unexpected_blockers": [],
            "checks": [
                {
                    "id": "real_trained_adapter_no_fake_endpoint",
                    "ok": True,
                    "source": "live_docker_capture",
                    "self_test": False,
                }
            ],
        },
    )


def test_verifier_accepts_complete_live_bundle(tmp_path: Path) -> None:
    write_complete_bundle(tmp_path)

    report = bundle.verify_bundle(tmp_path)

    assert report["decision"] == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert report["release_bundle_ready"] is True
    assert report["m6_rc_claimed_go"] is True
    assert report["blockers"] == []


def test_verifier_rejects_self_test_endpoint_bundle(tmp_path: Path) -> None:
    write_complete_bundle(tmp_path)
    endpoint = json.loads((tmp_path / "real_trained_adapter_endpoint_evidence.json").read_text(encoding="utf-8"))
    endpoint.update({"source": "self_test", "self_test": True})
    write_json(tmp_path / "real_trained_adapter_endpoint_evidence.json", endpoint)
    (tmp_path / "real_trained_adapter_endpoint_evidence.md").write_text("self_test: true\n", encoding="utf-8")

    report = bundle.verify_bundle(tmp_path)

    assert report["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert "endpoint_live_no_fake_json" in report["blockers"]
    assert "endpoint_markdown_markers" in report["blockers"]


def test_verifier_cross_checks_endpoint_and_intake_hashes(tmp_path: Path) -> None:
    write_complete_bundle(tmp_path)
    intake = json.loads((tmp_path / "real_adapter_artifact_intake.json").read_text(encoding="utf-8"))
    intake["adapter_sha256"] = "c" * 64
    write_json(tmp_path / "real_adapter_artifact_intake.json", intake)

    report = bundle.verify_bundle(tmp_path)

    assert report["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert "adapter_hash_crosscheck" in report["blockers"]


def test_verifier_rejects_missing_current_bundle(tmp_path: Path) -> None:
    report = bundle.verify_bundle(tmp_path)

    assert report["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert {"endpoint_live_no_fake_json", "adapter_intake_go", "rc_gate_go", "m6_verification_go"} <= set(report["blockers"])
