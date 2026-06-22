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


gate = load_module("scripts/run_m6_real_adapter_rc_gate.py", "run_m6_real_adapter_rc_gate")


def args_for(
    tmp_path: Path,
    *,
    token: str = "x" * 32,
    plan_only: bool = False,
    preflight_only: bool = False,
    endpoint_evidence_only: bool = False,
    m6_verification_only: bool = False,
) -> SimpleNamespace:
    adapter_dir = tmp_path / "run" / "adapter"
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "adapter.safetensors").write_bytes(b"real adapter placeholder for preflight presence")
    (adapter_dir / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "run" / "manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    model_cache = tmp_path / "model-cache"
    model_cache.mkdir()
    return SimpleNamespace(
        adapter_dir=str(adapter_dir),
        adapter_manifest=str(manifest),
        base_model="microsoft/Phi-3.5-mini-instruct",
        image="mib-export:test",
        agent_id="finance.router.v1",
        model_cache_dir=str(model_cache),
        host_port=18084,
        container_name="mib-real-adapter-rc-gate-test",
        token=token,
        input_text="finance_income income calculation",
        timeout_seconds=3,
        step_timeout_seconds=5,
        endpoint_timeout_seconds=5,
        keep_container=False,
        adapter_intake_json_output=str(tmp_path / "real_adapter_artifact_intake.json"),
        endpoint_output=str(tmp_path / "real_trained_adapter_endpoint_evidence.md"),
        endpoint_json_output=str(tmp_path / "real_trained_adapter_endpoint_evidence.json"),
        m6_json_output=str(tmp_path / "m6_rc_evidence_verification.json"),
        json_output=str(tmp_path / "gate.json"),
        plan_only=plan_only,
        preflight_only=preflight_only,
        endpoint_evidence_only=endpoint_evidence_only,
        m6_verification_only=m6_verification_only,
    )


def write_json(path: str, payload: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_manifest_with_adapter_sha(args: SimpleNamespace, adapter_sha: str) -> None:
    Path(args.adapter_manifest).write_text(json.dumps({"adapter_sha256": adapter_sha}, sort_keys=True) + "\n", encoding="utf-8")


def write_endpoint_ready_artifacts(args: SimpleNamespace) -> None:
    write_json(
        args.adapter_intake_json_output,
        {
            "schema_version": "mib_real_adapter_artifact_intake.v1",
            "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
            "adapter_sha256": "a" * 64,
            "artifact_manifest_sha256": "b" * 64,
            "errors": [],
        },
    )
    Path(args.endpoint_output).write_text("live endpoint evidence\n", encoding="utf-8")
    write_json(
        args.endpoint_json_output,
        {
            "schema_version": "mib_real_adapter_endpoint_evidence.v1",
            "source": "live_docker_capture",
            "self_test": False,
            "decision": "GO_REAL_TRAINED_ADAPTER_ENDPOINT",
        },
    )
    prior_args = SimpleNamespace(**vars(args))
    prior_args.endpoint_evidence_only = True
    prior_args.m6_verification_only = False
    prior = gate.base_summary(prior_args)
    prior.update(
        {
            "status": "GO_REAL_ADAPTER_ENDPOINT_EVIDENCE_READY_M6_NOT_CLAIMED",
            "decision": "ENDPOINT_EVIDENCE_READY",
            "m6_rc_claimed_go": False,
            "steps": [
                {"id": "adapter_intake", "returncode": 0, "command": ["<redacted>"], "stdout_tail": "ok", "stderr_tail": ""},
                {"id": "endpoint_capture", "returncode": 0, "command": ["<redacted>"], "stdout_tail": "ok", "stderr_tail": ""},
            ],
        }
    )
    write_json(args.json_output, prior)


def test_gate_runner_chains_intake_capture_and_m6_go(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        script = command[1] if len(command) > 1 else ""
        if "verify_real_adapter_artifact.py" in script:
            write_json(
                args.adapter_intake_json_output,
                {
                    "schema_version": "mib_real_adapter_artifact_intake.v1",
                    "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
                    "adapter_sha256": "a" * 64,
                    "artifact_manifest_sha256": "b" * 64,
                    "errors": [],
                },
            )
        elif "capture_real_adapter_endpoint_evidence.py" in script:
            Path(args.endpoint_output).write_text("live endpoint evidence\n", encoding="utf-8")
            write_json(
                args.endpoint_json_output,
                {
                    "schema_version": "mib_real_adapter_endpoint_evidence.v1",
                    "source": "live_docker_capture",
                    "self_test": False,
                    "decision": "GO_REAL_TRAINED_ADAPTER_ENDPOINT",
                },
            )
        elif "verify_m6_rc_evidence.py" in script:
            write_json(
                args.m6_json_output,
                {
                    "schema_version": "mib_m6_rc_evidence_verification.v1",
                    "decision": "GO",
                    "verification_ok": True,
                },
            )
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "GO_M6_REAL_ADAPTER_RC_GATE"
    assert [row["id"] for row in summary["steps"]] == ["adapter_intake", "endpoint_capture", "m6_go_verification"]
    script_commands = [command for command in commands if len(command) > 1 and command[1].endswith(".py")]
    assert [Path(command[1]).name for command in script_commands] == [
        "verify_real_adapter_artifact.py",
        "capture_real_adapter_endpoint_evidence.py",
        "verify_m6_rc_evidence.py",
    ]
    assert json.dumps(summary).find(args.token) == -1
    assert "<redacted-token>" in json.dumps(summary)


def test_gate_runner_stops_before_endpoint_when_intake_command_fails(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if len(command) > 1 and command[1].endswith(".py"):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="adapter rejected")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_GO_STEP_FAILED"
    assert summary["decision"] == "NOT_GO"
    script_commands = [command for command in commands if len(command) > 1 and command[1].endswith(".py")]
    assert [Path(command[1]).name for command in script_commands] == ["verify_real_adapter_artifact.py"]
    assert summary["m6_rc_claimed_go"] is False


def test_gate_runner_endpoint_evidence_only_stops_before_m6_go_without_claiming_rc(tmp_path: Path) -> None:
    args = args_for(tmp_path, endpoint_evidence_only=True)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        script = command[1] if len(command) > 1 else ""
        if "verify_real_adapter_artifact.py" in script:
            write_json(
                args.adapter_intake_json_output,
                {
                    "schema_version": "mib_real_adapter_artifact_intake.v1",
                    "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
                    "adapter_sha256": "a" * 64,
                    "artifact_manifest_sha256": "b" * 64,
                    "errors": [],
                },
            )
        elif "capture_real_adapter_endpoint_evidence.py" in script:
            Path(args.endpoint_output).write_text("live endpoint evidence\n", encoding="utf-8")
            write_json(
                args.endpoint_json_output,
                {
                    "schema_version": "mib_real_adapter_endpoint_evidence.v1",
                    "source": "live_docker_capture",
                    "self_test": False,
                    "decision": "GO_REAL_TRAINED_ADAPTER_ENDPOINT",
                },
            )
        elif "verify_m6_rc_evidence.py" in script:
            raise AssertionError("endpoint-evidence-only must not run M6 GO verification")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "GO_REAL_ADAPTER_ENDPOINT_EVIDENCE_READY_M6_NOT_CLAIMED"
    assert summary["decision"] == "ENDPOINT_EVIDENCE_READY"
    assert summary["m6_rc_claimed_go"] is False
    assert [row["id"] for row in summary["steps"]] == ["adapter_intake", "endpoint_capture"]
    assert "docs/reviews/M6/SIGNOFF_MATRIX.md" in summary["next_required_action"]
    script_commands = [command for command in commands if len(command) > 1 and command[1].endswith(".py")]
    assert [Path(command[1]).name for command in script_commands] == [
        "verify_real_adapter_artifact.py",
        "capture_real_adapter_endpoint_evidence.py",
    ]


def test_gate_runner_m6_verification_only_uses_existing_endpoint_evidence(tmp_path: Path) -> None:
    args = args_for(tmp_path, m6_verification_only=True)
    write_endpoint_ready_artifacts(args)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        script = command[1] if len(command) > 1 else ""
        if "verify_m6_rc_evidence.py" in script:
            write_json(
                args.m6_json_output,
                {
                    "schema_version": "mib_m6_rc_evidence_verification.v1",
                    "decision": "GO",
                    "verification_ok": True,
                    "blockers": [],
                    "unexpected_blockers": [],
                },
            )
            return subprocess.CompletedProcess(command, 0, stdout="m6 ok", stderr="")
        raise AssertionError(f"m6-verification-only must not run non-M6 command: {command}")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "GO_M6_REAL_ADAPTER_RC_GATE"
    assert summary["decision"] == "GO"
    assert summary["m6_rc_claimed_go"] is True
    assert [row["id"] for row in summary["steps"]] == ["adapter_intake", "endpoint_capture", "m6_go_verification"]
    assert [Path(command[1]).name for command in commands] == ["verify_m6_rc_evidence.py"]
    assert summary["preflight"][0]["id"] == "previous_endpoint_only_gate_summary"
    assert all(row["ok"] for row in summary["preflight"])


def test_gate_runner_m6_verification_only_refuses_missing_endpoint_summary(tmp_path: Path) -> None:
    args = args_for(tmp_path, m6_verification_only=True)

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise AssertionError("m6-verification-only must not execute without previous endpoint evidence")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_GO_EXISTING_ENDPOINT_EVIDENCE"
    assert summary["decision"] == "NOT_GO"
    assert summary["m6_rc_claimed_go"] is False
    assert summary["steps"] == []
    assert any(row["id"] == "previous_endpoint_only_gate_summary" and row["ok"] is False for row in summary["preflight"])


def test_gate_runner_preflight_only_reports_not_ready_without_executing_steps(tmp_path: Path) -> None:
    args = args_for(tmp_path, preflight_only=True)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="No such image")
        if command == ["nvidia-smi"]:
            return subprocess.CompletedProcess(command, 127, stdout="", stderr="nvidia-smi: not found")
        raise AssertionError(f"unexpected command in preflight-only: {command}")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_READY_PRECHECK_FAILED"
    assert summary["decision"] == "NOT_READY"
    assert summary["steps"] == []
    assert "docker_image_available" in {row["id"] for row in summary["preflight"]}
    image_lineage = next(row for row in summary["preflight"] if row["id"] == "docker_image_adapter_matches_adapter_manifest")
    assert image_lineage["ok"] is True
    assert image_lineage["skipped"] is True
    assert "host_cuda_visible" in {row["id"] for row in summary["preflight"]}
    assert all(not (len(command) > 1 and command[1].endswith(".py")) for command in commands)
    assert summary["m6_rc_claimed_go"] is False


def test_gate_runner_preflight_checks_docker_image_adapter_lineage_when_manifest_hash_exists(tmp_path: Path) -> None:
    args = args_for(tmp_path, preflight_only=True)
    write_manifest_with_adapter_sha(args, "a" * 64)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, stdout="[]", stderr="")
        if command[:3] == ["docker", "run", "--rm"]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"adapter_sha256": "a" * 64}) + "\n", stderr="")
        if command == ["nvidia-smi"]:
            return subprocess.CompletedProcess(command, 0, stdout="NVIDIA-SMI", stderr="")
        raise AssertionError(f"unexpected command in preflight-only: {command}")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "READY_TO_RUN"
    image_lineage = next(row for row in summary["preflight"] if row["id"] == "docker_image_adapter_matches_adapter_manifest")
    assert image_lineage["ok"] is True
    assert image_lineage["expected_adapter_sha256"] == "a" * 64
    assert image_lineage["image_adapter_sha256"] == "a" * 64
    assert any(command[:3] == ["docker", "run", "--rm"] for command in commands)


