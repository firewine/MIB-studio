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


verify = load_module("scripts/verify_m6_rc_evidence.py", "verify_m6_rc_evidence")


ADAPTER_SHA = "a" * 64
MANIFEST_SHA = "b" * 64


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_required_rc_artifacts(root: Path) -> None:
    write_text(
        root / "artifacts/review/fe_v6_evidence.md",
        "Gate: `mib-studio-fe-v6-mockup`\nBrowser Verification Evidence\nrun e2e`: passed\n",
    )
    write_text(
        root / "artifacts/review/docker_real_backend_deps_evidence.md",
        "Decision: `GO_DEPENDENCY_PACKAGING_ONLY`\ntemp_image_backend_import_probe: pass\n",
    )
    write_text(
        root / "artifacts/review/export_adapter_validation_evidence.md",
        "Decision: `GO_STRUCTURAL_ADAPTER_VALIDATION`\nM6-RC remains `NOT_GO`\n",
    )
    write_text(
        root / "artifacts/review/export_adapter_lineage_evidence.md",
        "Decision: `GO_EXPORT_LINEAGE_VALIDATION`\nM6-RC remains `NOT_GO`\n",
    )
    write_text(
        root / "artifacts/review/exported_adapter_load_guard_evidence.md",
        "Decision: `GO_TEST_GUARD_ONLY_M6_NOT_GO`\nfake_backend_requires_explicit_env: true\n",
    )
    write_text(
        root / "artifacts/review/phi_strict_cache_runtime_evidence.md",
        "Decision: `PARTIAL_GO_ENDPOINT_PATH_WITH_FIXTURE_ADAPTER`\nMIB_RUNTIME_ALLOW_FAKE_BACKEND=1\n",
    )
    write_text(
        root / "artifacts/review/real_adapter_inference_evidence.md",
        "Decision: `NOT_GO_REAL_ADAPTER_INFERENCE_BLOCKED`\nreal_trained_adapter_found: false\n",
    )


def write_not_go_review_docs(root: Path) -> None:
    write_text(root / "docs/reviews/M6/FE_REVIEW.md", "Decision: GO\n")
    write_text(
        root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
        "| M6 Export / v0 RC | GO | GO | GO | NO_GO | GO | NO_GO | GO | NO_GO | NO_GO | NOT_GO |\n",
    )
    write_text(
        root / "docs/reviews/M6/CTO_DECISION.md",
        "Decision: NOT_GO\nreal trained adapter\nMIB_RUNTIME_ALLOW_FAKE_BACKEND\n",
    )


def write_go_review_docs(root: Path) -> None:
    write_text(root / "docs/reviews/M6/FE_REVIEW.md", "Decision: GO\n")
    write_text(
        root / "docs/reviews/M6/SIGNOFF_MATRIX.md",
        "| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |\n",
    )
    write_text(root / "docs/reviews/M6/CTO_DECISION.md", "Decision: GO\n")


def write_go_endpoint(root: Path) -> Path:
    evidence = root / "artifacts/review/real_trained_adapter_endpoint_evidence.md"
    write_text(evidence, "structured sidecar owns live endpoint evidence\n")
    write_json(
        evidence.with_suffix(".json"),
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
    return evidence


def review_check(report: dict[str, object]) -> dict[str, object]:
    checks = report["checks"]
    assert isinstance(checks, list)
    match = next(row for row in checks if isinstance(row, dict) and row.get("id") == "m6_review_docs_current")
    assert isinstance(match, dict)
    return match


def test_expected_not_go_accepts_current_blocker_docs_with_missing_endpoint(tmp_path: Path, monkeypatch) -> None:
    write_required_rc_artifacts(tmp_path)
    write_not_go_review_docs(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = verify.evaluate("NOT_GO", "artifacts/review/real_trained_adapter_endpoint_evidence.md")

    assert report["decision"] == "NOT_GO"
    assert report["verification_ok"] is True
    assert report["blockers"] == ["real_trained_adapter_no_fake_endpoint"]
    assert review_check(report)["ok"] is True


def test_expected_go_rejects_complete_endpoint_when_review_docs_are_not_go(tmp_path: Path, monkeypatch) -> None:
    write_required_rc_artifacts(tmp_path)
    write_not_go_review_docs(tmp_path)
    endpoint = write_go_endpoint(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = verify.evaluate("GO", str(endpoint))
    review = review_check(report)

    assert report["decision"] == "NOT_GO"
    assert report["verification_ok"] is False
    assert report["blockers"] == ["m6_review_docs_current"]
    assert report["unexpected_blockers"] == ["m6_review_docs_current"]
    assert review["ok"] is False
    assert review["requirements"] == {
        "fe_review_go": True,
        "signoff_final_go": False,
        "cto_decision_go": False,
    }


def test_expected_go_requires_final_review_docs_and_live_endpoint(tmp_path: Path, monkeypatch) -> None:
    write_required_rc_artifacts(tmp_path)
    write_go_review_docs(tmp_path)
    endpoint = write_go_endpoint(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = verify.evaluate("GO", str(endpoint))

    assert report["decision"] == "GO"
    assert report["verification_ok"] is True
    assert report["blockers"] == []
    assert report["unexpected_blockers"] == []
    assert review_check(report)["ok"] is True
