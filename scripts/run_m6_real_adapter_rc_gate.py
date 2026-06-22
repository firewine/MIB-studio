#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_INTAKE_OUTPUT = "artifacts/review/real_adapter_artifact_intake.json"
DEFAULT_ENDPOINT_OUTPUT = "artifacts/review/real_trained_adapter_endpoint_evidence.md"
DEFAULT_ENDPOINT_JSON_OUTPUT = "artifacts/review/real_trained_adapter_endpoint_evidence.json"
DEFAULT_M6_OUTPUT = "artifacts/review/m6_rc_evidence_verification.json"
DEFAULT_GATE_OUTPUT = "artifacts/review/m6_real_adapter_rc_gate_run.json"


@dataclass(frozen=True)
class Step:
    id: str
    command: list[str]
    timeout: int


Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def run_subprocess(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def clip(value: str, *, limit: int = 4000) -> str:
    return value if len(value) <= limit else value[-limit:]


def redacted_text(value: str, secrets: Sequence[str]) -> str:
    result = value
    for secret in secrets:
        if secret:
            result = result.replace(secret, "<redacted-token>")
    return result


def redacted_command(command: Sequence[str], secrets: Sequence[str]) -> list[str]:
    return [redacted_text(part, secrets) for part in command]


def read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def bearer_token(args: argparse.Namespace) -> str:
    return args.token or os.environ.get("MIB_RUNTIME_BEARER_TOKEN", "")


def preflight_errors(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    token = bearer_token(args)
    if os.environ.get("MIB_RUNTIME_ALLOW_FAKE_BACKEND"):
        errors.append("MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset")
    if len(token) < 32:
        errors.append("MIB_RUNTIME_BEARER_TOKEN or --token must be at least 32 characters")
    if args.plan_only:
        return errors
    if not Path(args.adapter_dir).is_dir():
        errors.append(f"adapter directory does not exist: {args.adapter_dir}")
    if not Path(args.adapter_manifest).is_file():
        errors.append(f"adapter manifest does not exist: {args.adapter_manifest}")
    if not Path(args.model_cache_dir).is_dir():
        errors.append(f"model cache dir does not exist: {args.model_cache_dir}")
    return errors


def build_steps(args: argparse.Namespace, *, python_exe: str | None = None) -> list[Step]:
    python = python_exe or sys.executable
    scripts_dir = Path(__file__).resolve().parent
    intake = [
        python,
        str(scripts_dir / "verify_real_adapter_artifact.py"),
        "--adapter-dir",
        args.adapter_dir,
        "--base-model",
        args.base_model,
        "--manifest",
        args.adapter_manifest,
        "--json-output",
        args.adapter_intake_json_output,
    ]
    endpoint = [
        python,
        str(scripts_dir / "capture_real_adapter_endpoint_evidence.py"),
        "--image",
        args.image,
        "--agent-id",
        args.agent_id,
        "--model-cache-dir",
        args.model_cache_dir,
        "--adapter-intake-report",
        args.adapter_intake_json_output,
        "--host-port",
        str(args.host_port),
        "--container-name",
        args.container_name,
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--input-text",
        args.input_text,
        "--output",
        args.endpoint_output,
        "--json-output",
        args.endpoint_json_output,
    ]
    token = bearer_token(args)
    if args.token:
        endpoint.extend(["--token", token])
    if args.keep_container:
        endpoint.append("--keep-container")
    m6 = [
        python,
        str(scripts_dir / "verify_m6_rc_evidence.py"),
        "--expected-decision",
        "GO",
        "--real-endpoint-evidence",
        args.endpoint_output,
        "--json-output",
        args.m6_json_output,
    ]
    return [
        Step("adapter_intake", intake, args.step_timeout_seconds),
        Step("endpoint_capture", endpoint, args.endpoint_timeout_seconds),
        Step("m6_go_verification", m6, args.step_timeout_seconds),
    ]


def base_summary(args: argparse.Namespace) -> dict[str, Any]:
    token = bearer_token(args)
    secrets = [token] if token else []
    planned_steps = build_steps(args)
    return {
        "schema_version": "mib_real_adapter_rc_gate_runner.v1",
        "date": now_utc(),
        "gate": "mib-studio-real-adapter-rc-gate-runner",
        "status": "RUNNING",
        "plan_only": bool(args.plan_only),
        "decision": "PENDING",
        "m6_rc_claimed_go": False,
        "inputs": {
            "adapter_dir": args.adapter_dir,
            "adapter_manifest": args.adapter_manifest,
            "base_model": args.base_model,
            "image": args.image,
            "agent_id": args.agent_id,
            "model_cache_dir": args.model_cache_dir,
            "adapter_intake_json_output": args.adapter_intake_json_output,
            "endpoint_output": args.endpoint_output,
            "endpoint_json_output": args.endpoint_json_output,
            "m6_json_output": args.m6_json_output,
        },
        "planned_steps": [
            {"id": step.id, "command": redacted_command(step.command, secrets), "timeout_seconds": step.timeout}
            for step in planned_steps
        ],
        "steps": [],
        "errors": [],
    }


def failed(summary: dict[str, Any], *, status: str, decision: str, error: str) -> dict[str, Any]:
    summary["status"] = status
    summary["decision"] = decision
    summary["m6_rc_claimed_go"] = False
    summary["errors"].append(error)
    return summary


def step_result_row(step: Step, result: subprocess.CompletedProcess[str], secrets: Sequence[str]) -> dict[str, Any]:
    return {
        "id": step.id,
        "command": redacted_command(step.command, secrets),
        "returncode": result.returncode,
        "stdout_tail": clip(redacted_text(result.stdout or "", secrets)),
        "stderr_tail": clip(redacted_text(result.stderr or "", secrets)),
    }


def run_gate(args: argparse.Namespace, *, runner: Runner = run_subprocess) -> dict[str, Any]:
    token = bearer_token(args)
    secrets = [token] if token else []
    summary = base_summary(args)
    errors = preflight_errors(args)
    if errors:
        summary["errors"].extend(errors)
        summary["status"] = "NOT_GO_PRECHECK_FAILED"
        summary["decision"] = "NOT_GO"
        return summary
    if args.plan_only:
        summary["status"] = "PLAN_ONLY_NOT_RUN"
        summary["decision"] = "NOT_RUN"
        summary["m6_rc_claimed_go"] = False
        return summary

    for step in build_steps(args):
        result = runner(step.command, step.timeout)
        summary["steps"].append(step_result_row(step, result, secrets))
        if result.returncode != 0:
            return failed(summary, status="NOT_GO_STEP_FAILED", decision="NOT_GO", error=f"{step.id} failed")
        if step.id == "adapter_intake":
            intake = read_json(args.adapter_intake_json_output)
            if intake.get("status") != "GO_REAL_ADAPTER_ARTIFACT_INTAKE":
                return failed(summary, status="NOT_GO_ADAPTER_INTAKE", decision="NOT_GO", error="adapter intake report is not GO")
        if step.id == "endpoint_capture":
            endpoint = read_json(args.endpoint_json_output)
            if endpoint.get("source") != "live_docker_capture" or endpoint.get("self_test") is not False:
                return failed(summary, status="NOT_GO_ENDPOINT_EVIDENCE", decision="NOT_GO", error="endpoint evidence is not live capture")
        if step.id == "m6_go_verification":
            m6_report = read_json(args.m6_json_output)
            if m6_report.get("verification_ok") is not True or m6_report.get("decision") != "GO":
                return failed(summary, status="NOT_GO_M6_VERIFICATION", decision="NOT_GO", error="M6 verifier did not return GO")

    summary["status"] = "GO_M6_REAL_ADAPTER_RC_GATE"
    summary["decision"] = "GO"
    summary["m6_rc_claimed_go"] = True
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the real adapter M6-RC evidence gate.")
    parser.add_argument("--plan-only", action="store_true", help="Render the command plan without executing the gate.")
    parser.add_argument("--adapter-dir", required=True)
    parser.add_argument("--adapter-manifest", required=True)
    parser.add_argument("--base-model", choices=["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"], required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--host-port", type=int, default=18084)
    parser.add_argument("--container-name", default="mib-real-adapter-rc-gate")
    parser.add_argument("--token")
    parser.add_argument("--input-text", default="finance_income income calculation")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--step-timeout-seconds", type=int, default=180)
    parser.add_argument("--endpoint-timeout-seconds", type=int, default=300)
    parser.add_argument("--keep-container", action="store_true")
    parser.add_argument("--adapter-intake-json-output", default=DEFAULT_INTAKE_OUTPUT)
    parser.add_argument("--endpoint-output", default=DEFAULT_ENDPOINT_OUTPUT)
    parser.add_argument("--endpoint-json-output", default=DEFAULT_ENDPOINT_JSON_OUTPUT)
    parser.add_argument("--m6-json-output", default=DEFAULT_M6_OUTPUT)
    parser.add_argument("--json-output", default=DEFAULT_GATE_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_gate(args)
    write_json(args.json_output, summary)
    print(json.dumps({"json_output": args.json_output, "status": summary["status"], "decision": summary["decision"]}, sort_keys=True))
    return 0 if summary["status"] in {"GO_M6_REAL_ADAPTER_RC_GATE", "PLAN_ONLY_NOT_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
