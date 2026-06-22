#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_external_cuda_operator_transfer_manifest.v1"
PACKET_SCHEMA_VERSION = "mib_external_cuda_operator_packet.v1"
PACKET_VERIFICATION_SCHEMA_VERSION = "mib_external_cuda_operator_packet_verification.v1"
GO_PACKET_VERIFICATION = "GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION"
READY_STATUS = "READY_EXTERNAL_CUDA_OPERATOR_TRANSFER"
NOT_READY_STATUS = "NOT_READY_EXTERNAL_CUDA_OPERATOR_TRANSFER"
VERIFIED_LAUNCHER_HANDOFF = "artifacts/review/verified_external_cuda_training_launcher.sh"
TRAINING_HANDOFF = "artifacts/review/real_adapter_cuda_training_handoff.sh"
TRANSFER_MANIFEST_BUILDER = "scripts/build_external_cuda_operator_transfer_manifest.py"
FORBIDDEN_TRANSFER_PAYLOADS = [
    "model weights",
    "LoRA adapter files or /tmp/mib-real-adapter contents",
    "Docker image layers or archives",
    "raw live endpoint transcripts",
    "copied external real-adapter evidence bundles",
]
EXTERNAL_HOST_PREREQS = [
    ".venv/bin/python",
    ".venv/bin/llamafactory-cli",
    "nvidia-smi",
    "/tmp/mib-real-adapter/backend_config.yaml",
    "/tmp/mib-strict-model-cache-phi/model_cache",
    "Docker daemon access",
    "digest-pinned CUDA/Python base image from artifacts/review/real_adapter_cuda_base_image.env",
]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def checkout_relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def read_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "expected JSON object"
    return payload, None


def check_row(check_id: str, ok: bool, detail: str, *, missing_markers: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": ok,
        "detail": detail,
        "missing_markers": missing_markers or [],
    }


def safe_relative_path(path: str) -> bool:
    candidate = Path(path)
    return not candidate.is_absolute() and ".." not in candidate.parts


