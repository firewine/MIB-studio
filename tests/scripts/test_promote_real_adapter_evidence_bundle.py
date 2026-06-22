from __future__ import annotations

import importlib.util
import io
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


promotion = load_module("scripts/promote_real_adapter_evidence_bundle.py", "promote_real_adapter_evidence_bundle")


ADAPTER_SHA = "a" * 64
MANIFEST_SHA = "b" * 64


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def args_for(
    tmp_path: Path,
    *,
    bundle_dir: Path | None = None,
    bundle_archive: Path | None = None,
    target_dir: Path,
    expected: str = "GO",
    dry_run: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        bundle_dir=str(bundle_dir) if bundle_dir else None,
        bundle_archive=str(bundle_archive) if bundle_archive else None,
        target_dir=str(target_dir),
        expected_decision=expected,
        dry_run=dry_run,
        verification_output=str(tmp_path / "verification.json"),
        promotion_manifest_output=str(tmp_path / "promotion.json"),
    )


def write_complete_bundle(root: Path) -> None:
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


def archive_metadata(source: Path) -> tuple[dict[str, object], dict[str, object]]:
    verification = promotion.add_expected(promotion.verifier.verify_bundle(source), promotion.GO_DECISION)
    files = []
    for logical_name, filename in promotion.fixed_bundle_files().items():
        path = source / filename
        files.append(
            {
                "logical_name": logical_name,
                "filename": filename,
                "source_path": str(path),
                "bundle_path": str(path),
                "present": path.is_file(),
                "copied": False,
                "sha256": promotion.sha256_file(path) if path.is_file() else None,
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    manifest = {
        "schema_version": "mib_real_adapter_evidence_bundle_manifest.v1",
        "source_dir": str(source),
        "bundle_dir": str(source),
        "expected_decision": verification["expected_decision"],
        "decision_matches_expected": verification["decision_matches_expected"],
        "files": files,
        "missing_files": [row["logical_name"] for row in files if not row["present"]],
        "verification_summary": {
            "decision": verification["decision"],
            "release_bundle_ready": verification["release_bundle_ready"],
            "m6_rc_claimed_go": verification["m6_rc_claimed_go"],
            "blockers": verification["blockers"],
        },
    }
    return manifest, verification


def add_json_member(archive: tarfile.TarFile, name: str, payload: dict[str, object]) -> None:
    data = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def write_archive_from_dir(source: Path, archive_path: Path, *, include_metadata: bool = True) -> None:
    manifest, verification = archive_metadata(source)
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in sorted(source.iterdir()):
            archive.add(path, arcname=path.name)
        if include_metadata:
            add_json_member(archive, "real_adapter_evidence_bundle_manifest.json", manifest)
            add_json_member(archive, "real_adapter_evidence_bundle_verification.json", verification)


def test_promotes_complete_go_bundle_into_target(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    target_dir = tmp_path / "review"
    write_complete_bundle(bundle_dir)
    (bundle_dir / "unrelated.txt").write_text("must not be promoted\n", encoding="utf-8")

    manifest, verification = promotion.promote_bundle(args_for(tmp_path, bundle_dir=bundle_dir, target_dir=target_dir))

    assert verification["decision"] == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert manifest["promoted"] is True
    assert manifest["promotion_ok"] is True
    assert {row["filename"] for row in manifest["copied_files"]} == set(promotion.fixed_bundle_files().values())
    assert all(row["copied"] for row in manifest["copied_files"])
    assert (target_dir / "real_trained_adapter_endpoint_evidence.json").is_file()
    assert not (target_dir / "unrelated.txt").exists()


def test_promotes_complete_go_archive_into_target(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    archive_path = tmp_path / "real_adapter_evidence_bundle.tar.gz"
    target_dir = tmp_path / "review"
    write_complete_bundle(bundle_dir)
    (bundle_dir / "unrelated.txt").write_text("must not be promoted\n", encoding="utf-8")
    write_archive_from_dir(bundle_dir, archive_path)

    manifest, verification = promotion.promote_bundle(args_for(tmp_path, bundle_archive=archive_path, target_dir=target_dir))

    assert verification["decision"] == "GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert manifest["promoted"] is True
    assert manifest["promotion_ok"] is True
    assert manifest["bundle_archive"] == str(archive_path)
    assert manifest["bundle_archive_sha256"]
    assert (target_dir / "real_trained_adapter_endpoint_evidence.json").is_file()
    assert not (target_dir / "unrelated.txt").exists()


def test_rejects_go_archive_without_builder_metadata(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    archive_path = tmp_path / "real_adapter_evidence_bundle.tar.gz"
    target_dir = tmp_path / "review"
    write_complete_bundle(bundle_dir)
    write_archive_from_dir(bundle_dir, archive_path, include_metadata=False)

    manifest, verification = promotion.promote_bundle(args_for(tmp_path, bundle_archive=archive_path, target_dir=target_dir))

    assert verification["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert "archive_metadata_not_verified" in verification["blockers"]
    assert manifest["promoted"] is False
    assert manifest["promotion_ok"] is False
    assert manifest["reason"] == "archive_metadata_not_verified"
    assert "manifest:missing" in manifest["archive_metadata"]["failures"]
    assert "verification:missing" in manifest["archive_metadata"]["failures"]
    assert not target_dir.exists() or list(target_dir.iterdir()) == []


def test_rejects_unsafe_bundle_archive_member_path(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    target_dir = tmp_path / "review"
    payload = b"{}"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("../escape.json")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))

    try:
        promotion.promote_bundle(args_for(tmp_path, bundle_archive=archive_path, target_dir=target_dir))
    except ValueError as exc:
        assert "unsafe archive" in str(exc)
    else:
        raise AssertionError("unsafe archive member should be rejected")


def test_not_go_dry_run_writes_manifest_without_copying(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    target_dir = tmp_path / "review"
    bundle_dir.mkdir()
    target_dir.mkdir()
    (target_dir / "real_trained_adapter_endpoint_evidence.json").write_text("stale target evidence\n", encoding="utf-8")
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

    manifest, verification = promotion.promote_bundle(
        args_for(tmp_path, bundle_dir=bundle_dir, target_dir=target_dir, expected="NOT_GO", dry_run=True)
    )

    assert verification["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert manifest["promotion_ok"] is True
    assert manifest["promoted"] is False
    assert manifest["reason"] == "dry_run"
    assert manifest["copied_files"] == []
    assert (target_dir / "real_trained_adapter_endpoint_evidence.json").read_text(encoding="utf-8") == "stale target evidence\n"


def test_expected_go_does_not_copy_not_go_bundle(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    target_dir = tmp_path / "review"
    bundle_dir.mkdir()
    target_dir.mkdir()
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

    manifest, verification = promotion.promote_bundle(args_for(tmp_path, bundle_dir=bundle_dir, target_dir=target_dir))

    assert verification["decision"] == "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"
    assert manifest["promotion_ok"] is False
    assert manifest["promoted"] is False
    assert manifest["reason"] == "source_bundle_not_go"
    assert list(target_dir.iterdir()) == []


def test_rejects_same_bundle_and_target_dir(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    args = args_for(tmp_path, bundle_dir=bundle_dir, target_dir=bundle_dir)

    try:
        promotion.promote_bundle(args)
    except ValueError as exc:
        assert "--bundle-dir and --target-dir must be different" in str(exc)
    else:
        raise AssertionError("same bundle and target directory should be rejected")
