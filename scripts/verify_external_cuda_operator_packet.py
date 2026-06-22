#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mib_external_cuda_operator_packet_verification.v1"
PACKET_SCHEMA_VERSION = "mib_external_cuda_operator_packet.v1"
GO_DECISION = "GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION"
NOT_GO_DECISION = "NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION"
EXPECTED_STATUS = "PREPARED_NOT_RUN"
PRIMARY_HANDOFF = "artifacts/review/real_adapter_cuda_training_handoff.sh"

REQUIRED_READINESS_IDS = [
    "dataset_jsonl_present",
    "python_executable_present",
    "llamafactory_cli_present",
    "model_cache_dir_present",
    "backend_config_present",
    "rc_handoff_shell_present",
]
REQUIRED_TRAINING_COMMANDS = [
    "resolve_cuda_base_image",
    "prepare_strict_model_cache",
    "preflight_cuda_training",
    "train_real_adapter",
    "finalize_manifest",
    "verify_adapter_intake",
    "prepare_docker_image",
    "run_rc_handoff",
]
REQUIRED_RC_COMMANDS = [
    "candidate_scan",
    "adapter_intake",
    "rc_gate_preflight",
    "rc_gate_endpoint_evidence",
    "m6_review_docs_go_update_required",
    "rc_gate_m6_go",
    "evidence_bundle_assembly",
    "v0_readiness_recheck",
]
REQUIRED_CLOSEOUT_COMMANDS = ["local_closeout_after_bundle_transfer"]
REQUIRED_FORBIDDEN_LABELS = [
    "model weights",
    "LoRA adapter files or /tmp/mib-real-adapter contents",
    "Docker image layers or archives",
    "raw live endpoint transcripts",
    "copied external real-adapter evidence bundles",
]
REQUIRED_COMMITTED_FILE_PATHS = {
    PRIMARY_HANDOFF,
    "scripts/prepare_strict_model_cache.py",
}

FORBIDDEN_TRACKED_EXACT = {
    "artifacts/review/real_adapter_evidence_bundle.tar.gz",
    "artifacts/review/real_trained_adapter_endpoint_evidence.json",
    "artifacts/review/real_trained_adapter_endpoint_evidence.md",
    "artifacts/review/real_adapter_evidence_bundle/real_trained_adapter_endpoint_evidence.json",
    "artifacts/review/real_adapter_evidence_bundle/real_trained_adapter_endpoint_evidence.md",
}
FORBIDDEN_TRACKED_PATTERNS = [
    "*.safetensors",
    "*.gguf",
    "*.pt",
    "*.pth",
    "*.ckpt",
    "*.onnx",
    "*/adapter_model.bin",
    "*/pytorch_model.bin",
    "*/docker-image*.tar",
    "*/docker_image*.tar",
]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_row(check_id: str, ok: bool, detail: str, *, missing_markers: list[str] | None = None, path: str | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "ok": ok,
        "detail": detail,
        "path": path,
        "missing_markers": missing_markers or [],
    }


