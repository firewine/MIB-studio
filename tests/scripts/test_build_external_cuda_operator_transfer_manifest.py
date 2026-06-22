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


manifest_builder = load_module(
    "scripts/build_external_cuda_operator_transfer_manifest.py",
    "build_external_cuda_operator_transfer_manifest",
)


def write_text(root: Path, path: str, text: str = "x\n") -> Path:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def write_json(root: Path, path: str, payload: dict[str, object]) -> Path:
    return write_text(root, path, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def args_for(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        root=str(root),
        packet_json="artifacts/review/external_cuda_operator_packet.json",
        packet_verification_json="artifacts/review/external_cuda_operator_packet_verification.json",
    )


def create_ready_inputs(
    root: Path,
    *,
    verification_decision: str | None = None,
    verification_ok: bool = True,
    operator_packet_ready: bool = True,
    verification_warnings: list[str] | None = None,
    release_claimed_go: bool = False,
) -> tuple[Path, Path]:
    required_paths = [
        manifest_builder.VERIFIED_LAUNCHER_HANDOFF,
        manifest_builder.TRAINING_HANDOFF,
        manifest_builder.TRANSFER_MANIFEST_BUILDER,
        "scripts/prepare_strict_model_cache.py",
    ]
    for path in required_paths:
        write_text(root, path, f"{path}\n")

    packet = {
        "schema_version": manifest_builder.PACKET_SCHEMA_VERSION,
        "status": "PREPARED_NOT_RUN",
        "release_claimed_go": release_claimed_go,
        "m6_rc_claimed_go": False,
        "git": {"head": "packetsha"},
        "primary_external_handoff": manifest_builder.VERIFIED_LAUNCHER_HANDOFF,
        "downstream_training_handoff": manifest_builder.TRAINING_HANDOFF,
        "required_committed_files": [{"path": path, "role": Path(path).name} for path in required_paths],
    }
    verification = {
        "schema_version": manifest_builder.PACKET_VERIFICATION_SCHEMA_VERSION,
        "decision": verification_decision or manifest_builder.GO_PACKET_VERIFICATION,
        "verification_ok": verification_ok,
        "operator_packet_ready": operator_packet_ready,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "packet_handoff_source_commit": "packetsha",
        "warnings": verification_warnings or [],
        "summary": {"forbidden_tracked_artifacts": []},
    }
    packet_path = write_json(root, "artifacts/review/external_cuda_operator_packet.json", packet)
    verification_path = write_json(root, "artifacts/review/external_cuda_operator_packet_verification.json", verification)
    return packet_path, verification_path


def test_ready_manifest_requires_full_checkout_and_no_go_claims(tmp_path: Path) -> None:
    create_ready_inputs(tmp_path)

    result = manifest_builder.build_manifest(args_for(tmp_path))
    markdown = manifest_builder.render_markdown(result)

    assert result["schema_version"] == manifest_builder.SCHEMA_VERSION
    assert result["status"] == manifest_builder.READY_STATUS
    assert result["release_claimed_go"] is False
    assert result["m6_rc_claimed_go"] is False
    assert result["full_checkout_required"] is True
    assert result["partial_file_archive_allowed"] is False
    assert result["transfer_model"] == "full_repository_checkout_required"
    assert result["packet_handoff_source_commit"] == "packetsha"
    assert result["blockers"] == []
    assert any(row["path"] == manifest_builder.VERIFIED_LAUNCHER_HANDOFF for row in result["required_current_checkout_files"])
    assert "real trained CUDA lora_adapter no-fake Docker endpoint evidence" in result["operator_notes"][2]
    assert "full repository checkout required" in markdown
    assert "packet_handoff_source_commit: packetsha" in markdown


def test_not_ready_when_packet_verification_not_go(tmp_path: Path) -> None:
    create_ready_inputs(
        tmp_path,
        verification_decision="NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION",
        verification_ok=False,
        operator_packet_ready=False,
    )

    result = manifest_builder.build_manifest(args_for(tmp_path))

    assert result["status"] == manifest_builder.NOT_READY_STATUS
    assert "packet_verification_go" in result["blockers"]


def test_not_ready_when_verifier_warnings_are_present(tmp_path: Path) -> None:
    create_ready_inputs(tmp_path, verification_warnings=["packet source checkout warning"])

    result = manifest_builder.build_manifest(args_for(tmp_path))

    assert result["status"] == manifest_builder.NOT_READY_STATUS
    assert "packet_verification_warnings_empty" in result["blockers"]


def test_not_ready_when_release_go_is_claimed(tmp_path: Path) -> None:
    create_ready_inputs(tmp_path, release_claimed_go=True)

    result = manifest_builder.build_manifest(args_for(tmp_path))

    assert result["status"] == manifest_builder.NOT_READY_STATUS
    assert "release_claimed_go_false" in result["blockers"]
