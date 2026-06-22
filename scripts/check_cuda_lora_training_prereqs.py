#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from resolve_cuda_base_image import cuda_markers, python_runtime_markers
from services.shared.model_catalog import load_model_catalog


SCHEMA_VERSION = "mib_cuda_lora_training_prereq_preflight.v1"
READY_STATUS = "READY_FOR_CUDA_LORA_TRAINING"
NOT_READY_STATUS = "NOT_READY_CUDA_LORA_TRAINING"
BASE_IMAGE_ENV = "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST"
FAKE_BACKEND_ENV = "MIB_RUNTIME_ALLOW_FAKE_BACKEND"
DIGEST_REF_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_subprocess(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def clip(value: str, *, limit: int = 1000) -> str:
    return value if len(value) <= limit else value[-limit:]


def check_row(check_id: str, ok: bool, detail: str, **extra: Any) -> dict[str, Any]:
    row = {"id": check_id, "ok": ok, "detail": detail}
    row.update(extra)
    return row


def command_check(check_id: str, command: list[str], *, timeout: int, runner: Runner) -> dict[str, Any]:
    try:
        result = runner(command, timeout)
    except Exception as exc:
        return check_row(check_id, False, str(exc), command=command, returncode=None)
    detail = "ok" if result.returncode == 0 else clip((result.stderr or result.stdout or "").strip())
    return check_row(check_id, result.returncode == 0, detail, command=command, returncode=result.returncode)


def docker_base_image_checks(base_image: str, *, timeout: int, runner: Runner) -> list[dict[str, Any]]:
    command = ["docker", "image", "inspect", base_image]
    if not base_image:
        return [
            check_row(
                "docker_base_image_available",
                False,
                f"cannot inspect base image until {BASE_IMAGE_ENV} is set",
                command=["docker", "image", "inspect", f"${BASE_IMAGE_ENV}"],
                returncode=None,
            )
        ]
    try:
        result = runner(command, timeout)
    except Exception as exc:
        return [check_row("docker_base_image_available", False, str(exc), command=command, returncode=None)]
    if result.returncode != 0:
        detail = clip((result.stderr or result.stdout or "").strip())
        return [check_row("docker_base_image_available", False, detail, command=command, returncode=result.returncode)]
    available = check_row("docker_base_image_available", True, "ok", command=command, returncode=result.returncode)
    try:
        inspected = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [
            available,
            check_row(
                "docker_base_image_cuda_python_runtime",
                False,
                f"docker image inspect returned invalid JSON: {exc}",
                command=command,
                cuda_markers=[],
                python_runtime_markers=[],
            ),
        ]
    if not isinstance(inspected, list) or not inspected or not isinstance(inspected[0], dict):
        return [
            available,
            check_row(
                "docker_base_image_cuda_python_runtime",
                False,
                "docker image inspect returned no image object",
                command=command,
                cuda_markers=[],
                python_runtime_markers=[],
            ),
        ]
    image = inspected[0]
    cuda = cuda_markers(base_image, base_image, image)
    python_runtime = python_runtime_markers(base_image, base_image, image)
    ok = bool(cuda) and bool(python_runtime)
    missing: list[str] = []
    if not cuda:
        missing.append("cuda_markers")
    if not python_runtime:
        missing.append("python_runtime_markers")
    detail = "ok" if ok else "base image is inspectable but missing " + ", ".join(missing)
    return [
        available,
        check_row(
            "docker_base_image_cuda_python_runtime",
            ok,
            detail,
            command=command,
            cuda_markers=cuda,
            python_runtime_markers=python_runtime,
        ),
    ]


def llamafactory_cli_check(command_path: str, *, timeout: int, runner: Runner) -> dict[str, Any]:
    command = [command_path, "version"]
    try:
        result = runner(command, timeout)
    except Exception as exc:
        return check_row("llamafactory_cli_available", False, str(exc), command=command, returncode=None)
    output = (result.stdout or result.stderr or "").strip()
    ok = result.returncode == 0 and "LLaMA Factory" in output
    detail = "ok" if ok else clip(output)
    return check_row("llamafactory_cli_available", ok, detail, command=command, returncode=result.returncode)


def digest_reference(value: str | None) -> bool:
    return bool(value and DIGEST_REF_RE.fullmatch(value))


def dataset_check(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return check_row("dataset_jsonl_ready", False, f"missing dataset JSONL: {path}", path=str(path), row_count=0)
    row_count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            return check_row(
                "dataset_jsonl_ready",
                False,
                f"invalid JSONL row {line_number}: {exc}",
                path=str(path),
                row_count=row_count,
            )
        if not isinstance(row, dict):
            return check_row("dataset_jsonl_ready", False, f"row {line_number} is not a JSON object", path=str(path), row_count=row_count)
        row_count += 1
    return check_row("dataset_jsonl_ready", row_count > 0, "ok" if row_count > 0 else "dataset JSONL has no rows", path=str(path), row_count=row_count)


def backend_config_check(path: Path, *, model_cache_dir: str, output_root: str) -> dict[str, Any]:
    if not path.is_file():
        return check_row("backend_config_ready", False, f"missing backend_config.yaml: {path}", path=str(path))
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return check_row("backend_config_ready", False, f"invalid backend_config.yaml: {exc}", path=str(path))
    if not isinstance(config, dict):
        return check_row("backend_config_ready", False, "backend_config.yaml must be a mapping", path=str(path))
    expected_output = str(Path(output_root) / "adapter")
    mismatches = []
    if config.get("model_name_or_path") != model_cache_dir:
        mismatches.append("model_name_or_path")
    if config.get("output_dir") != expected_output:
        mismatches.append("output_dir")
    if config.get("do_train") is not True:
        mismatches.append("do_train")
    if config.get("finetuning_type") != "lora":
        mismatches.append("finetuning_type")
    return check_row(
        "backend_config_ready",
        not mismatches,
        "ok" if not mismatches else "backend_config.yaml mismatch: " + ", ".join(mismatches),
        path=str(path),
        mismatches=mismatches,
    )


def strict_model_cache_check(*, base_model: str, model_cache_dir: Path, verify_hashes: bool) -> dict[str, Any]:
    model = load_model_catalog().get(base_model)
    root = model_cache_dir / model.cache_subdir
    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[str] = []
    for item in model.required_files:
        candidate = root / item.path
        if not candidate.is_file():
            missing.append(item.path)
            continue
        size = candidate.stat().st_size
        if size != item.size_bytes:
            size_mismatches.append({"path": item.path, "expected_size_bytes": item.size_bytes, "actual_size_bytes": size})
            continue
        if verify_hashes and sha256_file(candidate) != item.sha256:
            hash_mismatches.append(item.path)
    ok = not missing and not size_mismatches and not hash_mismatches
    detail = "ok" if ok else "strict model cache files are missing or do not match the locked catalog"
    return check_row(
        "strict_model_cache_files",
        ok,
        detail,
        model_id=model.id,
        cache_dir=str(root),
        required_count=len(model.required_files),
        verify_hashes=verify_hashes,
        missing=missing,
        size_mismatches=size_mismatches,
        hash_mismatches=hash_mismatches,
    )


def build_report(args: argparse.Namespace, *, runner: Runner = run_subprocess, env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env if env is not None else dict(os.environ)
    base_image = env.get(BASE_IMAGE_ENV, "")
    checks = [
        check_row(
            "fake_backend_env_absent",
            not env.get(FAKE_BACKEND_ENV),
            f"{FAKE_BACKEND_ENV} must be unset",
        ),
        check_row(
            "docker_base_image_env_digest",
            digest_reference(base_image),
            f"{BASE_IMAGE_ENV} must be set to an image reference with @sha256:<64-hex>",
            env_var=BASE_IMAGE_ENV,
            value_present=bool(base_image),
        ),
        dataset_check(Path(args.dataset_jsonl)),
        backend_config_check(Path(args.backend_config), model_cache_dir=args.model_cache_dir, output_root=args.output_root),
        strict_model_cache_check(base_model=args.base_model, model_cache_dir=Path(args.model_cache_dir), verify_hashes=args.verify_model_cache_hashes),
        command_check("cuda_visible", ["nvidia-smi"], timeout=30, runner=runner),
        llamafactory_cli_check(args.llamafactory_cli, timeout=30, runner=runner),
        command_check("docker_daemon_available", ["docker", "version", "--format", "{{.Server.Version}}"], timeout=30, runner=runner),
    ]
    checks.extend(docker_base_image_checks(base_image, timeout=30, runner=runner))
    blockers = [row["id"] for row in checks if not row["ok"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-cuda-training-host-preflight",
        "status": READY_STATUS if not blockers else NOT_READY_STATUS,
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "inputs": {
            "dataset_jsonl": args.dataset_jsonl,
            "base_model": args.base_model,
            "model_cache_dir": args.model_cache_dir,
            "output_root": args.output_root,
            "backend_config": args.backend_config,
            "image": args.image,
            "llamafactory_cli": args.llamafactory_cli,
            "verify_model_cache_hashes": args.verify_model_cache_hashes,
        },
        "env_requirements": {
            "fake_backend_env": FAKE_BACKEND_ENV,
            "docker_base_image_env": BASE_IMAGE_ENV,
            "docker_base_image_digest_present": digest_reference(base_image),
        },
        "checks": checks,
        "blockers": blockers,
        "operator_rules": [
            f"Do not set {FAKE_BACKEND_ENV}.",
            f"Set {BASE_IMAGE_ENV} to a locally inspectable CUDA/Python runtime image reference containing @sha256 before training.",
            "Run on a host where nvidia-smi succeeds before launching llamafactory-cli train.",
            "Keep strict model cache files pinned to presets/model_catalog.yaml.",
            "Do not claim M6-RC or v0 GO from this preflight alone.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check prerequisites before running the external CUDA LLaMA-Factory LoRA training handoff.")
    parser.add_argument("--dataset-jsonl", required=True)
    parser.add_argument("--base-model", choices=["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"], required=True)
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--backend-config", required=True)
    parser.add_argument("--image", default="mib-export:test")
    parser.add_argument("--llamafactory-cli", default="./.venv/bin/llamafactory-cli")
    parser.add_argument("--verify-model-cache-hashes", action="store_true")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_cuda_training_prereq_preflight.json")
    parser.add_argument("--expected-status", choices=[READY_STATUS, NOT_READY_STATUS])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_json(args.json_output, report)
    print(json.dumps({"json_output": args.json_output, "status": report["status"], "blockers": report["blockers"]}, sort_keys=True))
    if args.expected_status:
        return 0 if report["status"] == args.expected_status else 1
    return 0 if report["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
