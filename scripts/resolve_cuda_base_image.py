#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "mib_cuda_base_image_resolution.v1"
READY_STATUS = "CUDA_BASE_IMAGE_RESOLVED"
NOT_READY_STATUS = "NOT_READY_CUDA_BASE_IMAGE"
BASE_IMAGE_ENV = "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST"
DEFAULT_CANDIDATES = ("pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime",)
DIGEST_REF_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_text(path: str | Path, value: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def run_subprocess(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def clip(value: str, *, limit: int = 1000) -> str:
    return value if len(value) <= limit else value[-limit:]


def repo_without_tag(ref: str) -> str:
    ref = ref.split("@", 1)[0]
    last_slash = ref.rfind("/")
    last_colon = ref.rfind(":")
    if last_colon > last_slash:
        return ref[:last_colon]
    return ref


def normalized_repo(ref: str) -> str:
    repo = repo_without_tag(ref)
    for prefix in ("docker.io/", "index.docker.io/"):
        if repo.startswith(prefix):
            repo = repo[len(prefix) :]
    if repo.startswith("library/"):
        repo = repo[len("library/") :]
    return repo


def select_digest_reference(candidate: str, repo_digests: list[str]) -> str | None:
    if DIGEST_REF_RE.fullmatch(candidate):
        return candidate
    candidate_repo = normalized_repo(candidate)
    for digest in repo_digests:
        if DIGEST_REF_RE.fullmatch(digest) and normalized_repo(digest) == candidate_repo:
            return digest
    for digest in repo_digests:
        if DIGEST_REF_RE.fullmatch(digest):
            return digest
    return None


def env_values(inspect_row: dict[str, Any]) -> list[str]:
    config = inspect_row.get("Config") or {}
    env = config.get("Env") or []
    return [item for item in env if isinstance(item, str)]


def label_values(inspect_row: dict[str, Any]) -> dict[str, str]:
    config = inspect_row.get("Config") or {}
    labels = config.get("Labels") or {}
    return {str(key): str(value) for key, value in labels.items()}


def cuda_markers(candidate: str, digest_reference: str, inspect_row: dict[str, Any]) -> list[str]:
    markers: list[str] = []
    refs = " ".join([candidate, digest_reference]).lower()
    if "cuda" in refs:
        markers.append("reference_contains_cuda")
    if "pytorch/pytorch" in refs and "cuda" in refs:
        markers.append("reference_is_pytorch_cuda")
    for item in env_values(inspect_row):
        key = item.split("=", 1)[0]
        value = item.lower()
        if key in {
            "CUDA_VERSION",
            "NVIDIA_REQUIRE_CUDA",
            "NVIDIA_VISIBLE_DEVICES",
            "NVIDIA_DRIVER_CAPABILITIES",
            "NV_CUDA_LIB_VERSION",
        }:
            markers.append(f"env:{key}")
        elif "cuda" in value:
            markers.append(f"env:{key}")
    for key, value in label_values(inspect_row).items():
        if "cuda" in key.lower() or "cuda" in value.lower():
            markers.append(f"label:{key}")
    return sorted(set(markers))


def python_runtime_markers(candidate: str, digest_reference: str, inspect_row: dict[str, Any]) -> list[str]:
    markers: list[str] = []
    refs = " ".join([candidate, digest_reference]).lower()
    if "pytorch/pytorch" in refs:
        markers.append("reference_is_pytorch_runtime")
    for item in env_values(inspect_row):
        key = item.split("=", 1)[0]
        if key in {"PYTHON_VERSION", "PYTHON_PIP_VERSION", "CONDA_PYTHON_EXE"}:
            markers.append(f"env:{key}")
    return sorted(set(markers))


def inspect_candidate(candidate: str, *, runner: Runner, timeout: int) -> dict[str, Any]:
    command = ["docker", "image", "inspect", candidate]
    try:
        result = runner(command, timeout)
    except Exception as exc:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "inspect_failed",
            "detail": str(exc),
            "returncode": None,
        }
    if result.returncode != 0:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "inspect_failed",
            "detail": clip((result.stderr or result.stdout or "").strip()),
            "returncode": result.returncode,
        }
    try:
        inspected = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "inspect_json_invalid",
            "detail": str(exc),
            "returncode": result.returncode,
        }
    if not isinstance(inspected, list) or not inspected or not isinstance(inspected[0], dict):
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "inspect_json_empty",
            "detail": "docker image inspect returned no image object",
            "returncode": result.returncode,
        }
    image = inspected[0]
    repo_digests = [item for item in image.get("RepoDigests") or [] if isinstance(item, str)]
    repo_tags = [item for item in image.get("RepoTags") or [] if isinstance(item, str)]
    digest_reference = select_digest_reference(candidate, repo_digests)
    if not digest_reference:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "no_digest_reference",
            "detail": "image is locally inspectable but has no usable sha256 RepoDigest",
            "returncode": result.returncode,
            "repo_digests": repo_digests,
            "repo_tags": repo_tags,
            "image_id": image.get("Id"),
        }
    cuda = cuda_markers(candidate, digest_reference, image)
    python_markers = python_runtime_markers(candidate, digest_reference, image)
    if not cuda:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "cuda_markers_missing",
            "detail": "image has a digest but does not look like a CUDA runtime base image",
            "returncode": result.returncode,
            "repo_digests": repo_digests,
            "repo_tags": repo_tags,
            "digest_reference": digest_reference,
            "image_id": image.get("Id"),
            "cuda_markers": cuda,
            "python_runtime_markers": python_markers,
        }
    if not python_markers:
        return {
            "candidate": candidate,
            "command": command,
            "ok": False,
            "status": "python_runtime_markers_missing",
            "detail": "image has a digest and CUDA markers but does not look like a Python runtime base image",
            "returncode": result.returncode,
            "repo_digests": repo_digests,
            "repo_tags": repo_tags,
            "digest_reference": digest_reference,
            "image_id": image.get("Id"),
            "cuda_markers": cuda,
            "python_runtime_markers": python_markers,
        }
    return {
        "candidate": candidate,
        "command": command,
        "ok": True,
        "status": "resolved",
        "detail": "ok",
        "returncode": result.returncode,
        "repo_digests": repo_digests,
        "repo_tags": repo_tags,
        "digest_reference": digest_reference,
        "image_id": image.get("Id"),
        "cuda_markers": cuda,
        "python_runtime_markers": python_markers,
        "python_runtime_likely": True,
    }


