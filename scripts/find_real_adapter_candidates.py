#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_real_adapter_artifact import LOCKED_BASE_MODELS, verify_adapter


SCHEMA_VERSION = "mib_real_adapter_candidate_scan.v1"
DEFAULT_GATE_OUTPUT = "artifacts/review/m6_real_adapter_rc_gate_run.json"
DEFAULT_INTAKE_OUTPUT = "artifacts/review/real_adapter_artifact_intake.json"
DEFAULT_ENDPOINT_OUTPUT = "artifacts/review/real_trained_adapter_endpoint_evidence.md"
DEFAULT_ENDPOINT_JSON_OUTPUT = "artifacts/review/real_trained_adapter_endpoint_evidence.json"
DEFAULT_M6_OUTPUT = "artifacts/review/m6_rc_evidence_verification.json"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def candidate_dirs(root: Path) -> tuple[list[Path], list[dict[str, str]]]:
    found: set[Path] = set()
    errors: list[dict[str, str]] = []
    if not root.exists():
        errors.append({"root": str(root), "error": "root does not exist"})
        return [], errors

    def onerror(exc: OSError) -> None:
        errors.append({"root": str(root), "error": str(exc)})

    for current, dirnames, filenames in os.walk(root, onerror=onerror):
        if "adapter.safetensors" in filenames and "adapter_config.json" in filenames:
            found.add(Path(current))
        ignored = {".git", ".venv", "__pycache__", "node_modules"}
        dirnames[:] = [name for name in dirnames if name not in ignored]
    return sorted(found), errors


def manifest_candidates(adapter_dir: Path) -> list[Path]:
    paths = [
        adapter_dir.parent / "manifest.json",
        adapter_dir / "manifest.json",
    ]
    unique: list[Path] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    return unique


def best_manifest(adapter_dir: Path) -> Path | None:
    for path in manifest_candidates(adapter_dir):
        if path.is_file():
            return path
    return None


def rc_gate_command(args: argparse.Namespace, *, adapter_dir: Path, manifest_path: Path) -> list[str]:
    return [
        sys.executable,
        "scripts/run_m6_real_adapter_rc_gate.py",
        "--adapter-dir",
        str(adapter_dir),
        "--adapter-manifest",
        str(manifest_path),
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


def evaluate_candidate(args: argparse.Namespace, adapter_dir: Path) -> dict[str, Any]:
    manifest_path = best_manifest(adapter_dir)
    report = verify_adapter(
        adapter_dir=adapter_dir,
        expected_base_model=args.base_model,
        manifest_path=manifest_path,
    )
    row: dict[str, Any] = {
        "adapter_dir": str(adapter_dir),
        "manifest_path": str(manifest_path) if manifest_path else None,
        "status": report["status"],
        "go": report["status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE",
        "adapter_sha256": report.get("adapter_sha256"),
        "artifact_manifest_sha256": report.get("artifact_manifest_sha256"),
        "errors": report.get("errors", []),
        "safetensors": report.get("safetensors", {}),
        "config": report.get("config", {}),
    }
    if row["go"] and manifest_path is not None:
        row["rc_gate_command"] = rc_gate_command(args, adapter_dir=adapter_dir, manifest_path=manifest_path)
    return row


def scan(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(root).resolve() for root in args.root]
    candidates: list[dict[str, Any]] = []
    scan_errors: list[dict[str, str]] = []
    seen: set[Path] = set()
    for root in roots:
        dirs, errors = candidate_dirs(root)
        scan_errors.extend(errors)
        for adapter_dir in dirs:
            resolved = adapter_dir.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(evaluate_candidate(args, resolved))

    go_candidates = [row for row in candidates if row["go"]]
    fixture_like_candidates = [
        row
        for row in candidates
        if any("fixture-sized" in str(error) for error in row.get("errors", []))
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "roots": [str(root) for root in roots],
        "base_model": args.base_model,
        "image": args.image,
        "agent_id": args.agent_id,
        "model_cache_dir": args.model_cache_dir,
        "candidate_count": len(candidates),
        "go_candidate_count": len(go_candidates),
        "fixture_like_candidate_count": len(fixture_like_candidates),
        "scan_errors": scan_errors,
        "candidates": candidates,
        "decision": "GO_CANDIDATES_FOUND" if go_candidates else "NO_GO_CANDIDATES_FOUND",
        "m6_rc_claimed_go": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Find real adapter candidates and emit M6-RC runner commands.")
    parser.add_argument("--root", action="append", required=True, help="Root directory to scan. Repeat for multiple roots.")
    parser.add_argument("--base-model", choices=sorted(LOCKED_BASE_MODELS), required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--expected-go-candidates", type=int)
    parser.add_argument("--adapter-intake-json-output", default=DEFAULT_INTAKE_OUTPUT)
    parser.add_argument("--endpoint-output", default=DEFAULT_ENDPOINT_OUTPUT)
    parser.add_argument("--endpoint-json-output", default=DEFAULT_ENDPOINT_JSON_OUTPUT)
    parser.add_argument("--m6-json-output", default=DEFAULT_M6_OUTPUT)
    parser.add_argument("--gate-json-output", default=DEFAULT_GATE_OUTPUT)
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_candidate_scan.json")
    args = parser.parse_args()

    report = scan(args)
    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"json_output": args.json_output, "decision": report["decision"], "go_candidate_count": report["go_candidate_count"]}, sort_keys=True))
    if args.expected_go_candidates is not None and report["go_candidate_count"] != args.expected_go_candidates:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
