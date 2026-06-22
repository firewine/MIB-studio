#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "mib_v0_release_blocker_recertification.v1"
GO_STATUS = "GO_V0_RELEASE_BLOCKER_RECERTIFICATION"
NOT_GO_STATUS = "NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION"
FAILED_STATUS = "RECERTIFICATION_COMMAND_FAILED"
DEFAULT_SCAN_ROOTS = [
    "/home/firewine/MIB-studio",
    "/tmp/mib-real-adapter",
    "/tmp/mib-phi-docker-export-_vgqfd4g",
]
VERIFIED_LAUNCHER_SHELL = "artifacts/review/verified_external_cuda_training_launcher.sh"
TRAINING_HANDOFF_SHELL = "artifacts/review/real_adapter_cuda_training_handoff.sh"
TRAINING_HANDOFF_REASONS = {
    "no_go_adapter_candidates",
    "docker_base_image_env_digest",
    "backend_config_ready",
    "strict_model_cache_files",
    "cuda_visible",
    "docker_base_image_available",
    "adapter_dir_present",
    "adapter_safetensors_present",
    "adapter_config_present",
    "adapter_manifest_present",
    "model_cache_dir_present",
    "docker_image_available",
    "host_cuda_visible",
}

Runner = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def read_json(root: Path, path: str | Path) -> dict[str, Any] | None:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if not candidate.is_file():
        return None
    data = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {candidate}")
    return data


def clip(value: str, *, limit: int = 2000) -> str:
    return value if len(value) <= limit else value[-limit:]


def run_subprocess(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout)


def expected_bundle_decision(value: str) -> str:
    return "GO_REAL_ADAPTER_EVIDENCE_BUNDLE" if value == "GO" else "NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE"


def adapter_paths(adapter_root: str) -> tuple[str, str]:
    root = Path(adapter_root)
    return str(root / "adapter"), str(root / "manifest.json")


def scan_roots(args: argparse.Namespace) -> list[str]:
    return list(args.scan_root or DEFAULT_SCAN_ROOTS)


def candidate_scan_command(args: argparse.Namespace) -> list[str]:
    command = [args.python, "scripts/find_real_adapter_candidates.py"]
    for root in scan_roots(args):
        command.extend(["--root", root])
    command.extend(
        [
            "--base-model",
            args.base_model,
            "--image",
            args.image,
            "--agent-id",
            args.agent_id,
            "--model-cache-dir",
            args.model_cache_dir,
            "--json-output",
            args.candidate_scan_output,
        ]
    )
    if args.expected_go_candidates is not None:
        command.extend(["--expected-go-candidates", str(args.expected_go_candidates)])
    return command


def training_preflight_command(args: argparse.Namespace) -> list[str]:
    command = [
        args.python,
        "scripts/check_cuda_lora_training_prereqs.py",
        "--dataset-jsonl",
        args.dataset_jsonl,
        "--base-model",
        args.base_model,
        "--model-cache-dir",
        args.model_cache_dir,
        "--output-root",
        args.adapter_root,
        "--backend-config",
        args.backend_config,
        "--image",
        args.image,
        "--llamafactory-cli",
        args.llamafactory_cli,
        "--verify-model-cache-hashes",
        "--json-output",
        args.training_preflight_output,
    ]
    if args.expected_training_status:
        command.extend(["--expected-status", args.expected_training_status])
    return command


def rc_preflight_command(args: argparse.Namespace) -> list[str]:
    adapter_dir, adapter_manifest = adapter_paths(args.adapter_root)
    return [
        args.python,
        "scripts/run_m6_real_adapter_rc_gate.py",
        "--preflight-only",
        "--adapter-dir",
        adapter_dir,
        "--adapter-manifest",
        adapter_manifest,
        "--base-model",
        args.base_model,
        "--image",
        args.image,
        "--agent-id",
        args.agent_id,
        "--model-cache-dir",
        args.model_cache_dir,
        "--adapter-intake-json-output",
        args.adapter_intake_output,
        "--endpoint-output",
        args.endpoint_output,
        "--endpoint-json-output",
        args.endpoint_json_output,
        "--m6-json-output",
        args.m6_verification_output,
        "--json-output",
        args.rc_prereq_output,
        "--token",
        args.preflight_token,
    ]


def bundle_verify_command(args: argparse.Namespace) -> list[str]:
    return [
        args.python,
        "scripts/verify_real_adapter_evidence_bundle.py",
        "--bundle-dir",
        args.bundle_source_dir,
        "--expected-decision",
        args.expected_bundle_decision,
        "--json-output",
        args.bundle_verification_output,
    ]


def readiness_command(args: argparse.Namespace) -> list[str]:
    return [
        args.python,
        "scripts/verify_v0_release_readiness.py",
        "--expected-decision",
        args.expected_readiness_decision,
        "--json-output",
        args.readiness_output,
    ]


