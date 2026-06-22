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


def args_for(tmp_path: Path, *, token: str = "x" * 32, plan_only: bool = False) -> SimpleNamespace:
    adapter_dir = tmp_path / "run" / "adapter"
    adapter_dir.mkdir(parents=True)
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
    )


def write_json(path: str, payload: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def test_gate_runner_chains_intake_capture_and_m6_go(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "verify_real_adapter_artifact.py" in command[1]:
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
        elif "capture_real_adapter_endpoint_evidence.py" in command[1]:
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
        elif "verify_m6_rc_evidence.py" in command[1]:
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
    assert [Path(command[1]).name for command in commands] == [
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
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="adapter rejected")

    summary = gate.run_gate(args, runner=runner)

    assert summary["status"] == "NOT_GO_STEP_FAILED"
    assert summary["decision"] == "NOT_GO"
    assert [Path(command[1]).name for command in commands] == ["verify_real_adapter_artifact.py"]
    assert summary["m6_rc_claimed_go"] is False


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
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset" in summary["errors"]
    assert summary["m6_rc_claimed_go"] is False
