#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_real_adapter_cuda_handoff.v1"
LOCKED_BASE_MODELS = {"google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def write_text(path: str | Path, value: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def command_row(command_id: str, argv: list[str], *, env: dict[str, str] | None = None, note: str = "") -> dict[str, Any]:
    prefix = ""
    if env:
        prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items()) + " "
    return {
        "id": command_id,
        "argv": argv,
        "env": env or {},
        "shell": prefix + shlex.join(argv),
        "note": note,
    }


def script_command(row: dict[str, Any]) -> str:
    argv = row.get("argv", [])
    if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
        raise ValueError(f"invalid argv for command row {row.get('id')}")

    env = row.get("env", {})
    if not isinstance(env, dict):
        raise ValueError(f"invalid env for command row {row.get('id')}")

    prefixes: list[str] = []
    for key, value in env.items():
        if key == "MIB_RUNTIME_BEARER_TOKEN":
            prefixes.append('MIB_RUNTIME_BEARER_TOKEN="${MIB_RUNTIME_BEARER_TOKEN}"')
        else:
            prefixes.append(f"{key}={shlex.quote(str(value))}")
    return (" ".join(prefixes) + " " if prefixes else "") + shlex.join(argv)


def failed_preflight_ids(prereq: dict[str, Any]) -> list[str]:
    rows = prereq.get("preflight", [])
    if isinstance(rows, list):
        return [str(row.get("id")) for row in rows if isinstance(row, dict) and row.get("ok") is False]
    explicit = prereq.get("missing_prereq_ids", [])
    return [str(item) for item in explicit] if isinstance(explicit, list) else []


def preflight_status(prereq: dict[str, Any], check_id: str) -> str:
    for row in prereq.get("preflight", []):
        if isinstance(row, dict) and row.get("id") == check_id:
            if row.get("skipped") is True:
                return "pending"
            return "available" if row.get("ok") is True else "missing"
    return "missing" if check_id in failed_preflight_ids(prereq) else "unknown"


def required_inputs(prereq: dict[str, Any]) -> list[dict[str, str]]:
    required = [
        ("adapter_dir_present", "Real adapter directory exists, normally /tmp/mib-real-adapter/adapter"),
        ("adapter_safetensors_present", "adapter.safetensors is present and is not fixture-sized"),
        ("adapter_config_present", "adapter_config.json declares PEFT LORA and the locked base model"),
        ("adapter_manifest_present", "manifest.json records adapter_sha256, files, and trainer_backend"),
        ("docker_image_available", "Docker image tag exists for the export that packages the same adapter"),
        ("docker_image_adapter_matches_adapter_manifest", "Docker /app/adapter hash matches manifest adapter_sha256"),
        ("host_cuda_visible", "nvidia-smi succeeds on the host"),
        ("model_cache_dir_present", "Strict base-model cache directory is present and mounted read-only"),
        ("bearer_token_ready", "MIB_RUNTIME_BEARER_TOKEN is at least 32 characters"),
        ("fake_backend_env_absent", "MIB_RUNTIME_ALLOW_FAKE_BACKEND is unset"),
    ]
    return [{"id": item_id, "status": preflight_status(prereq, item_id), "requirement": text} for item_id, text in required]


def scan_roots(candidate_scan: dict[str, Any], adapter_root: str) -> list[str]:
    roots = [str(item) for item in candidate_scan.get("roots", []) if isinstance(item, str)]
    return unique(roots + [adapter_root])


def default_paths(adapter_root: str) -> tuple[str, str]:
    root = Path(adapter_root)
    return str(root / "adapter"), str(root / "manifest.json")