def handoff_command(args: argparse.Namespace) -> list[str]:
    return [
        args.python,
        "scripts/build_real_adapter_handoff.py",
        "--candidate-scan",
        args.candidate_scan_output,
        "--prereq-audit",
        args.rc_prereq_output,
        "--readiness-audit",
        args.readiness_output,
        "--adapter-root",
        args.adapter_root,
        "--base-model",
        args.base_model,
        "--image",
        args.image,
        "--agent-id",
        args.agent_id,
        "--model-cache-dir",
        args.model_cache_dir,
        "--json-output",
        args.handoff_json_output,
        "--markdown-output",
        args.handoff_markdown_output,
        "--shell-output",
        args.handoff_shell_output,
    ]


def command_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        {"id": "candidate_scan", "command": candidate_scan_command(args), "timeout_seconds": 180, "output": args.candidate_scan_output},
        {"id": "cuda_training_preflight", "command": training_preflight_command(args), "timeout_seconds": 180, "output": args.training_preflight_output},
        {"id": "m6_rc_preflight", "command": rc_preflight_command(args), "timeout_seconds": 180, "output": args.rc_prereq_output},
        {"id": "real_adapter_bundle_verification", "command": bundle_verify_command(args), "timeout_seconds": 180, "output": args.bundle_verification_output},
        {"id": "v0_readiness", "command": readiness_command(args), "timeout_seconds": 180, "output": args.readiness_output},
        {"id": "cuda_handoff", "command": handoff_command(args), "timeout_seconds": 180, "output": args.handoff_json_output},
    ]


def command_result(row: dict[str, Any], result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "command": row["command"],
        "output": row["output"],
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout_tail": clip(result.stdout or ""),
        "stderr_tail": clip(result.stderr or ""),
    }


