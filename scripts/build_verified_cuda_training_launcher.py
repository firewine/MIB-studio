#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_verified_external_cuda_training_launcher.v1"
STATUS = "PREPARED_NOT_RUN"
VERIFIER_DECISION = "GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION"
TRANSFER_READY_STATUS = "READY_EXTERNAL_CUDA_OPERATOR_TRANSFER"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_text(path: str | Path, value: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def command_row(command_id: str, argv: list[str], *, note: str) -> dict[str, Any]:
    return {"id": command_id, "argv": argv, "shell": shlex.join(argv), "note": note}


def build_launcher(args: argparse.Namespace) -> dict[str, Any]:
    verify_command = [
        args.python,
        args.verifier_script,
        "--packet-json",
        args.packet_json,
        "--expected-decision",
        "GO",
        "--json-output",
        args.verification_output,
    ]
    transfer_manifest_command = [
        args.python,
        args.transfer_manifest_script,
        "--packet-json",
        args.packet_json,
        "--packet-verification-json",
        args.verification_output,
        "--json-output",
        args.transfer_manifest_json_output,
        "--markdown-output",
        args.transfer_manifest_markdown_output,
        "--expected-status",
        TRANSFER_READY_STATUS,
    ]
    training_command = ["bash", args.training_handoff_shell]
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-verified-external-cuda-training-launcher",
        "status": STATUS,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "purpose": "Run operator-packet verification before invoking the external CUDA real-adapter training handoff.",
        "inputs": {
            "python": args.python,
            "verifier_script": args.verifier_script,
            "packet_json": args.packet_json,
            "verification_output": args.verification_output,
            "expected_verifier_decision": VERIFIER_DECISION,
            "transfer_manifest_script": args.transfer_manifest_script,
            "transfer_manifest_json_output": args.transfer_manifest_json_output,
            "transfer_manifest_markdown_output": args.transfer_manifest_markdown_output,
            "expected_transfer_manifest_status": TRANSFER_READY_STATUS,
            "training_handoff_shell": args.training_handoff_shell,
        },
        "command_sequence": [
            command_row("verify_external_cuda_operator_packet", verify_command, note="Require operator-packet integrity GO before any CUDA training command runs."),
            command_row("build_external_cuda_operator_transfer_manifest", transfer_manifest_command, note="Require full-checkout transfer/readiness manifest before invoking CUDA training."),
            command_row("run_real_adapter_cuda_training_handoff", training_command, note="Invoke the existing guarded CUDA training handoff only after packet and transfer-manifest readiness pass."),
        ],
        "guardrails": [
            "Refuse to run when MIB_RUNTIME_ALLOW_FAKE_BACKEND is set.",
            "Refuse to run when repo Python, verifier script, transfer manifest script, operator packet, or CUDA training handoff shell is missing.",
            "Require READY_EXTERNAL_CUDA_OPERATOR_TRANSFER before invoking the CUDA training handoff.",
            "Do not claim M6-RC or v0 release GO from launcher execution alone.",
        ],
    }


def render_markdown(launcher: dict[str, Any]) -> str:
    commands = "\n\n".join(f"### {row['id']}\n\n```bash\n{row['shell']}\n```" for row in launcher["command_sequence"])
    guardrails = "\n".join(f"- {item}" for item in launcher["guardrails"])
    return f"""# Verified External CUDA Training Launcher

```yaml
schema_version: {launcher["schema_version"]}
date: {launcher["date"]}
gate: {launcher["gate"]}
status: {launcher["status"]}
release_claimed_go: false
m6_rc_claimed_go: false
expected_verifier_decision: {launcher["inputs"]["expected_verifier_decision"]}
expected_transfer_manifest_status: {launcher["inputs"]["expected_transfer_manifest_status"]}
training_handoff_shell: {launcher["inputs"]["training_handoff_shell"]}
```

This launcher verifies the external CUDA operator packet before running the real-adapter CUDA training handoff. It does not contain model weights, adapter files, Docker images, endpoint transcripts, copied evidence bundles, or release GO evidence.

## Guardrails

{guardrails}

## Command Sequence

{commands}
"""


def render_shell(launcher: dict[str, Any]) -> str:
    inputs = launcher["inputs"]
    python = shlex.quote(inputs["python"])
    verifier_script = shlex.quote(inputs["verifier_script"])
    transfer_manifest_script = shlex.quote(inputs["transfer_manifest_script"])
    packet_json = shlex.quote(inputs["packet_json"])
    training_handoff_shell = shlex.quote(inputs["training_handoff_shell"])
    commands = "\n\n".join(
        f"printf '\\n== {row['id']} ==\\n'\n{row['shell']}"
        for row in launcher["command_sequence"]
    )
    return f"""#!/usr/bin/env bash
set -euo pipefail

# Generated by scripts/build_verified_cuda_training_launcher.py.
# Run this on the external CUDA host instead of invoking the training handoff directly.

if [ -n "${{MIB_RUNTIME_ALLOW_FAKE_BACKEND:-}}" ]; then
  echo "Refusing to run: MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset." >&2
  exit 2
fi

if [ ! -x {python} ]; then
  echo "Refusing to run: Python executable is missing or not executable: {python}" >&2
  exit 2
fi

if [ ! -f {verifier_script} ]; then
  echo "Refusing to run: operator packet verifier is missing: {verifier_script}" >&2
  exit 2
fi

if [ ! -f {transfer_manifest_script} ]; then
  echo "Refusing to run: operator transfer manifest builder is missing: {transfer_manifest_script}" >&2
  exit 2
fi

if [ ! -f {packet_json} ]; then
  echo "Refusing to run: operator packet JSON is missing: {packet_json}" >&2
  exit 2
fi

if [ ! -f {training_handoff_shell} ]; then
  echo "Refusing to run: CUDA training handoff shell is missing: {training_handoff_shell}" >&2
  exit 2
fi

{commands}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a verified external CUDA training launcher.")
    parser.add_argument("--python", default="./.venv/bin/python")
    parser.add_argument("--verifier-script", default="scripts/verify_external_cuda_operator_packet.py")
    parser.add_argument("--transfer-manifest-script", default="scripts/build_external_cuda_operator_transfer_manifest.py")
    parser.add_argument("--packet-json", default="artifacts/review/external_cuda_operator_packet.json")
    parser.add_argument("--verification-output", default="artifacts/review/external_cuda_operator_packet_verification.json")
    parser.add_argument("--transfer-manifest-json-output", default="artifacts/review/external_cuda_operator_transfer_manifest.json")
    parser.add_argument("--transfer-manifest-markdown-output", default="artifacts/review/external_cuda_operator_transfer_manifest.md")
    parser.add_argument("--training-handoff-shell", default="artifacts/review/real_adapter_cuda_training_handoff.sh")
    parser.add_argument("--json-output", default="artifacts/review/verified_external_cuda_training_launcher.json")
    parser.add_argument("--markdown-output", default="artifacts/review/verified_external_cuda_training_launcher.md")
    parser.add_argument("--shell-output", default="artifacts/review/verified_external_cuda_training_launcher.sh")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    launcher = build_launcher(args)
    write_json(args.json_output, launcher)
    write_text(args.markdown_output, render_markdown(launcher))
    write_text(args.shell_output, render_shell(launcher))
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "markdown_output": args.markdown_output,
                "shell_output": args.shell_output,
                "status": launcher["status"],
                "release_claimed_go": launcher["release_claimed_go"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