def base_commands(args: argparse.Namespace, candidate_scan: dict[str, Any]) -> list[dict[str, Any]]:
    adapter_dir, adapter_manifest = default_paths(args.adapter_root)
    roots = scan_roots(candidate_scan, args.adapter_root)
    scan_argv = [args.python, "scripts/find_real_adapter_candidates.py"]
    for root in roots:
        scan_argv.extend(["--root", root])
    scan_argv.extend(
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
            args.candidate_scan,
        ]
    )
    intake_argv = [
        args.python,
        "scripts/verify_real_adapter_artifact.py",
        "--adapter-dir",
        adapter_dir,
        "--base-model",
        args.base_model,
        "--manifest",
        adapter_manifest,
        "--json-output",
        args.adapter_intake_json_output,
    ]
    gate_common = [
        args.python,
        "scripts/run_m6_real_adapter_rc_gate.py",
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
        args.adapter_intake_json_output,
        "--endpoint-output",
        args.endpoint_output,
        "--endpoint-json-output",
        args.endpoint_json_output,
        "--m6-json-output",
        args.m6_json_output,
        "--json-output",
        args.gate_json_output,
    ]
    token_env = {"MIB_RUNTIME_BEARER_TOKEN": "<set-32-plus-character-token>"}
    m6_doc_go_check = (
        "from pathlib import Path; import sys; "
        "signoff=Path('docs/reviews/M6/SIGNOFF_MATRIX.md').read_text(encoding='utf-8'); "
        "cto=Path('docs/reviews/M6/CTO_DECISION.md').read_text(encoding='utf-8'); "
        "ok='| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |' in signoff and 'Decision: GO' in cto; "
        "sys.exit(0 if ok else 3)"
    )
    bundle_argv = [
        args.python,
        "scripts/build_real_adapter_evidence_bundle.py",
        "--source-dir",
        "artifacts/review",
        "--bundle-dir",
        args.bundle_dir,
        "--expected-decision",
        "GO",
        "--verification-output",
        args.bundle_json_output,
        "--manifest-output",
        args.bundle_manifest_output,
        "--archive-output",
        args.bundle_archive_output,
    ]
    return [
        command_row("candidate_scan", scan_argv, note="Find and validate adapter candidates under explicit roots."),
        command_row("adapter_intake", intake_argv, note="Run strict intake on the operator-provided adapter before export/endpoint evidence."),
        command_row("rc_gate_preflight", gate_common + ["--preflight-only"], env=token_env, note="Must return READY_TO_RUN before live endpoint capture."),
        command_row(
            "rc_gate_endpoint_evidence",
            gate_common + ["--endpoint-evidence-only"],
            env=token_env,
            note="Runs intake and no-fake Docker endpoint capture only; does not run M6 GO verification or claim M6-RC GO.",
        ),
        command_row(
            "m6_review_docs_go_update_required",
            [args.python, "-c", m6_doc_go_check],
            note="Stops until docs/reviews/M6 signoff and CTO decision are updated to GO after reviewing live endpoint evidence.",
        ),
        command_row(
            "rc_gate_m6_go",
            gate_common + ["--m6-verification-only"],
            env=token_env,
            note="Runs only M6 GO verification against the existing live endpoint evidence after M6 review docs are GO.",
        ),
        command_row(
            "evidence_bundle_assembly",
            bundle_argv,
            note="Copy fixed real-adapter evidence files into a portable bundle and require GO_REAL_ADAPTER_EVIDENCE_BUNDLE before v0 readiness can pass.",
        ),
        command_row(
            "v0_readiness_recheck",
            [
                args.python,
                "scripts/verify_v0_release_readiness.py",
                "--expected-decision",
                "GO",
                "--json-output",
                args.readiness_audit,
            ],
            note="Run only after the live RC gate produces GO M6 evidence.",
        ),
    ]


def post_transfer_closeout_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        command_row(
            "local_closeout_after_bundle_transfer",
            [
                args.python,
                "scripts/run_v0_release_closeout_from_bundle.py",
                "--bundle-archive",
                args.bundle_archive_output,
                "--expected-bundle-decision",
                "GO",
                "--expected-readiness-decision",
                "GO",
            ],
            note=(
                "Run in this repository after copying the real adapter evidence bundle archive "
                "back from the CUDA host. The archive must be metadata-bearing and produced by "
                "build_real_adapter_evidence_bundle.py; missing or mismatched archive metadata "
                "returns archive_metadata_not_verified and prevents promotion. Expected success "
                "status: GO_V0_RELEASE_CLOSEOUT."
            ),
        )
    ]


