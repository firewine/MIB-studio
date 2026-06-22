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


packet = load_module("scripts/build_external_cuda_operator_packet.py", "build_external_cuda_operator_packet")


def write_text(root: Path, path: str, text: str = "x") -> None:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def write_json(root: Path, path: str, value: dict[str, object]) -> None:
    write_text(root, path, json.dumps(value, sort_keys=True) + "\n")


def populate_root(root: Path, *, training_claims_go: bool = False) -> None:
    for role, path in packet.REQUIRED_COMMITTED_FILES.items():
        if path.endswith(".json"):
            write_json(root, path, {"role": role})
        else:
            write_text(root, path, f"{role}\n")
    write_json(
        root,
        "artifacts/review/real_adapter_cuda_training_handoff.json",
        {
            "status": "PREPARED_NOT_RUN",
            "release_claimed_go": training_claims_go,
            "package_readiness_checks": [
                {"id": "dataset_jsonl_present", "path": "examples/fixtures/router_20.jsonl"},
                {"id": "python_executable_present", "path": "./.venv/bin/python"},
            ],
            "command_sequence": [
                {"id": "resolve_cuda_base_image"},
                {"id": "prepare_strict_model_cache"},
                {"id": "preflight_cuda_training"},
                {"id": "train_real_adapter"},
            ],
        },
    )
    write_json(
        root,
        "artifacts/review/real_adapter_cuda_handoff.json",
        {
            "command_sequence": [{"id": "adapter_intake"}, {"id": "endpoint_evidence"}],
            "post_transfer_closeout_commands": [{"id": "local_closeout_after_bundle_transfer"}],
        },
    )
    write_json(
        root,
        "artifacts/review/v0_release_blocker_recertification.json",
        {
            "status": "NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION",
            "release_claimed_go": False,
            "primary_external_handoff": "artifacts/review/verified_external_cuda_training_launcher.sh",
        },
    )


def args_for(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        root=str(root),
        training_handoff_json="artifacts/review/real_adapter_cuda_training_handoff.json",
        rc_handoff_json="artifacts/review/real_adapter_cuda_handoff.json",
        recertification_json="artifacts/review/v0_release_blocker_recertification.json",
        git_head="unitsha",
        git_branch="main",
        remote_origin="git@example.test:repo.git",
        json_output=str(root / "packet.json"),
        markdown_output=str(root / "packet.md"),
    )


def test_packet_is_commit_pinned_and_names_primary_handoff(tmp_path: Path) -> None:
    populate_root(tmp_path)

    result = packet.build_packet(args_for(tmp_path))
    markdown = packet.render_markdown(result)

    assert result["schema_version"] == packet.SCHEMA_VERSION
    assert result["status"] == packet.STATUS
    assert result["release_claimed_go"] is False
    assert result["m6_rc_claimed_go"] is False
    assert result["git"]["head"] == "unitsha"
    assert result["primary_external_handoff"] == "artifacts/review/verified_external_cuda_training_launcher.sh"
    assert result["downstream_training_handoff"] == "artifacts/review/real_adapter_cuda_training_handoff.sh"
    assert result["recertification_primary_external_handoff"] == "artifacts/review/verified_external_cuda_training_launcher.sh"
    assert result["primary_handoff_status"] == "PREPARED_NOT_RUN"
    assert result["downstream_training_handoff_status"] == "PREPARED_NOT_RUN"
    assert [row["id"] for row in result["package_readiness_checks"]] == [
        "dataset_jsonl_present",
        "python_executable_present",
    ]
    assert result["command_order"]["training_handoff"] == [
        "resolve_cuda_base_image",
        "prepare_strict_model_cache",
        "preflight_cuda_training",
        "train_real_adapter",
    ]
    assert result["command_order"]["post_transfer_closeout"] == ["local_closeout_after_bundle_transfer"]
    assert any(row["path"] == "artifacts/review/verified_external_cuda_training_launcher.sh" for row in result["required_committed_files"])
    assert any(row["path"] == "artifacts/review/real_adapter_cuda_training_handoff.sh" for row in result["required_committed_files"])
    assert any(row["path"] == "scripts/prepare_strict_model_cache.py" for row in result["required_committed_files"])
    assert "verified_external_cuda_training_launcher.sh" in result["operator_sequence"][1]
    assert "real_adapter_cuda_training_handoff.sh" in result["operator_sequence"][1]
    assert "model weights" in result["forbidden_committed_artifacts"]
    assert "raw live endpoint transcripts" in result["forbidden_committed_artifacts"]
    assert "git_head: unitsha" in markdown
    assert "Forbidden Committed Artifacts" in markdown


def test_packet_refuses_go_claiming_handoff(tmp_path: Path) -> None:
    populate_root(tmp_path, training_claims_go=True)

    try:
        packet.build_packet(args_for(tmp_path))
    except ValueError as exc:
        assert "GO-claiming" in str(exc)
    else:
        raise AssertionError("GO-claiming handoff should be rejected")
