#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_external_cuda_operator_packet.v1"
STATUS = "PREPARED_NOT_RUN"
PRIMARY_HANDOFF = "artifacts/review/real_adapter_cuda_training_handoff.sh"
VERIFIED_LAUNCHER_HANDOFF = "artifacts/review/verified_external_cuda_training_launcher.sh"
REQUIRED_COMMITTED_FILES = {
    "training_handoff_json": "artifacts/review/real_adapter_cuda_training_handoff.json",
    "training_handoff_markdown": "artifacts/review/real_adapter_cuda_training_handoff.md",
    "training_handoff_shell": "artifacts/review/real_adapter_cuda_training_handoff.sh",
    "rc_handoff_json": "artifacts/review/real_adapter_cuda_handoff.json",
    "rc_handoff_markdown": "artifacts/review/real_adapter_cuda_handoff.md",
    "rc_handoff_shell": "artifacts/review/real_adapter_cuda_handoff.sh",
    "recertification_summary": "artifacts/review/v0_release_blocker_recertification.json",
    "router_training_dataset": "examples/fixtures/router_20.jsonl",
    "strict_model_cache_preparation": "scripts/prepare_strict_model_cache.py",
    "training_handoff_generator": "scripts/prepare_cuda_lora_training_run.py",
    "cuda_training_preflight": "scripts/check_cuda_lora_training_prereqs.py",
    "cuda_base_image_resolver": "scripts/resolve_cuda_base_image.py",
    "docker_image_handoff_generator": "scripts/prepare_real_adapter_docker_image.py",
    "real_adapter_rc_gate": "scripts/run_m6_real_adapter_rc_gate.py",
    "evidence_bundle_builder": "scripts/build_real_adapter_evidence_bundle.py",
    "bundle_closeout": "scripts/run_v0_release_closeout_from_bundle.py",
}
FORBIDDEN_COMMITTED_ARTIFACTS = [
    "model weights",
    "LoRA adapter files or /tmp/mib-real-adapter contents",
    "Docker image layers or archives",
    "raw live endpoint transcripts",
    "copied external real-adapter evidence bundles",
]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(root: Path, path: str) -> dict[str, Any]:
    data = json.loads((root / path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def required_file_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role, relative in REQUIRED_COMMITTED_FILES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required packet file is missing: {relative}")
        rows.append(
            {
                "role": role,
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def command_ids(report: dict[str, Any], key: str) -> list[str]:
    value = report.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(row["id"]) for row in value if isinstance(row, dict) and row.get("id")]


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    training = read_json(root, args.training_handoff_json)
    rc_handoff = read_json(root, args.rc_handoff_json)
    recertification = read_json(root, args.recertification_json)
    recertification_primary = str(recertification.get("primary_external_handoff") or PRIMARY_HANDOFF)
    primary_handoff = PRIMARY_HANDOFF

    if recertification_primary not in {PRIMARY_HANDOFF, VERIFIED_LAUNCHER_HANDOFF}:
        raise ValueError(f"unexpected recertification primary handoff: {recertification_primary}")
    if training.get("release_claimed_go") is True or recertification.get("release_claimed_go") is True:
        raise ValueError("operator packet refuses to build from GO-claiming handoff artifacts")

    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-external-cuda-operator-packet",
        "status": STATUS,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "root": str(root),
        "git": {
            "branch": args.git_branch or run_git(root, "branch", "--show-current"),
            "head": args.git_head or run_git(root, "rev-parse", "--short", "HEAD"),
            "remote_origin": args.remote_origin or run_git(root, "config", "--get", "remote.origin.url"),
            "clean_worktree_required": True,
        },
        "primary_external_handoff": primary_handoff,
        "recertification_primary_external_handoff": recertification_primary,
        "primary_handoff_status": training.get("status"),
        "recertification_status": recertification.get("status"),
        "required_committed_files": required_file_rows(root),
        "package_readiness_checks": training.get("package_readiness_checks", []),
        "command_order": {
            "training_handoff": command_ids(training, "command_sequence"),
            "rc_handoff": command_ids(rc_handoff, "command_sequence"),
            "post_transfer_closeout": command_ids(rc_handoff, "post_transfer_closeout_commands"),
        },
        "operator_sequence": [
            f"Clone or update the repository to commit {args.git_head or run_git(root, 'rev-parse', '--short', 'HEAD')}.",
            f"Verify the required_committed_files sha256 values before running {primary_handoff}.",
            f"Run {primary_handoff} on the external CUDA host and require all package_readiness_checks to pass.",
            "Run the downstream no-fake endpoint/M6/evidence-bundle commands emitted by artifacts/review/real_adapter_cuda_handoff.sh.",
            "Transfer the metadata-bearing artifacts/review/real_adapter_evidence_bundle.tar.gz back to the release workstation.",
            "Run scripts/run_v0_release_closeout_from_bundle.py only after accepted M6 GO review docs are present in the same checkout.",
        ],
        "expected_return_artifacts": [
            "artifacts/review/real_adapter_evidence_bundle.tar.gz",
            "artifacts/review/real_adapter_evidence_bundle_manifest.json",
            "artifacts/review/real_adapter_evidence_bundle_verification.json",
            "accepted GO updates to docs/reviews/M6/SIGNOFF_MATRIX.md",
            "accepted GO updates to docs/reviews/M6/CTO_DECISION.md",
        ],
        "forbidden_committed_artifacts": FORBIDDEN_COMMITTED_ARTIFACTS,
        "notes": [
            "This packet is a commit-pinned operator handoff only; it does not contain model weights, adapter files, Docker images, endpoint transcripts, or copied external evidence bundles.",
            "Do not claim M6-RC or v0 release GO until real trained adapter evidence, accepted M6 review docs, bundle verification, and v0 readiness all return GO.",
        ],
    }


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def render_markdown(packet: dict[str, Any]) -> str:
    files = "\n".join(
        f"- `{row['path']}` ({row['role']}): `{row['sha256']}`"
        for row in packet["required_committed_files"]
    )
    readiness = "\n".join(
        f"- `{row.get('id')}`: `{row.get('path')}`"
        for row in packet.get("package_readiness_checks", [])
        if isinstance(row, dict)
    )
    sequence = "\n".join(f"{index}. {item}" for index, item in enumerate(packet["operator_sequence"], start=1))
    returns = "\n".join(f"- `{item}`" for item in packet["expected_return_artifacts"])
    forbidden = "\n".join(f"- {item}" for item in packet["forbidden_committed_artifacts"])
    return f"""# External CUDA Operator Packet

```yaml
schema_version: {packet["schema_version"]}
date: {packet["date"]}
gate: {packet["gate"]}
status: {packet["status"]}
release_claimed_go: false
m6_rc_claimed_go: false
git_head: {packet["git"]["head"]}
primary_external_handoff: {packet["primary_external_handoff"]}
```

## Required Committed Files

{files}

## Package Readiness Checks

{readiness}

## Operator Sequence

{sequence}

## Expected Return Artifacts

{returns}

## Forbidden Committed Artifacts

{forbidden}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a commit-pinned external CUDA operator packet for real-adapter evidence production.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--training-handoff-json", default="artifacts/review/real_adapter_cuda_training_handoff.json")
    parser.add_argument("--rc-handoff-json", default="artifacts/review/real_adapter_cuda_handoff.json")
    parser.add_argument("--recertification-json", default="artifacts/review/v0_release_blocker_recertification.json")
    parser.add_argument("--git-head")
    parser.add_argument("--git-branch")
    parser.add_argument("--remote-origin")
    parser.add_argument("--json-output", default="artifacts/review/external_cuda_operator_packet.json")
    parser.add_argument("--markdown-output", default="artifacts/review/external_cuda_operator_packet.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = build_packet(args)
    write_json(args.json_output, packet)
    markdown = Path(args.markdown_output)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "markdown_output": args.markdown_output,
                "status": packet["status"],
                "release_claimed_go": packet["release_claimed_go"],
                "primary_external_handoff": packet["primary_external_handoff"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
