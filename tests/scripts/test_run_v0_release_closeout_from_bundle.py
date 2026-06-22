from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


closeout = load_module("scripts/run_v0_release_closeout_from_bundle.py", "run_v0_release_closeout_from_bundle")


ADAPTER_SHA = "a" * 64
MANIFEST_SHA = "b" * 64


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def args_for(
    root: Path,
    *,
    bundle_dir: Path | None = None,
    bundle_archive: Path | None = None,
    expected_bundle: str = "GO",
    expected_readiness: str = "GO",
) -> SimpleNamespace:
    return SimpleNamespace(
        bundle_dir=str(bundle_dir) if bundle_dir else None,
        bundle_archive=str(bundle_archive) if bundle_archive else None,
        root=str(root),
        target_dir="artifacts/review",
        expected_bundle_decision=expected_bundle,
        expected_readiness_decision=expected_readiness,
        dry_run=False,
        bundle_verification_output="artifacts/review/real_adapter_evidence_bundle_verification.json",
        promotion_manifest_output="artifacts/review/real_adapter_evidence_bundle_promotion.json",
        readiness_output="artifacts/review/v0_release_readiness_audit.json",
        summary_output="artifacts/review/v0_release_closeout_from_bundle.json",
    )


def write_required_release_docs(root: Path, *, m6_go: bool) -> None:
    write_text(
        root / "docs/reviews/M0/SIGNOFF_MATRIX.md",
        "| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |\nModel catalog strict verification: PASS\nImport boundary report: PASS\n",
    )
    write_text(
        root / "artifacts/review/m1_smoke_recertification_evidence.md",
        "Decision: `GO_M1_SMOKE_CURRENT_ENVIRONMENT`\ntoolchain versions OK\ntests/smoke/test_m1_smoke.py 1 passed\n",
    )
    write_text(
        root / "artifacts/review/fe_v6_evidence.md",
        "Gate: `mib-studio-fe-v6-mockup`\nBrowser Verification Evidence\nrun e2e`: passed\n",
    )
    write_text(
        root / "artifacts/review/desktop_e2e_route_repair_evidence.md",
        "decision: GO_DESKTOP_E2E_ROUTE_REPAIR_M6_NOT_GO\nM1 desktop shell happy path passed\nFE v6 route contract builder passed\nM2 teacher packet preview passed\n",
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
    if m6_go:
        write_text(
            root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
            "| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |\n",
        )
        write_text(root / "docs/reviews/M6/CTO_DECISION.md", "Decision: GO\n")
    else:
        write_text(
            root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
            "| M6 Export / v0 RC | GO | GO | GO | NO_GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |\n",
        )
        write_text(
            root / "docs/reviews/M6/CTO_DECISION.md",
            "Decision: NOT_GO\nreal trained CUDA `lora_adapter` endpoint\nMIB_RUNTIME_ALLOW_FAKE_BACKEND\n",
        )
    write_json(
        root / "artifacts/review/m6_real_adapter_prereq_audit.json",
        {
            "schema_version": "mib_real_adapter_rc_gate_runner.v1",
            "status": "READY_TO_RUN",
            "decision": "READY",
            "errors": [],
            "preflight": [{"id": "host_cuda_visible", "ok": True}],
        },
    )


def write_complete_bundle(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_text(
        root / "real_trained_adapter_endpoint_evidence.md",
        "# Real Trained Adapter Endpoint Evidence\n\nDecision: `GO_REAL_TRAINED_ADAPTER_ENDPOINT`\n\n```yaml\nMIB_RUNTIME_ALLOW_FAKE_BACKEND: absent\n/agents/{agent_id}/run: 200\n/v1/chat/completions: 200\nreal_trained_adapter: true\nadapter_intake_verified: true\nself_test: false\n```\n",
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
            "checks": [{"id": "real_trained_adapter_no_fake_endpoint", "ok": True, "source": "live_docker_capture", "self_test": False}],
        },
    )


def write_archive_from_dir(source: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(source.iterdir()):
            archive.add(path, arcname=path.name)


def test_closeout_promotes_go_archive_and_returns_release_go(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_required_release_docs(root, m6_go=True)
    bundle_dir = tmp_path / "bundle"
    archive = root / "incoming" / "bundle.tar.gz"
    write_complete_bundle(bundle_dir)
    write_archive_from_dir(bundle_dir, archive)

    summary, _promotion_manifest, _bundle_verification, v0_report = closeout.closeout(
        args_for(root, bundle_archive=Path("incoming/bundle.tar.gz"))
    )

    assert summary["status"] == "GO_V0_RELEASE_CLOSEOUT"
    assert summary["closeout_ok"] is True
    assert summary["release_claimed_go"] is True
    assert summary["resolved_bundle_archive"] == str(archive)
    assert v0_report["decision"] == "GO"
    assert (root / "artifacts/review/real_adapter_evidence_bundle_verification.json").is_file()


def test_closeout_refuses_not_go_bundle_before_readiness_go(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_required_release_docs(root, m6_go=True)
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    write_json(
        bundle_dir / "m6_rc_evidence_verification.json",
        {
            "schema_version": "mib_m6_rc_evidence_verification.v1",
            "decision": "NOT_GO",
            "verification_ok": True,
            "blockers": ["real_trained_adapter_no_fake_endpoint"],
            "unexpected_blockers": [],
            "checks": [],
        },
    )

    summary, promotion_manifest, _bundle_verification, v0_report = closeout.closeout(args_for(root, bundle_dir=bundle_dir))

    assert summary["status"] == "NOT_GO_BUNDLE_PROMOTION"
    assert summary["closeout_ok"] is False
    assert summary["release_claimed_go"] is False
    assert promotion_manifest["reason"] == "source_bundle_not_go"
    assert v0_report["decision"] == "NOT_GO"


def test_closeout_keeps_not_go_when_bundle_go_but_m6_review_docs_not_go(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_required_release_docs(root, m6_go=False)
    bundle_dir = tmp_path / "bundle"
    write_complete_bundle(bundle_dir)

    summary, _promotion_manifest, _bundle_verification, v0_report = closeout.closeout(args_for(root, bundle_dir=bundle_dir))

    assert summary["status"] == "NOT_GO_V0_READINESS"
    assert summary["closeout_ok"] is False
    assert summary["release_claimed_go"] is False
    assert v0_report["decision"] == "NOT_GO"
    assert "m6_review_docs_not_current" in v0_report["blockers"]