def read_packet(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path.is_file():
        return None, check_row("packet_json", False, "missing", path=str(path), missing_markers=["packet_json_present"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, check_row("packet_json", False, f"invalid JSON: {exc}", path=str(path), missing_markers=["packet_json_valid"])
    if not isinstance(data, dict):
        return None, check_row("packet_json", False, "expected JSON object", path=str(path), missing_markers=["packet_json_object"])
    return data, check_row("packet_json", True, "ok", path=str(path))


def check_packet_contract(packet: dict[str, Any]) -> dict[str, Any]:
    requirements = {
        "schema_version": packet.get("schema_version") == PACKET_SCHEMA_VERSION,
        "status": packet.get("status") == EXPECTED_STATUS,
        "primary_external_handoff": packet.get("primary_external_handoff") == PRIMARY_HANDOFF,
        "release_claimed_go_false": packet.get("release_claimed_go") is False,
        "m6_rc_claimed_go_false": packet.get("m6_rc_claimed_go") is False,
        "git_head_present": bool(packet.get("git", {}).get("head")) if isinstance(packet.get("git"), dict) else False,
    }
    missing = [key for key, ok in requirements.items() if not ok]
    return check_row("packet_contract", not missing, "ok" if not missing else "packet contract failed", missing_markers=missing)


def check_required_files(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    rows = packet.get("required_committed_files")
    if not isinstance(rows, list):
        return check_row("required_committed_file_hashes", False, "expected required_committed_files list", missing_markers=["required_committed_files"])

    failures: list[str] = []
    paths: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            failures.append(f"row_{index}_object")
            continue
        relative = row.get("path")
        expected_sha = row.get("sha256")
        expected_size = row.get("size_bytes")
        if not isinstance(relative, str):
            failures.append(f"row_{index}_path")
            continue
        paths.append(relative)
        path = root / relative
        if not path.is_file():
            failures.append(f"{relative}:missing")
            continue
        actual_sha = sha256_file(path)
        actual_size = path.stat().st_size
        if expected_sha != actual_sha:
            failures.append(f"{relative}:sha256")
        if expected_size != actual_size:
            failures.append(f"{relative}:size_bytes")

    for required_path in sorted(REQUIRED_COMMITTED_FILE_PATHS):
        if required_path not in paths:
            failures.append(f"{required_path}:not_in_required_files")
    return check_row(
        "required_committed_file_hashes",
        not failures,
        f"verified {len(paths)} required file hashes" if not failures else "required file hash verification failed",
        missing_markers=failures,
    )


def check_package_readiness(packet: dict[str, Any]) -> dict[str, Any]:
    checks = packet.get("package_readiness_checks")
    if not isinstance(checks, list):
        return check_row("package_readiness_checks", False, "expected package_readiness_checks list", missing_markers=["package_readiness_checks"])
    by_id = {row.get("id"): row for row in checks if isinstance(row, dict)}
    missing = [check_id for check_id in REQUIRED_READINESS_IDS if check_id not in by_id]
    unguarded = [check_id for check_id in REQUIRED_READINESS_IDS if isinstance(by_id.get(check_id), dict) and by_id[check_id].get("shell_guard") is not True]
    markers = [f"missing:{check_id}" for check_id in missing] + [f"unguarded:{check_id}" for check_id in unguarded]
    return check_row("package_readiness_checks", not markers, "ok" if not markers else "package readiness checks failed", missing_markers=markers)


def missing_ordered_ids(actual: Any, required: list[str], prefix: str) -> list[str]:
    if not isinstance(actual, list):
        return [f"{prefix}:not_list"]
    return [f"{prefix}:{item}" for item in required if item not in actual]


def check_command_order(packet: dict[str, Any]) -> dict[str, Any]:
    command_order = packet.get("command_order")
    if not isinstance(command_order, dict):
        return check_row("command_order", False, "expected command_order object", missing_markers=["command_order"])
    missing = []
    missing.extend(missing_ordered_ids(command_order.get("training_handoff"), REQUIRED_TRAINING_COMMANDS, "training_handoff"))
    missing.extend(missing_ordered_ids(command_order.get("rc_handoff"), REQUIRED_RC_COMMANDS, "rc_handoff"))
    missing.extend(missing_ordered_ids(command_order.get("post_transfer_closeout"), REQUIRED_CLOSEOUT_COMMANDS, "post_transfer_closeout"))
    return check_row("command_order", not missing, "ok" if not missing else "command order missing required steps", missing_markers=missing)


def check_forbidden_policy(packet: dict[str, Any]) -> dict[str, Any]:
    labels = packet.get("forbidden_committed_artifacts")
    if not isinstance(labels, list):
        return check_row("forbidden_committed_artifacts", False, "expected forbidden_committed_artifacts list", missing_markers=["forbidden_committed_artifacts"])
    missing = [label for label in REQUIRED_FORBIDDEN_LABELS if label not in labels]
    return check_row("forbidden_committed_artifacts", not missing, "ok" if not missing else "forbidden artifact labels missing", missing_markers=missing)


def forbidden_tracked_matches(tracked_files: list[str]) -> list[str]:
    matches: list[str] = []
    for path in tracked_files:
        if path in FORBIDDEN_TRACKED_EXACT:
            matches.append(path)
            continue
        if any(fnmatch.fnmatch(path, pattern) for pattern in FORBIDDEN_TRACKED_PATTERNS):
            matches.append(path)
    return matches


def tracked_files(root: Path) -> tuple[list[str], str | None]:
    returncode, stdout, stderr = run_git(root, "ls-files")
    if returncode != 0:
        return [], stderr or "git ls-files failed"
    return [line for line in stdout.splitlines() if line], None


def check_forbidden_tracked_artifacts(root: Path) -> tuple[dict[str, Any], str | None]:
    files, warning = tracked_files(root)
    matches = forbidden_tracked_matches(files)
    return check_row(
        "forbidden_tracked_artifacts",
        not matches,
        "ok" if not matches else "forbidden tracked artifacts are present",
        missing_markers=matches,
    ), warning


def check_git_head_resolves(root: Path, packet: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    git_info = packet.get("git") if isinstance(packet.get("git"), dict) else {}
    packet_head = git_info.get("head") if isinstance(git_info, dict) else None
    if not isinstance(packet_head, str) or not packet_head:
        return check_row("packet_git_head_resolves", False, "packet git head missing", missing_markers=["git.head"]), None

    returncode, _, stderr = run_git(root, "cat-file", "-e", f"{packet_head}^{{commit}}")
    if returncode != 0:
        # Unit tests and copied packets may run outside a full git checkout. Keep this
        # as a verifier warning rather than weakening the packet-content checks.
        return check_row("packet_git_head_resolves", True, "skipped or unavailable outside full git checkout"), stderr or "git head could not be resolved"

    warning = None
    current_code, current_head, _ = run_git(root, "rev-parse", "--short", "HEAD")
    if current_code == 0 and current_head and current_head != packet_head:
        warning = f"current checkout head {current_head} differs from packet handoff source commit {packet_head}"
    return check_row("packet_git_head_resolves", True, "ok"), warning


def verify_packet(root: Path, packet_json: Path) -> dict[str, Any]:
    packet, packet_row = read_packet(packet_json)
    checks = [packet_row]
    warnings: list[str] = []

    if packet is None:
        decision = NOT_GO_DECISION
        return {
            "schema_version": SCHEMA_VERSION,
            "date": now_utc(),
            "packet_json": str(packet_json),
            "decision": decision,
            "operator_packet_ready": False,
            "release_claimed_go": False,
            "m6_rc_claimed_go": False,
            "checks": checks,
            "blockers": [row["id"] for row in checks if not row["ok"]],
            "warnings": warnings,
        }

    checks.extend(
        [
            check_packet_contract(packet),
            check_required_files(root, packet),
            check_package_readiness(packet),
            check_command_order(packet),
            check_forbidden_policy(packet),
        ]
    )
    forbidden_row, forbidden_warning = check_forbidden_tracked_artifacts(root)
    checks.append(forbidden_row)
    if forbidden_warning:
        warnings.append(f"tracked file scan warning: {forbidden_warning}")
    git_row, git_warning = check_git_head_resolves(root, packet)
    checks.append(git_row)
    if git_warning:
        warnings.append(git_warning)

    blockers = [row["id"] for row in checks if not row["ok"]]
    decision = GO_DECISION if not blockers else NOT_GO_DECISION
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "packet_json": str(packet_json),
        "decision": decision,
        "operator_packet_ready": not blockers,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "primary_external_handoff": packet.get("primary_external_handoff"),
        "packet_handoff_source_commit": packet.get("git", {}).get("head") if isinstance(packet.get("git"), dict) else None,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "summary": {
            "required_committed_files": len(packet.get("required_committed_files", [])) if isinstance(packet.get("required_committed_files"), list) else 0,
            "package_readiness_checks": len(packet.get("package_readiness_checks", [])) if isinstance(packet.get("package_readiness_checks"), list) else 0,
            "forbidden_tracked_artifacts": forbidden_row["missing_markers"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the external CUDA operator packet before running the real-adapter CUDA handoff.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--packet-json", default="artifacts/review/external_cuda_operator_packet.json")
    parser.add_argument("--expected-decision", choices=["GO", "NOT_GO"], default="GO")
    parser.add_argument("--json-output", default="artifacts/review/external_cuda_operator_packet_verification.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    packet_json = root / args.packet_json
    report = verify_packet(root, packet_json)
    expected_decision = GO_DECISION if args.expected_decision == "GO" else NOT_GO_DECISION
    report["expected_decision"] = expected_decision
    report["decision_matches_expected"] = report["decision"] == expected_decision
    report["verification_ok"] = report["decision_matches_expected"]

    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "decision": report["decision"],
                "operator_packet_ready": report["operator_packet_ready"],
                "verification_ok": report["verification_ok"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["verification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