def required_packet_paths(packet: dict[str, Any]) -> tuple[list[str], list[str]]:
    rows = packet.get("required_committed_files")
    if not isinstance(rows, list):
        return [], ["required_committed_files"]

    paths: list[str] = []
    failures: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            failures.append(f"row_{index}_object")
            continue
        path = row.get("path")
        if not isinstance(path, str):
            failures.append(f"row_{index}_path")
            continue
        if not safe_relative_path(path):
            failures.append(f"{path}:unsafe_path")
            continue
        paths.append(path)
    return paths, failures


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def current_checkout_file_rows(root: Path, paths: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for path in unique_paths(paths):
        if not safe_relative_path(path):
            missing.append(f"{path}:unsafe_path")
            continue
        file_path = root / path
        exists = file_path.is_file()
        rows.append(
            {
                "path": path,
                "exists": exists,
                "size_bytes": file_path.stat().st_size if exists else None,
            }
        )
        if not exists:
            missing.append(path)
    return rows, missing


def verification_warnings(verification: dict[str, Any]) -> list[Any]:
    warnings = verification.get("warnings", [])
    return warnings if isinstance(warnings, list) else ["warnings_not_list"]


def forbidden_tracked_artifacts(verification: dict[str, Any]) -> list[Any]:
    summary = verification.get("summary")
    if not isinstance(summary, dict):
        return ["summary_missing"]
    markers = summary.get("forbidden_tracked_artifacts", [])
    return markers if isinstance(markers, list) else ["forbidden_tracked_artifacts_not_list"]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    packet_path = resolve_path(root, args.packet_json)
    verification_path = resolve_path(root, args.packet_verification_json)
    packet, packet_error = read_json_file(packet_path)
    verification, verification_error = read_json_file(verification_path)
    checks: list[dict[str, Any]] = []

    checks.append(
        check_row(
            "packet_json_present",
            packet_error is None,
            "ok" if packet_error is None else packet_error,
            missing_markers=[] if packet_error is None else ["packet_json"],
        )
    )
    checks.append(
        check_row(
            "packet_verification_json_present",
            verification_error is None,
            "ok" if verification_error is None else verification_error,
            missing_markers=[] if verification_error is None else ["packet_verification_json"],
        )
    )

    packet = packet or {}
    verification = verification or {}
    packet_git = packet.get("git") if isinstance(packet.get("git"), dict) else {}
    packet_source_commit = packet_git.get("head") if isinstance(packet_git, dict) else None
    verification_source_commit = verification.get("packet_handoff_source_commit")
    packet_paths, packet_path_failures = required_packet_paths(packet)
    current_checkout_paths = unique_paths(
        [
            checkout_relative_path(root, packet_path),
            checkout_relative_path(root, verification_path),
            VERIFIED_LAUNCHER_HANDOFF,
            TRAINING_HANDOFF,
            TRANSFER_MANIFEST_BUILDER,
            *packet_paths,
        ]
    )
    current_rows, missing_current_files = current_checkout_file_rows(root, current_checkout_paths)
    packet_verifier_warnings = verification_warnings(verification)
    forbidden_markers = forbidden_tracked_artifacts(verification)

    checks.extend(
        [
            check_row(
                "packet_schema",
                packet.get("schema_version") == PACKET_SCHEMA_VERSION,
                "ok" if packet.get("schema_version") == PACKET_SCHEMA_VERSION else "unexpected packet schema",
                missing_markers=[] if packet.get("schema_version") == PACKET_SCHEMA_VERSION else ["packet_schema_version"],
            ),
            check_row(
                "packet_verification_schema",
                verification.get("schema_version") == PACKET_VERIFICATION_SCHEMA_VERSION,
                "ok" if verification.get("schema_version") == PACKET_VERIFICATION_SCHEMA_VERSION else "unexpected packet verification schema",
                missing_markers=[]
                if verification.get("schema_version") == PACKET_VERIFICATION_SCHEMA_VERSION
                else ["packet_verification_schema_version"],
            ),
            check_row(
                "packet_verification_go",
                verification.get("decision") == GO_PACKET_VERIFICATION,
                "ok" if verification.get("decision") == GO_PACKET_VERIFICATION else "packet verification is not GO",
                missing_markers=[] if verification.get("decision") == GO_PACKET_VERIFICATION else ["GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION"],
            ),
            check_row(
                "packet_verification_ok",
                verification.get("verification_ok") is True,
                "ok" if verification.get("verification_ok") is True else "verification_ok is not true",
                missing_markers=[] if verification.get("verification_ok") is True else ["verification_ok"],
            ),
            check_row(
                "operator_packet_ready",
                verification.get("operator_packet_ready") is True,
                "ok" if verification.get("operator_packet_ready") is True else "operator packet is not ready",
                missing_markers=[] if verification.get("operator_packet_ready") is True else ["operator_packet_ready"],
            ),
            check_row(
                "packet_verification_warnings_empty",
                packet_verifier_warnings == [],
                "ok" if packet_verifier_warnings == [] else "packet verification warnings are present",
                missing_markers=[str(item) for item in packet_verifier_warnings],
            ),
            check_row(
                "forbidden_tracked_artifacts_empty",
                forbidden_markers == [],
                "ok" if forbidden_markers == [] else "forbidden tracked artifacts are present",
                missing_markers=[str(item) for item in forbidden_markers],
            ),
            check_row(
                "release_claimed_go_false",
                packet.get("release_claimed_go") is False and verification.get("release_claimed_go") is False,
                "ok" if packet.get("release_claimed_go") is False and verification.get("release_claimed_go") is False else "release GO is claimed",
                missing_markers=[] if packet.get("release_claimed_go") is False and verification.get("release_claimed_go") is False else ["release_claimed_go"],
            ),
            check_row(
                "m6_rc_claimed_go_false",
                packet.get("m6_rc_claimed_go") is False and verification.get("m6_rc_claimed_go") is False,
                "ok" if packet.get("m6_rc_claimed_go") is False and verification.get("m6_rc_claimed_go") is False else "M6-RC GO is claimed",
                missing_markers=[] if packet.get("m6_rc_claimed_go") is False and verification.get("m6_rc_claimed_go") is False else ["m6_rc_claimed_go"],
            ),
            check_row(
                "packet_source_commit_matches_verification",
                isinstance(packet_source_commit, str) and packet_source_commit == verification_source_commit,
                "ok" if isinstance(packet_source_commit, str) and packet_source_commit == verification_source_commit else "packet/verification source commit mismatch",
                missing_markers=[]
                if isinstance(packet_source_commit, str) and packet_source_commit == verification_source_commit
                else ["packet_handoff_source_commit"],
            ),
            check_row(
                "primary_external_handoff_verified_launcher",
                packet.get("primary_external_handoff") == VERIFIED_LAUNCHER_HANDOFF,
                "ok" if packet.get("primary_external_handoff") == VERIFIED_LAUNCHER_HANDOFF else "primary handoff is not verified launcher",
                missing_markers=[] if packet.get("primary_external_handoff") == VERIFIED_LAUNCHER_HANDOFF else ["primary_external_handoff"],
            ),
            check_row(
                "required_committed_files_parseable",
                not packet_path_failures,
                "ok" if not packet_path_failures else "packet required file rows are invalid",
                missing_markers=packet_path_failures,
            ),
            check_row(
                "required_current_checkout_files_present",
                not missing_current_files,
                "ok" if not missing_current_files else "required full-checkout files are missing",
                missing_markers=missing_current_files,
            ),
        ]
    )

    blockers = [row["id"] for row in checks if not row["ok"]]
    status = READY_STATUS if not blockers else NOT_READY_STATUS
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "status": status,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "root": str(root),
        "current_checkout_head": run_git(root, "rev-parse", "--short", "HEAD"),
        "packet_json": str(packet_path),
        "packet_verification_json": str(verification_path),
        "packet_handoff_source_commit": packet_source_commit,
        "primary_external_handoff": packet.get("primary_external_handoff"),
        "transfer_model": "full_repository_checkout_required",
        "full_checkout_required": True,
        "partial_file_archive_allowed": False,
        "why_full_checkout_required": [
            "The verified launcher and downstream handoff scripts import repository Python modules and expect the committed repo tree.",
            "The CUDA operator path depends on scripts, examples, services/shared contracts, docs review state, artifacts/review metadata, and a local .venv.",
            "A partial file archive can omit import dependencies or source-pinned files that packet verification is designed to check.",
        ],
        "operator_commands": [
            f"Run scripts/verify_external_cuda_operator_packet.py --expected-decision GO before executing {VERIFIED_LAUNCHER_HANDOFF}.",
            f"Run {VERIFIED_LAUNCHER_HANDOFF} from the full repository checkout on the external CUDA host.",
            "Return only metadata-bearing review artifacts required by the M6/v0 closeout path after real endpoint evidence exists.",
        ],
        "required_current_checkout_files": current_rows,
        "external_host_prereqs": EXTERNAL_HOST_PREREQS,
        "forbidden_transfer_payloads": FORBIDDEN_TRANSFER_PAYLOADS,
        "checks": checks,
        "blockers": blockers,
        "operator_notes": [
            "This manifest does not claim M6-RC or v0 release GO.",
            "Do not transfer model weights, adapters, Docker layers, raw endpoint transcripts, or copied external evidence bundles into git.",
            "The local release remains NOT_GO until accepted real trained CUDA lora_adapter no-fake Docker endpoint evidence exists.",
        ],
    }


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def render_markdown(manifest: dict[str, Any]) -> str:
    checks = "\n".join(
        f"- `{row['id']}`: `{row['ok']}` - {row['detail']}"
        for row in manifest["checks"]
    )
    required_files = "\n".join(
        f"- `{row['path']}`: `{row['exists']}`"
        for row in manifest["required_current_checkout_files"]
    )
    prereqs = "\n".join(f"- `{item}`" for item in manifest["external_host_prereqs"])
    commands = "\n".join(f"{index}. {item}" for index, item in enumerate(manifest["operator_commands"], start=1))
    forbidden = "\n".join(f"- {item}" for item in manifest["forbidden_transfer_payloads"])
    return f"""# External CUDA Operator Transfer Manifest

```yaml
schema_version: {manifest["schema_version"]}
status: {manifest["status"]}
release_claimed_go: false
m6_rc_claimed_go: false
transfer_model: full repository checkout required
full_checkout_required: true
partial_file_archive_allowed: false
packet_handoff_source_commit: {manifest["packet_handoff_source_commit"]}
current_checkout_head: {manifest["current_checkout_head"]}
primary_external_handoff: {manifest["primary_external_handoff"]}
```

## Checks

{checks}

## Required Current Checkout Files

{required_files}

## External Host Prereqs

{prereqs}

## Operator Commands

{commands}

## Forbidden Transfer Payloads

{forbidden}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a full-checkout transfer/readiness manifest for the external CUDA operator path.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--packet-json", default="artifacts/review/external_cuda_operator_packet.json")
    parser.add_argument("--packet-verification-json", default="artifacts/review/external_cuda_operator_packet_verification.json")
    parser.add_argument("--json-output", default="artifacts/review/external_cuda_operator_transfer_manifest.json")
    parser.add_argument("--markdown-output", default="artifacts/review/external_cuda_operator_transfer_manifest.md")
    parser.add_argument("--expected-status", choices=[READY_STATUS, NOT_READY_STATUS])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    write_json(args.json_output, manifest)
    markdown = Path(args.markdown_output)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(manifest), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "markdown_output": args.markdown_output,
                "status": manifest["status"],
                "release_claimed_go": manifest["release_claimed_go"],
                "packet_handoff_source_commit": manifest["packet_handoff_source_commit"],
            },
            sort_keys=True,
        )
    )
    if args.expected_status:
        return 0 if manifest["status"] == args.expected_status else 1
    return 0 if manifest["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