def current_state(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    candidate = read_json(root, args.candidate_scan_output) or {}
    training = read_json(root, args.training_preflight_output) or {}
    rc = read_json(root, args.rc_prereq_output) or {}
    bundle = read_json(root, args.bundle_verification_output) or {}
    readiness = read_json(root, args.readiness_output) or {}
    handoff = read_json(root, args.handoff_json_output) or {}
    return {
        "candidate_scan_decision": candidate.get("decision"),
        "go_candidate_count": candidate.get("go_candidate_count"),
        "fixture_like_candidate_count": candidate.get("fixture_like_candidate_count"),
        "cuda_training_status": training.get("status"),
        "cuda_training_blockers": training.get("blockers", []),
        "m6_rc_prereq_status": rc.get("status"),
        "m6_rc_prereq_decision": rc.get("decision"),
        "m6_rc_prereq_errors": rc.get("errors", []),
        "bundle_decision": bundle.get("decision"),
        "bundle_blockers": bundle.get("blockers", []),
        "v0_readiness_decision": readiness.get("decision"),
        "v0_release_ready": readiness.get("release_ready"),
        "v0_blockers": readiness.get("blockers", []),
        "v0_unexpected_blockers": readiness.get("unexpected_blockers", []),
        "handoff_decision": handoff.get("decision"),
    }


def expectation_checks(args: argparse.Namespace, state: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        {
            "id": "cuda_training_status_matches_expected",
            "expected": args.expected_training_status,
            "actual": state["cuda_training_status"],
            "ok": state["cuda_training_status"] == args.expected_training_status,
        },
        {
            "id": "m6_rc_status_matches_expected",
            "expected": args.expected_rc_status,
            "actual": state["m6_rc_prereq_status"],
            "ok": state["m6_rc_prereq_status"] == args.expected_rc_status,
        },
        {
            "id": "bundle_decision_matches_expected",
            "expected": expected_bundle_decision(args.expected_bundle_decision),
            "actual": state["bundle_decision"],
            "ok": state["bundle_decision"] == expected_bundle_decision(args.expected_bundle_decision),
        },
        {
            "id": "readiness_decision_matches_expected",
            "expected": args.expected_readiness_decision,
            "actual": state["v0_readiness_decision"],
            "ok": state["v0_readiness_decision"] == args.expected_readiness_decision,
        },
    ]
    if args.expected_go_candidates is not None:
        checks.append(
            {
                "id": "go_candidate_count_matches_expected",
                "expected": args.expected_go_candidates,
                "actual": state["go_candidate_count"],
                "ok": state["go_candidate_count"] == args.expected_go_candidates,
            }
        )
    return checks


def append_unique(values: list[str], value: object) -> None:
    if isinstance(value, str) and value and value not in values:
        values.append(value)


def append_many_unique(values: list[str], candidates: object) -> None:
    if isinstance(candidates, list):
        for candidate in candidates:
            append_unique(values, candidate)


def prereq_id(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.split(":", 1)[0].strip()


def blocking_reasons(failed_step: str | None, state: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if failed_step:
        append_unique(reasons, f"child_command_failed:{failed_step}")
    if state.get("go_candidate_count") == 0:
        append_unique(reasons, "no_go_adapter_candidates")
    append_many_unique(reasons, state.get("cuda_training_blockers"))
    if isinstance(state.get("m6_rc_prereq_errors"), list):
        for error in state["m6_rc_prereq_errors"]:
            append_unique(reasons, prereq_id(error))
    append_many_unique(reasons, state.get("bundle_blockers"))
    append_many_unique(reasons, state.get("v0_blockers"))
    append_many_unique(reasons, state.get("v0_unexpected_blockers"))
    if state.get("handoff_decision") and state.get("handoff_decision") != "READY_FOR_REAL_ADAPTER_RC":
        append_unique(reasons, str(state["handoff_decision"]))
    return reasons


def operator_next_actions(reasons: list[str]) -> list[str]:
    actions: list[str] = []

    def add(action: str) -> None:
        append_unique(actions, action)

    if any(reason.startswith("child_command_failed:") for reason in reasons):
        add("Inspect the failed child command stderr/stdout tail in commands, fix the tool/runtime failure, and rerun recertification.")
    if TRAINING_HANDOFF_REASONS & set(reasons):
        add(
            f"Run {VERIFIED_LAUNCHER_SHELL} on the external CUDA host first; it verifies the operator packet before invoking {TRAINING_HANDOFF_SHELL}."
        )
    if "no_go_adapter_candidates" in reasons:
        add("Produce or transfer a real trained adapter under /tmp/mib-real-adapter before rerunning local release checks.")
    if {
        "adapter_dir_present",
        "adapter_safetensors_present",
        "adapter_config_present",
        "adapter_manifest_present",
    } & set(reasons):
        add("Provide /tmp/mib-real-adapter/adapter with adapter.safetensors and adapter_config.json plus /tmp/mib-real-adapter/manifest.json.")
    if {"model_cache_dir_present", "strict_model_cache_files"} & set(reasons):
        add("Prepare the strict model cache at /tmp/mib-strict-model-cache-phi/model_cache with required base-model files and hashes.")
    if "docker_base_image_env_digest" in reasons:
        add("Set MIB_DOCKER_BASE_IMAGE_WITH_DIGEST to a digest-pinned CUDA/Python base image on the CUDA host.")
    if {"docker_base_image_available", "docker_image_available"} & set(reasons):
        add("Build or pull the required Docker images, including the digest-pinned base image and mib-export:test.")
    if {"cuda_visible", "host_cuda_visible"} & set(reasons):
        add("Rerun on a CUDA host where nvidia-smi is visible to the process.")
    if {
        "endpoint_live_no_fake_json",
        "real_trained_adapter_no_fake_endpoint",
        "adapter_intake_go",
        "adapter_hash_crosscheck",
        "rc_gate_go",
        "m6_verification_go",
    } & set(reasons):
        add("Run the real-adapter M6 RC gate against a live no-fake Docker endpoint and collect accepted JSON/markdown evidence.")
    if {"endpoint_markdown_present", "WAITING_FOR_REAL_ADAPTER_INPUTS"} & set(reasons):
        add("Follow artifacts/review/real_adapter_cuda_handoff.sh on the external CUDA host, then transfer the metadata-bearing evidence bundle back.")
    return actions


def recertify(args: argparse.Namespace, *, runner: Runner = run_subprocess) -> dict[str, Any]:
    root = Path(args.root).resolve()
    results: list[dict[str, Any]] = []
    failed_step: str | None = None
    for row in command_plan(args):
        result = runner(row["command"], root, row["timeout_seconds"])
        results.append(command_result(row, result))
        if result.returncode != 0:
            failed_step = str(row["id"])
            break

    state = current_state(args, root)
    checks = expectation_checks(args, state)
    commands_ok = failed_step is None and all(row["ok"] for row in results)
    expectations_ok = all(row["ok"] for row in checks)
    v0_go = state["v0_readiness_decision"] == "GO" and state["v0_release_ready"] is True
    if not commands_ok:
        status = FAILED_STATUS
    elif v0_go and expectations_ok:
        status = GO_STATUS
    else:
        status = NOT_GO_STATUS
    reasons = blocking_reasons(failed_step, state) if status != GO_STATUS else []
    actions = operator_next_actions(reasons) if status != GO_STATUS else []

    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-v0-release-blocker-recertification",
        "root": str(root),
        "status": status,
        "recertification_ok": commands_ok and expectations_ok,
        "release_claimed_go": status == GO_STATUS,
        "m6_rc_claimed_go": False,
        "failed_step": failed_step,
        "expected_readiness_decision": args.expected_readiness_decision,
        "expected_bundle_decision": expected_bundle_decision(args.expected_bundle_decision),
        "expected_training_status": args.expected_training_status,
        "expected_rc_status": args.expected_rc_status,
        "commands": results,
        "expectation_checks": checks,
        "current_state": state,
        "blocking_reasons": reasons,
        "operator_next_actions": actions,
        "primary_external_handoff": VERIFIED_LAUNCHER_SHELL if TRAINING_HANDOFF_REASONS & set(reasons) else None,
        "outputs": {
            "candidate_scan": args.candidate_scan_output,
            "training_preflight": args.training_preflight_output,
            "m6_rc_prereq": args.rc_prereq_output,
            "bundle_verification": args.bundle_verification_output,
            "readiness": args.readiness_output,
            "handoff_json": args.handoff_json_output,
            "handoff_markdown": args.handoff_markdown_output,
            "handoff_shell": args.handoff_shell_output,
        },
        "operator_next_step": (
            f"Run {VERIFIED_LAUNCHER_SHELL} to verify the operator packet and produce a real trained adapter, then run the downstream no-fake endpoint handoff."
            if status != GO_STATUS
            else "Run final release closeout review and do not claim GO until M6 review docs and v0 readiness are confirmed."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh current v0 release blocker evidence using existing strict checks.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--python", default="./.venv/bin/python")
    parser.add_argument("--base-model", choices=["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"], default="microsoft/Phi-3.5-mini-instruct")
    parser.add_argument("--image", default="mib-export:test")
    parser.add_argument("--agent-id", default="finance.router.v1")
    parser.add_argument("--model-cache-dir", default="/tmp/mib-strict-model-cache-phi/model_cache")
    parser.add_argument("--adapter-root", default="/tmp/mib-real-adapter")
    parser.add_argument("--dataset-jsonl", default="examples/fixtures/router_20.jsonl")
    parser.add_argument("--backend-config", default="/tmp/mib-real-adapter/backend_config.yaml")
    parser.add_argument("--llamafactory-cli", default="./.venv/bin/llamafactory-cli")
    parser.add_argument("--scan-root", action="append")
    parser.add_argument("--expected-go-candidates", type=int)
    parser.add_argument("--expected-readiness-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--expected-bundle-decision", choices=["GO", "NOT_GO"], default="NOT_GO")
    parser.add_argument("--expected-training-status", choices=["READY_FOR_CUDA_LORA_TRAINING", "NOT_READY_CUDA_LORA_TRAINING"], default="NOT_READY_CUDA_LORA_TRAINING")
    parser.add_argument("--expected-rc-status", choices=["READY_TO_RUN", "NOT_READY_PRECHECK_FAILED"], default="NOT_READY_PRECHECK_FAILED")
    parser.add_argument("--preflight-token", default="recertification-preflight-token-000000000000")
    parser.add_argument("--candidate-scan-output", default="artifacts/review/real_adapter_candidate_scan.json")
    parser.add_argument("--training-preflight-output", default="artifacts/review/real_adapter_cuda_training_prereq_preflight.json")
    parser.add_argument("--rc-prereq-output", default="artifacts/review/m6_real_adapter_prereq_audit.json")
    parser.add_argument("--adapter-intake-output", default="artifacts/review/real_adapter_artifact_intake.json")
    parser.add_argument("--endpoint-output", default="artifacts/review/real_trained_adapter_endpoint_evidence.md")
    parser.add_argument("--endpoint-json-output", default="artifacts/review/real_trained_adapter_endpoint_evidence.json")
    parser.add_argument("--m6-verification-output", default="artifacts/review/m6_rc_evidence_verification.json")
    parser.add_argument("--bundle-source-dir", default="artifacts/review")
    parser.add_argument("--bundle-verification-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    parser.add_argument("--readiness-output", default="artifacts/review/v0_release_readiness_audit.json")
    parser.add_argument("--handoff-json-output", default="artifacts/review/real_adapter_cuda_handoff.json")
    parser.add_argument("--handoff-markdown-output", default="artifacts/review/real_adapter_cuda_handoff.md")
    parser.add_argument("--handoff-shell-output", default="artifacts/review/real_adapter_cuda_handoff.sh")
    parser.add_argument("--json-output", default="artifacts/review/v0_release_blocker_recertification.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = recertify(args)
    output = Path(args.json_output)
    if not output.is_absolute():
        output = Path(args.root).resolve() / output
    write_json(output, summary)
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "status": summary["status"],
                "recertification_ok": summary["recertification_ok"],
                "release_claimed_go": summary["release_claimed_go"],
            },
            sort_keys=True,
        )
    )
    return 0 if summary["recertification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