def build_report(args: argparse.Namespace, *, runner: Runner = run_subprocess) -> dict[str, Any]:
    candidates = list(args.candidate or DEFAULT_CANDIDATES)
    rows = [inspect_candidate(candidate, runner=runner, timeout=args.timeout) for candidate in candidates]
    selected = next((row for row in rows if row["ok"]), None)
    status = READY_STATUS if selected else NOT_READY_STATUS
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-cuda-base-image-resolution",
        "status": status,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "inputs": {
            "candidates": candidates,
            "timeout": args.timeout,
        },
        "env": {BASE_IMAGE_ENV: selected["digest_reference"]} if selected else {},
        "selected": selected,
        "candidates": rows,
        "blockers": [] if selected else ["cuda_base_image_not_resolved"],
        "operator_rules": [
            f"Use the emitted {BASE_IMAGE_ENV} only for Docker build handoffs that require a digest-pinned CUDA/Python base image.",
            "Do not use application images, CUDA-only images without Python, or fixture images as CUDA/Python base images.",
            "Do not claim M6-RC or v0 GO from base-image resolution alone.",
            "If no candidate resolves, pull or provide a CUDA/PyTorch runtime image on the CUDA host and rerun this resolver.",
        ],
    }


def render_env(report: dict[str, Any]) -> str:
    value = report.get("env", {}).get(BASE_IMAGE_ENV)
    if not value:
        raise ValueError("cannot render env output without a resolved CUDA base image")
    return f"export {BASE_IMAGE_ENV}={shlex.quote(value)}\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve a local CUDA/PyTorch Docker base image to a digest-pinned env var.")
    parser.add_argument("--candidate", action="append", help="Local Docker image tag or digest candidate to inspect. May be repeated.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_cuda_base_image_resolution.json")
    parser.add_argument("--env-output", default="artifacts/review/real_adapter_cuda_base_image.env")
    parser.add_argument("--expected-status", choices=[READY_STATUS, NOT_READY_STATUS])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_json(args.json_output, report)
    if report["status"] == READY_STATUS:
        write_text(args.env_output, render_env(report))
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "env_output": args.env_output if report["status"] == READY_STATUS else None,
                "status": report["status"],
                "selected": report["env"].get(BASE_IMAGE_ENV),
            },
            sort_keys=True,
        )
    )
    if args.expected_status:
        return 0 if report["status"] == args.expected_status else 1
    return 0 if report["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