def go_candidate_commands(candidate_scan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, candidate in enumerate(candidate_scan.get("candidates", []), 1):
        if not isinstance(candidate, dict) or candidate.get("go") is not True:
            continue
        command = candidate.get("rc_gate_command")
        if isinstance(command, list) and all(isinstance(part, str) for part in command):
            rows.append(
                command_row(
                    f"go_candidate_{index}_rc_gate",
                    command,
                    env={"MIB_RUNTIME_BEARER_TOKEN": "<set-32-plus-character-token>"},
                    note=f"Candidate from {candidate.get('adapter_dir')}",
                )
            )
    return rows


def decision(candidate_scan: dict[str, Any], prereq: dict[str, Any], readiness: dict[str, Any]) -> str:
    if readiness.get("decision") == "GO":
        return "RELEASE_READY_RECHECK_REQUIRED"
    missing = failed_preflight_ids(prereq)
    if int(candidate_scan.get("go_candidate_count", 0) or 0) > 0 and not missing:
        return "READY_FOR_ENDPOINT_FIRST_M6_RC_CLOSEOUT"
    if int(candidate_scan.get("go_candidate_count", 0) or 0) > 0:
        return "GO_CANDIDATE_AWAITING_PREFLIGHT"
    return "WAITING_FOR_REAL_ADAPTER_INPUTS"


def build_handoff(args: argparse.Namespace) -> dict[str, Any]:
    candidate_scan = read_json(args.candidate_scan)
    prereq = read_json(args.prereq_audit)
    readiness = read_json(args.readiness_audit)
    missing = failed_preflight_ids(prereq)
    go_commands = go_candidate_commands(candidate_scan)
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-real-adapter-cuda-handoff",
        "decision": decision(candidate_scan, prereq, readiness),
        "m6_rc_claimed_go": False,
        "release_claimed_go": False,
        "executable_artifact": args.shell_output,
        "inputs": {
            "adapter_root": args.adapter_root,
            "adapter_dir": default_paths(args.adapter_root)[0],
            "adapter_manifest": default_paths(args.adapter_root)[1],
            "base_model": args.base_model,
            "image": args.image,
            "agent_id": args.agent_id,
            "model_cache_dir": args.model_cache_dir,
        },
        "current_state": {
            "candidate_scan_decision": candidate_scan.get("decision"),
            "candidate_count": candidate_scan.get("candidate_count"),
            "go_candidate_count": candidate_scan.get("go_candidate_count"),
            "fixture_like_candidate_count": candidate_scan.get("fixture_like_candidate_count"),
            "prereq_status": prereq.get("status"),
            "prereq_decision": prereq.get("decision"),
            "missing_prereq_ids": missing,
            "v0_readiness_decision": readiness.get("decision"),
            "v0_release_ready": readiness.get("release_ready"),
            "v0_blockers": readiness.get("blockers", []),
            "v0_unexpected_blockers": readiness.get("unexpected_blockers", []),
            "real_adapter_evidence_bundle_decision": readiness.get("summary", {}).get("real_adapter_evidence_bundle_decision")
            if isinstance(readiness.get("summary"), dict)
            else None,
            "real_adapter_evidence_bundle_ready": readiness.get("summary", {}).get("real_adapter_evidence_bundle_ready")
            if isinstance(readiness.get("summary"), dict)
            else None,
        },
        "bundle_archive_contract": {
            "bundle_dir": args.bundle_dir,
            "bundle_archive_output": args.bundle_archive_output,
            "producer": "scripts/build_real_adapter_evidence_bundle.py",
            "required_metadata_files": [
                args.bundle_manifest_output,
                args.bundle_json_output,
            ],
            "local_closeout_command_id": "local_closeout_after_bundle_transfer",
            "local_closeout_requires_metadata": True,
            "missing_or_mismatched_metadata_status": "archive_metadata_not_verified",
            "expected_success_status": "GO_V0_RELEASE_CLOSEOUT",
        },
        "required_operator_inputs": required_inputs(prereq),
        "command_sequence": base_commands(args, candidate_scan),
        "post_transfer_closeout_commands": post_transfer_closeout_commands(args),
        "go_candidate_commands": go_commands,
        "operator_rules": [
            "Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.",
            "Do not use fixture-sized or self-test adapters as release evidence.",
            "The Docker image must package the same adapter hash recorded by manifest.json.",
            "The live endpoint capture must produce structured JSON sidecar evidence from source live_docker_capture.",
            "Capture endpoint evidence before updating M6 review docs to GO; the generated shell stops before M6 GO verification until those docs contain final GO markers.",
            "Run build_real_adapter_evidence_bundle.py to assemble the fixed evidence bundle and metadata-bearing portable archive, then require GO_REAL_ADAPTER_EVIDENCE_BUNDLE before v0 readiness recheck.",
            "The archive must include real_adapter_evidence_bundle_manifest.json and real_adapter_evidence_bundle_verification.json; local closeout rejects missing or mismatched metadata with archive_metadata_not_verified.",
            "After transferring the metadata-bearing bundle archive back to the release workstation, run run_v0_release_closeout_from_bundle.py and require GO_V0_RELEASE_CLOSEOUT.",
            "M6-RC and v0 remain NOT_GO until the M6 verifier, real adapter bundle verifier, and v0 readiness verifier all return GO.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    state = report["current_state"]
    archive_contract = report["bundle_archive_contract"]
    inputs = "\n".join(
        f"| `{row['id']}` | {row['status']} | {row['requirement']} |" for row in report["required_operator_inputs"]
    )
    commands = "\n\n".join(
        f"### {row['id']}\n\n```bash\n{row['shell']}\n```" for row in report["command_sequence"]
    )
    closeout_commands = "\n\n".join(
        f"### {row['id']}\n\n```bash\n{row['shell']}\n```\n\n{row['note']}"
        for row in report["post_transfer_closeout_commands"]
    )
    candidate_commands = "\n\n".join(
        f"### {row['id']}\n\n```bash\n{row['shell']}\n```" for row in report["go_candidate_commands"]
    )
    rules = "\n".join(f"- {item}" for item in report["operator_rules"])
    text = f"""# Real Adapter CUDA Handoff

```yaml
date: {report["date"]}
gate: {report["gate"]}
decision: {report["decision"]}
m6_rc_claimed_go: false
release_claimed_go: false
```

M6-RC remains NOT_GO until a real trained CUDA `lora_adapter` produces no-fake Docker endpoint evidence and the M6/v0 verifiers return GO.

Executable shell artifact: `{report["executable_artifact"]}`. Run it only on the CUDA host after placing the real trained adapter under the configured adapter root and setting `MIB_RUNTIME_BEARER_TOKEN`.

## Current State

```yaml
candidate_scan_decision: {state["candidate_scan_decision"]}
candidate_count: {state["candidate_count"]}
go_candidate_count: {state["go_candidate_count"]}
fixture_like_candidate_count: {state["fixture_like_candidate_count"]}
prereq_status: {state["prereq_status"]}
prereq_decision: {state["prereq_decision"]}
missing_prereq_ids: {json.dumps(state["missing_prereq_ids"])}
v0_readiness_decision: {state["v0_readiness_decision"]}
v0_release_ready: {str(state["v0_release_ready"]).lower()}
real_adapter_evidence_bundle_decision: {state["real_adapter_evidence_bundle_decision"]}
real_adapter_evidence_bundle_ready: {str(state["real_adapter_evidence_bundle_ready"]).lower()}
v0_blockers: {json.dumps(state["v0_blockers"])}
v0_unexpected_blockers: {json.dumps(state["v0_unexpected_blockers"])}
```

## Required Inputs

| Check | Status | Requirement |
| --- | --- | --- |
{inputs}

## Operator Rules

{rules}

## Bundle Archive Contract

```yaml
producer: {archive_contract["producer"]}
bundle_dir: {archive_contract["bundle_dir"]}
bundle_archive_output: {archive_contract["bundle_archive_output"]}
required_metadata_files: {json.dumps(archive_contract["required_metadata_files"])}
local_closeout_requires_metadata: true
missing_or_mismatched_metadata_status: {archive_contract["missing_or_mismatched_metadata_status"]}
expected_success_status: {archive_contract["expected_success_status"]}
```

## Command Sequence

{commands}

## Local Closeout After Metadata-Bearing Bundle Transfer

Copy the metadata-bearing `artifacts/review/real_adapter_evidence_bundle.tar.gz` from the CUDA host back into this repository, then run:

{closeout_commands}
"""
    if candidate_commands:
        text += f"""

## GO Candidate Commands

These commands were emitted by the latest candidate scan for candidates that passed real-adapter intake.

{candidate_commands}
"""
    return text


def render_shell(report: dict[str, Any]) -> str:
    commands = "\n\n".join(
        f"printf '\\n== {row['id']} ==\\n'\n{script_command(row)}" for row in report["command_sequence"]
    )
    closeout_commands = "\n".join(f"# {row['id']}: {row['shell']}" for row in report["post_transfer_closeout_commands"])
    return f"""#!/usr/bin/env bash
set -euo pipefail

# Generated by scripts/build_real_adapter_handoff.py.
# Run only on the CUDA host with the real trained adapter and matching Docker image.
# This script intentionally keeps M6-RC and v0 NOT_GO until every verifier returns GO.

if [ -n "${{MIB_RUNTIME_ALLOW_FAKE_BACKEND:-}}" ]; then
  echo "Refusing to run: MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset." >&2
  exit 2
fi

if [ -z "${{MIB_RUNTIME_BEARER_TOKEN:-}}" ] || [ "${{#MIB_RUNTIME_BEARER_TOKEN}}" -lt 32 ] || [ "${{MIB_RUNTIME_BEARER_TOKEN}}" = "<set-32-plus-character-token>" ]; then
  echo "Refusing to run: set a real MIB_RUNTIME_BEARER_TOKEN with at least 32 characters." >&2
  exit 2
fi

{commands}

printf '\\n== local_closeout_after_bundle_transfer ==\\n'
cat <<'MIB_LOCAL_CLOSEOUT'
Copy artifacts/review/real_adapter_evidence_bundle.tar.gz from the CUDA host
back into this repository, then run the local closeout command below.
The archive must be metadata-bearing and include:
- real_adapter_evidence_bundle_manifest.json
- real_adapter_evidence_bundle_verification.json
Missing or mismatched metadata returns archive_metadata_not_verified and
prevents promotion.
Expected success status: GO_V0_RELEASE_CLOSEOUT.

{closeout_commands}
MIB_LOCAL_CLOSEOUT
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a CUDA-host handoff for the remaining real adapter M6-RC blocker.")
    parser.add_argument("--candidate-scan", default="artifacts/review/real_adapter_candidate_scan.json")
    parser.add_argument("--prereq-audit", default="artifacts/review/m6_real_adapter_prereq_audit.json")
    parser.add_argument("--readiness-audit", default="artifacts/review/v0_release_readiness_audit.json")
    parser.add_argument("--adapter-root", default="/tmp/mib-real-adapter")
    parser.add_argument("--base-model", choices=sorted(LOCKED_BASE_MODELS), required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--python", default="./.venv/bin/python")
    parser.add_argument("--adapter-intake-json-output", default="artifacts/review/real_adapter_artifact_intake.json")
    parser.add_argument("--endpoint-output", default="artifacts/review/real_trained_adapter_endpoint_evidence.md")
    parser.add_argument("--endpoint-json-output", default="artifacts/review/real_trained_adapter_endpoint_evidence.json")
    parser.add_argument("--m6-json-output", default="artifacts/review/m6_rc_evidence_verification.json")
    parser.add_argument("--gate-json-output", default="artifacts/review/m6_real_adapter_rc_gate_run.json")
    parser.add_argument("--bundle-dir", default="artifacts/review/real_adapter_evidence_bundle")
    parser.add_argument("--bundle-json-output", default="artifacts/review/real_adapter_evidence_bundle_verification.json")
    parser.add_argument("--bundle-manifest-output", default="artifacts/review/real_adapter_evidence_bundle_manifest.json")
    parser.add_argument("--bundle-archive-output", default="artifacts/review/real_adapter_evidence_bundle.tar.gz")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_cuda_handoff.json")
    parser.add_argument("--markdown-output", default="artifacts/review/real_adapter_cuda_handoff.md")
    parser.add_argument("--shell-output", default="artifacts/review/real_adapter_cuda_handoff.sh")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_handoff(args)
    write_json(args.json_output, report)
    write_text(args.markdown_output, render_markdown(report))
    write_text(args.shell_output, render_shell(report))
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "markdown_output": args.markdown_output,
                "shell_output": args.shell_output,
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
