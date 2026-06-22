from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bundle = load_module("scripts/build_real_adapter_evidence_bundle.py", "build_real_adapter_evidence_bundle")


ADAPTER_SHA = "a" * 64
MANIFEST_SHA = "b" * 64


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def args_for(tmp_path: Path, *, source: Path, expected: str = "GO") -> SimpleNamespace:
    return SimpleNamespace(
        source_dir=str(source),
        bundle_dir=str(tmp_path / "bundle"),
        expected_decision=expected,
        verification_output=str(tmp_path / "verification.json"),
        manifest_output=str(tmp_path / "manifest.json"),
    )


def write_complete_source(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
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


def test_bundle_builder_copies_complete_live_bundle_and_verifies_go(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write_complete_source(source)
    (source / "unrelated.txt").write_text("not part of release evidence\n", encoding="utf-8")

    manifest, verification = bundle.build_bundle(args_for(tmp_path, source=source, expected="GO"))

    assert verification["decision"] == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert verification["verification_ok"] is True
    assert manifest["missing_files"] == []
    assert all(row["present"] for row in manifest["files"])
    assert all(row["sha256"] for row in manifest["files"])
    assert not (tmp_path / "bundle" / "unrelated.txt").exists()


def test_bundle_builder_removes_stale_fixed_files_before_not_go_verification(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    write_json(
        source / "m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "NOT_GO",
            "verification_ok": True,
            "blockers": ["real_trained_adapter_no_fake_endpoint"],
            "unexpected_blockers": [],
            "checks": [],
        },
    )
    stale_bundle = tmp_path / "bundle"
    write_complete_source(stale_bundle)

    manifest, verification = bundle.build_bundle(args_for(tmp_path, source=source, expected="NOT_GO"))

    assert "endpoint_json" in manifest["missing_files"]
    assert "adapter_intake" in manifest["missing_files"]
    assert not (stale_bundle / "real_trained_adapter_endpoint_evidence.json").exists()
    assert verification["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert verification["verification_ok"] is True
    assert "endpoint_live_no_fake_json" in verification["blockers"]


def test_bundle_builder_rejects_same_source_and_bundle_dir(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    args = SimpleNamespace(
        source_dir=str(source),
        bundle_dir=str(source),
        expected_decision="NOT_GO",
        verification_output=str(tmp_path / "verification.json"),
        manifest_output=str(tmp_path / "manifest.json"),
    )

    try:
        bundle.build_bundle(args)
    except ValueError as exc:
        assert "--source-dir and --bundle-dir must be different" in str(exc)
    else:
        raise AssertionError("same source and bundle directory should be rejected")
