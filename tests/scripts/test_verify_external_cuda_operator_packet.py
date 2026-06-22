from __future__ import annotations

import hashlib
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


verifier = load_module("scripts/verify_external_cuda_operator_packet.py", "verify_external_cuda_operator_packet")


def write_text(root: Path, path: str, text: str = "x\n") -> Path:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return output


def write_json(root: Path, path: str, payload: dict[str, object]) -> Path:
    return write_text(root, path, json.dumps(payload, sort_keys=True, indent=2) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_row(root: Path, role: str, path: str) -> dict[str, object]:
    file_path = write_text(root, path, f"{role}\n")
    return {
        "role": role,
        "path": path,
        "sha256": sha256(file_path),
        "size_bytes": file_path.stat().st_size,
    }


def readiness_rows() -> list[dict[str, object]]:
    return [
        {
            "id": check_id,
            "path": f"/tmp/{check_id}",
            "required_before_run": True,
            "shell_guard": True,
        }
        for check_id in verifier.REQUIRED_READINESS_IDS
    ]


def write_packet(root: Path, *, release_claimed_go: bool = False, bad_hash: bool = False) -> Path:
    rows = [
        required_row(root, "training_handoff_shell", verifier.PRIMARY_HANDOFF),
        required_row(root, "training_handoff_json", "artifacts/review/real_adapter_cuda_training_handoff.json"),
        required_row(root, "rc_handoff_shell", "artifacts/review/real_adapter_cuda_handoff.sh"),
    ]
    if bad_hash:
        rows[0]["sha256"] = "0" * 64
    packet = {
        "schema_version": verifier.PACKET_SCHEMA_VERSION,
        "status": verifier.EXPECTED_STATUS,
        "release_claimed_go": release_claimed_go,
        "m6_rc_claimed_go": False,
        "git": {"head": "unitsha"},
        "primary_external_handoff": verifier.PRIMARY_HANDOFF,
        "required_committed_files": rows,
        "package_readiness_checks": readiness_rows(),
        "command_order": {
            "training_handoff": verifier.REQUIRED_TRAINING_COMMANDS,
            "rc_handoff": verifier.REQUIRED_RC_COMMANDS,
            "post_transfer_closeout": verifier.REQUIRED_CLOSEOUT_COMMANDS,
        },
        "forbidden_committed_artifacts": verifier.REQUIRED_FORBIDDEN_LABELS,
    }
    return write_json(root, "artifacts/review/external_cuda_operator_packet.json", packet)


def test_verifier_accepts_ready_operator_packet(tmp_path: Path) -> None:
    packet_path = write_packet(tmp_path)

    report = verifier.verify_packet(tmp_path, packet_path)

    assert report["decision"] == verifier.GO_DECISION
    assert report["operator_packet_ready"] is True
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert report["primary_external_handoff"] == verifier.PRIMARY_HANDOFF
    assert report["blockers"] == []


def test_verifier_rejects_required_file_hash_mismatch(tmp_path: Path) -> None:
    packet_path = write_packet(tmp_path, bad_hash=True)

    report = verifier.verify_packet(tmp_path, packet_path)

    assert report["decision"] == verifier.NOT_GO_DECISION
    assert "required_committed_file_hashes" in report["blockers"]


def test_verifier_rejects_packet_go_claim(tmp_path: Path) -> None:
    packet_path = write_packet(tmp_path, release_claimed_go=True)

    report = verifier.verify_packet(tmp_path, packet_path)

    assert report["decision"] == verifier.NOT_GO_DECISION
    assert "packet_contract" in report["blockers"]


def test_forbidden_tracked_file_matching() -> None:
    matches = verifier.forbidden_tracked_matches(
        [
            "artifacts/review/external_cuda_operator_packet.json",
            "artifacts/review/real_adapter_evidence_bundle.tar.gz",
            "models/adapter/adapter.safetensors",
            "models/adapter/adapter_model.bin",
        ]
    )

    assert "artifacts/review/real_adapter_evidence_bundle.tar.gz" in matches
    assert "models/adapter/adapter.safetensors" in matches
    assert "models/adapter/adapter_model.bin" in matches
    assert "artifacts/review/external_cuda_operator_packet.json" not in matches