def test_gate_runner_preflight_rejects_docker_image_adapter_lineage_mismatch(tmp_path: Path) -> None:
    args = args_for(tmp_path, preflight_only=True)
    write_manifest_with_adapter_sha(args, "a" * 64)

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if command[:3] == ["docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, stdout="[]", stderr="")
        if command[:3] == ["docker", "run", "--rm"]:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"adapter_sha256": "b" * 64}) + "\n", stderr="")
        if command == ["nvidia-smi"]:
            return subprocess.CompletedProcess(command, 0, stdout="NVIDIA-SMI", stderr="")
        raise AssertionError(f"unexpected command in preflight-only: {command}")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_READY_PRECHECK_FAILED"
    image_lineage = next(row for row in summary["preflight"] if row["id"] == "docker_image_adapter_matches_adapter_manifest")
    assert image_lineage["ok"] is False
    assert image_lineage["expected_adapter_sha256"] == "a" * 64
    assert image_lineage["image_adapter_sha256"] == "b" * 64
    assert any("Docker image adapter hash does not match" in error for error in summary["errors"])


def test_gate_runner_plan_only_does_not_execute_runner(tmp_path: Path) -> None:
    args = args_for(tmp_path, plan_only=True)

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise AssertionError("plan-only must not execute commands")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "PLAN_ONLY_NOT_RUN"
    assert summary["decision"] == "NOT_RUN"
    assert summary["steps"] == []
    assert [row["id"] for row in summary["planned_steps"]] == ["adapter_intake", "endpoint_capture", "m6_go_verification"]
    assert summary["m6_rc_claimed_go"] is False


def test_gate_runner_refuses_fake_backend_env(tmp_path: Path, monkeypatch) -> None:
    args = args_for(tmp_path)
    monkeypatch.setenv("MIB_RUNTIME_ALLOW_FAKE_BACKEND", "1")

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise AssertionError("precheck failure must not execute commands")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_GO_PRECHECK_FAILED"
    assert any("MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset" in error for error in summary["errors"])
    assert summary["m6_rc_claimed_go"] is False
