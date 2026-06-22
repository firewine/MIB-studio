from __future__ import annotations

import importlib.util
import json
import subprocess
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


recert = load_module("scripts/run_v0_release_blocker_recertification.py", "run_v0_release_blocker_recertification")


def completed(command: list[str], returncode: int = 0, stdout: str = "ok", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def write_json(root: Path, path: str, value: dict[str, object]) -> None:
    output = root / path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def args_for(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        root=str(root),
        python="./.venv/bin/python",
        base_model="microsoft/Phi-3.5-mini-instruct",
        image="mib-export:test",
        agent_id="finance.router.v1",
        model_cache_dir="/tmp/mib-strict-model-cache-phi/model_cache",
        adapter_root="/tmp/mib-real-adapter",
        dataset_jsonl="examples/fixtures/router_20.jsonl",
        backend_config="/tmp/mib-real-adapter/backend_config.yaml",
        llamafactory_cli="./.venv/bin/llamafactory-cli",
        scan_root=[str(root), "/tmp/mib-real-adapter"],
        expected_go_candidates=0,
        expected_readiness_decision="NOT_GO",
        expected_bundle_decision="NOT_GO",
        expected_training_status="NOT_READY_CUDA_LORA_TRAINING",
        expected_rc_status="NOT_READY_PRECHECK_FAILED",
        preflight_token="recertification-preflight-token-000000000000",
        candidate_scan_output="artifacts/review/real_adapter_candidate_scan.json",
        training_preflight_output="artifacts/review/real_adapter_cuda_training_prereq_preflight.json",
        rc_prereq_output="artifacts/review/m6_real_adapter_prereq_audit.json",
        adapter_intake_output="artifacts/review/real_adapter_artifact_intake.json",
        endpoint_output="artifacts/review/real_trained_adapter_endpoint_evidence.md",
        endpoint_json_output="artifacts/review/real_trained_adapter_endpoint_evidence.json",
        m6_verification_output="artifacts/review/m6_rc_evidence_verification.json",
        bundle_source_dir="artifacts/review",
        bundle_verification_output="artifacts/review/real_adapter_evidence_bundle_verification.json",
        readiness_output="artifacts/review/v0_release_readiness_audit.json",
        handoff_json_output="artifacts/review/real_adapter_cuda_handoff.json",
        handoff_markdown_output="artifacts/review/real_adapter_cuda_handoff.md",
        handoff_shell_output="artifacts/review/real_adapter_cuda_handoff.sh",
        json_output="artifacts/review/v0_release_blocker_recertification.json",
    )


def write_step_output(root: Path, step_id: str, output: str) -> None:
    if step_id == "candidate_scan":
        write_json(
            root,
            output,
            {
                "decision": "NO_GO_CANDIDATES_FOUND",
                "go_candidate_count": 0,
                "fixture_like_candidate_count": 2,
            },
        )
    elif step_id == "cuda_training_preflight":
        write_json(
            root,
            output,
            {
                "status": "NOT_READY_CUDA_LORA_TRAINING",
                "blockers": [
                    "docker_base_image_env_digest",
                    "strict_model_cache_files",
                    "cuda_visible",
                    "docker_base_image_available",
                ],
            },
        )
    elif step_id == "m6_rc_preflight":
        write_json(
            root,
            output,
            {
                "status": "NOT_READY_PRECHECK_FAILED",
                "decision": "NOT_READY",
                "errors": ["adapter_dir_present: missing adapter directory"],
            },
        )
    elif step_id == "real_adapter_bundle_verification":
        write_json(
            root,
            output,
            {
                "schema_version": "mib_real_adapter_evidence_bundle_verification.v1",
                "decision": "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE",
                "verification_ok": True,
                "release_bundle_ready": False,
                "blockers": ["endpoint_live_no_fake_json"],
            },
        )
    elif step_id == "v0_readiness":
        write_json(
            root,
            output,
            {
                "decision": "NOT_GO",
                "release_ready": False,
                "verification_ok": True,
                "blockers": ["real_trained_adapter_no_fake_endpoint"],
                "unexpected_blockers": [],
            },
        )
    elif step_id == "cuda_handoff":
        write_json(root, output, {"decision": "WAITING_FOR_REAL_ADAPTER_INPUTS"})
        (root / "artifacts/review/real_adapter_cuda_handoff.md").write_text("handoff", encoding="utf-8")
        (root / "artifacts/review/real_adapter_cuda_handoff.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    else:
        raise AssertionError(f"unknown step: {step_id}")


def test_recertification_summarizes_current_expected_not_go(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    seen_steps: list[str] = []

    def runner(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        row = next(item for item in recert.command_plan(args) if item["command"] == command)
        seen_steps.append(row["id"])
        write_step_output(cwd, row["id"], row["output"])
        return completed(command)

    summary = recert.recertify(args, runner=runner)

    assert seen_steps == [
        "candidate_scan",
        "cuda_training_preflight",
        "m6_rc_preflight",
        "real_adapter_bundle_verification",
        "v0_readiness",
        "cuda_handoff",
    ]
    assert summary["schema_version"] == recert.SCHEMA_VERSION
    assert summary["status"] == recert.NOT_GO_STATUS
    assert summary["recertification_ok"] is True
    assert summary["release_claimed_go"] is False
    assert summary["m6_rc_claimed_go"] is False
    assert summary["current_state"]["v0_blockers"] == ["real_trained_adapter_no_fake_endpoint"]
    assert summary["current_state"]["handoff_decision"] == "WAITING_FOR_REAL_ADAPTER_INPUTS"
    assert summary["blocking_reasons"] == [
        "no_go_adapter_candidates",
        "docker_base_image_env_digest",
        "strict_model_cache_files",
        "cuda_visible",
        "docker_base_image_available",
        "adapter_dir_present",
        "endpoint_live_no_fake_json",
        "real_trained_adapter_no_fake_endpoint",
        "WAITING_FOR_REAL_ADAPTER_INPUTS",
    ]
    assert summary["primary_external_handoff"] == "artifacts/review/verified_external_cuda_training_launcher.sh"
    assert summary["operator_next_actions"] == [
        "Run artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host first; it verifies the operator packet before invoking artifacts/review/real_adapter_cuda_training_handoff.sh.",
        "Produce or transfer a real trained adapter under /tmp/mib-real-adapter before rerunning local release checks.",
        "Provide /tmp/mib-real-adapter/adapter with adapter.safetensors and adapter_config.json plus /tmp/mib-real-adapter/manifest.json.",
        "Run ./.venv/bin/python scripts/prepare_strict_model_cache.py --base-model microsoft/Phi-3.5-mini-instruct --backend cuda --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --allow-download --expected-status READY_STRICT_MODEL_CACHE before CUDA training preflight.",
        "Set MIB_DOCKER_BASE_IMAGE_WITH_DIGEST to a digest-pinned CUDA/Python base image on the CUDA host.",
        "Build or pull the required Docker images, including the digest-pinned base image and mib-export:test.",
        "Rerun on a CUDA host where nvidia-smi is visible to the process.",
        "Run the real-adapter M6 RC gate against a live no-fake Docker endpoint and collect accepted JSON/markdown evidence.",
        "Follow artifacts/review/real_adapter_cuda_handoff.sh on the external CUDA host, then transfer the metadata-bearing evidence bundle back.",
    ]
    assert all(row["ok"] for row in summary["expectation_checks"])
    assert summary["operator_next_step"].startswith("Run artifacts/review/verified_external_cuda_training_launcher.sh")


def test_recertification_refuses_failed_child_command(tmp_path: Path) -> None:
    args = args_for(tmp_path)

    def runner(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
        row = next(item for item in recert.command_plan(args) if item["command"] == command)
        if row["id"] == "candidate_scan":
            write_step_output(cwd, row["id"], row["output"])
            return completed(command)
        return completed(command, returncode=2, stderr="boom")

    summary = recert.recertify(args, runner=runner)

    assert summary["status"] == recert.FAILED_STATUS
    assert summary["recertification_ok"] is False
    assert summary["release_claimed_go"] is False
    assert summary["failed_step"] == "cuda_training_preflight"
    assert summary["blocking_reasons"][0] == "child_command_failed:cuda_training_preflight"
    assert summary["operator_next_actions"][0] == (
        "Inspect the failed child command stderr/stdout tail in commands, fix the tool/runtime failure, and rerun recertification."
    )
    assert summary["operator_next_actions"][1] == (
        "Run artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host first; it verifies the operator packet before invoking artifacts/review/real_adapter_cuda_training_handoff.sh."
    )
    assert [row["id"] for row in summary["commands"]] == ["candidate_scan", "cuda_training_preflight"]
