#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.worker.handlers.train_cuda import hyperparams
from services.worker.runtime.llamafactory import TrainerJobInput, trainer_input_to_dict, write_llamafactory_artifacts, write_manifest
from verify_real_adapter_artifact import verify_adapter


LOCKED_BASE_MODELS = {"google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"}
DEFAULT_CUDA_BASE_IMAGE_CANDIDATE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
DOCKER_BASE_IMAGE_ENV = "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: str | Path, value: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def build_trainer_input(args: argparse.Namespace) -> TrainerJobInput:
    dataset_path = Path(args.dataset_jsonl)
    selected_hyperparams = hyperparams(args.training_preset, args.hardware_profile_id)
    return TrainerJobInput(
        job_id=args.job_id,
        project_id=args.project_id,
        model_run_id=args.model_run_id,
        dataset_path=str(dataset_path),
        dataset_sha256=sha256_file(dataset_path),
        base_model=args.base_model,
        backend="cuda",
        method="qlora",
        output_dir=args.output_root,
        seed=args.seed,
        max_seq_length=args.max_seq_length,
        hyperparams=selected_hyperparams,
    )


def command_row(command_id: str, argv: list[str], *, note: str) -> dict[str, Any]:
    return {"id": command_id, "argv": argv, "shell": shlex.join(argv), "note": note}


def cuda_base_image_candidates(args: argparse.Namespace) -> list[str]:
    return list(args.cuda_base_image_candidate or [DEFAULT_CUDA_BASE_IMAGE_CANDIDATE])


def cuda_base_image_resolver_command(args: argparse.Namespace) -> list[str]:
    command = [
        args.python,
        "scripts/resolve_cuda_base_image.py",
        "--json-output",
        args.cuda_base_image_json_output,
        "--env-output",
        args.cuda_base_image_env_output,
        "--expected-status",
        "CUDA_BASE_IMAGE_RESOLVED",
    ]
    for candidate in cuda_base_image_candidates(args):
        command.extend(["--candidate", candidate])
    return command


def package_readiness_checks(args: argparse.Namespace, backend_config_path: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": "dataset_jsonl_present",
            "path": args.dataset_jsonl,
            "required_before_run": True,
            "shell_guard": True,
            "description": "Training dataset JSONL exists on the CUDA host.",
        },
        {
            "id": "python_executable_present",
            "path": args.python,
            "required_before_run": True,
            "shell_guard": True,
            "description": "Repo virtualenv Python exists and is executable.",
        },
        {
            "id": "llamafactory_cli_present",
            "path": args.llamafactory_cli,
            "required_before_run": True,
            "shell_guard": True,
            "description": "LLaMA-Factory CLI exists and is executable.",
        },
        {
            "id": "model_cache_dir_present",
            "path": args.model_cache_dir,
            "required_before_run": True,
            "shell_guard": True,
            "description": "Strict base-model cache directory is present on the CUDA host.",
        },
        {
            "id": "backend_config_present",
            "path": str(backend_config_path),
            "required_before_run": True,
            "shell_guard": True,
            "description": "Generated LLaMA-Factory backend_config.yaml is present under the adapter output root.",
        },
        {
            "id": "rc_handoff_shell_present",
            "path": args.rc_handoff_shell,
            "required_before_run": True,
            "shell_guard": True,
            "description": "Downstream real-adapter RC handoff shell is present before endpoint evidence capture.",
        },
    ]


def build_prepare_report(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    trainer_input = build_trainer_input(args)
    config_path = write_llamafactory_artifacts(trainer_input, model_cache_path=Path(args.model_cache_dir), dataset_id=args.dataset_id)
    backend_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    resolver_command = cuda_base_image_resolver_command(args)
    model_cache_command = [
        args.python,
        "scripts/prepare_strict_model_cache.py",
        "--base-model",
        args.base_model,
        "--backend",
        "cuda",
        "--model-cache-dir",
        args.model_cache_dir,
        "--allow-download",
        "--expected-status",
        "READY_STRICT_MODEL_CACHE",
        "--json-output",
        args.model_cache_json_output,
    ]
    preflight_command = [
        args.python,
        "scripts/check_cuda_lora_training_prereqs.py",
        "--dataset-jsonl",
        args.dataset_jsonl,
        "--base-model",
        args.base_model,
        "--model-cache-dir",
        args.model_cache_dir,
        "--output-root",
        args.output_root,
        "--backend-config",
        str(config_path),
        "--image",
        args.image,
        "--llamafactory-cli",
        args.llamafactory_cli,
        "--verify-model-cache-hashes",
        "--json-output",
        args.preflight_json_output,
    ]
    train_command = [args.llamafactory_cli, "train", str(config_path)]
    finalize_command = [
        args.python,
        "scripts/prepare_cuda_lora_training_run.py",
        "--finalize-only",
        "--base-model",
        args.base_model,
        "--output-root",
        args.output_root,
        "--json-output",
        args.finalize_json_output,
    ]
    intake_command = [
        args.python,
        "scripts/verify_real_adapter_artifact.py",
        "--adapter-dir",
        str(output_root / "adapter"),
        "--base-model",
        args.base_model,
        "--manifest",
        str(output_root / "manifest.json"),
        "--json-output",
        args.adapter_intake_json_output,
    ]
    docker_handoff_command = [
        args.python,
        "scripts/prepare_real_adapter_docker_image.py",
        "--adapter-root",
        args.output_root,
        "--base-model",
        args.base_model,
        "--agent-id",
        args.agent_id,
        "--image",
        args.image,
        "--context-output",
        args.docker_context_output,
        "--cuda-base-image-json-output",
        args.cuda_base_image_json_output,
        "--cuda-base-image-env-output",
        args.cuda_base_image_env_output,
        "--json-output",
        args.docker_handoff_json_output,
        "--markdown-output",
        args.docker_handoff_markdown_output,
        "--shell-output",
        args.docker_handoff_shell_output,
    ]
    for candidate in cuda_base_image_candidates(args):
        docker_handoff_command.extend(["--cuda-base-image-candidate", candidate])
    run_docker_handoff_command = ["bash", args.docker_handoff_shell_output]
    handoff_command = ["bash", args.rc_handoff_shell]
    return {
        "schema_version": "mib_cuda_lora_training_handoff.v1",
        "date": now_utc(),
        "gate": "mib-studio-cuda-real-adapter-training-handoff",
        "status": "PREPARED_NOT_RUN",
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "inputs": {
            "dataset_jsonl": args.dataset_jsonl,
            "dataset_id": args.dataset_id,
            "dataset_sha256": trainer_input.dataset_sha256,
            "base_model": args.base_model,
            "model_cache_dir": args.model_cache_dir,
            "llamafactory_cli": args.llamafactory_cli,
            "cuda_base_image_candidates": cuda_base_image_candidates(args),
            "output_root": args.output_root,
            "training_preset": args.training_preset,
            "seed": args.seed,
            "max_seq_length": args.max_seq_length,
        },
        "outputs": {
            "train_config": str(output_root / "train_config.json"),
            "backend_config": str(config_path),
            "strict_model_cache_report": args.model_cache_json_output,
            "cuda_base_image_resolution_report": args.cuda_base_image_json_output,
            "cuda_base_image_env": args.cuda_base_image_env_output,
            "preflight_report": args.preflight_json_output,
            "adapter_dir": str(output_root / "adapter"),
            "manifest": str(output_root / "manifest.json"),
            "finalize_report": args.finalize_json_output,
            "adapter_intake_report": args.adapter_intake_json_output,
            "docker_context": args.docker_context_output,
            "docker_handoff_report": args.docker_handoff_json_output,
            "docker_handoff_shell": args.docker_handoff_shell_output,
            "rc_handoff_shell": args.rc_handoff_shell,
        },
        "backend_config_summary": {
            "lora_rank": backend_config.get("lora_rank"),
            "lora_alpha": backend_config.get("lora_alpha"),
            "lora_target": backend_config.get("lora_target"),
            "quantization_bit": backend_config.get("quantization_bit"),
            "template": backend_config.get("template"),
            "output_dir": backend_config.get("output_dir"),
        },
        "package_readiness_checks": package_readiness_checks(args, config_path),
        "command_sequence": [
            command_row("resolve_cuda_base_image", resolver_command, note=f"Run only when {DOCKER_BASE_IMAGE_ENV} is unset; writes a digest-pinned CUDA base image env file for downstream preflight and Docker build."),
            command_row("prepare_strict_model_cache", model_cache_command, note="Create or verify the strict pinned base-model cache before CUDA training preflight. This may download large model files only because --allow-download is explicit."),
            command_row("preflight_cuda_training", preflight_command, note="Fail fast unless CUDA, LLaMA-Factory, Docker base image, backend config, dataset, and strict model cache prerequisites are ready."),
            command_row("train_real_adapter", train_command, note="Run actual CUDA QLoRA training with LLaMA-Factory on the CUDA host."),
            command_row("finalize_manifest", finalize_command, note="Write manifest.json from the trained adapter directory."),
            command_row("verify_adapter_intake", intake_command, note="Require GO_REAL_ADAPTER_ARTIFACT_INTAKE before export/endpoint evidence."),
            command_row("prepare_docker_image", docker_handoff_command, note="Create the guarded digest-pinned Docker image handoff before RC endpoint capture."),
            command_row("run_docker_image_handoff", run_docker_handoff_command, note="Build and inspect mib-export:test with the real adapter before the RC handoff."),
            command_row("run_rc_handoff", handoff_command, note="Run the existing guarded no-fake endpoint/M6/v0 handoff after the real adapter exists."),
        ],
        "operator_rules": [
            "Run on a host with NVIDIA CUDA visible to nvidia-smi.",
            "Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.",
            "Run scripts/prepare_strict_model_cache.py before CUDA training preflight so pinned model files are present and hash-verified.",
            f"If {DOCKER_BASE_IMAGE_ENV} is unset, resolve a local CUDA/PyTorch base image with scripts/resolve_cuda_base_image.py before preflight.",
            "Do not use fixture-sized or self-test adapters as release evidence.",
            "Do not claim M6-RC or v0 GO until the downstream real adapter handoff and verifiers return GO.",
        ],
    }


def build_finalize_report(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    manifest_path, adapter_sha256, manifest_sha256 = write_manifest(output_root, trainer_backend="llamafactory")
    intake = verify_adapter(adapter_dir=output_root / "adapter", expected_base_model=args.base_model, manifest_path=manifest_path)
    return {
        "schema_version": "mib_cuda_lora_training_finalize.v1",
        "date": now_utc(),
        "gate": "mib-studio-cuda-real-adapter-training-handoff",
        "status": "GO_CUDA_LORA_TRAINING_FINALIZE" if intake["status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE" else "NOT_GO_CUDA_LORA_TRAINING_FINALIZE",
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "output_root": str(output_root),
        "manifest": str(manifest_path),
        "adapter_sha256": adapter_sha256,
        "artifact_manifest_sha256": manifest_sha256,
        "adapter_intake_status": intake["status"],
        "adapter_intake_errors": intake["errors"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    commands = "\n\n".join(f"### {row['id']}\n\n```bash\n{row['shell']}\n```" for row in report["command_sequence"])
    rules = "\n".join(f"- {item}" for item in report["operator_rules"])
    readiness = "\n".join(
        f"- `{row['id']}`: `{row['path']}` - {row['description']}"
        for row in report["package_readiness_checks"]
    )
    summary = report["backend_config_summary"]
    return f"""# CUDA LoRA Training Handoff

```yaml
date: {report["date"]}
gate: {report["gate"]}
status: {report["status"]}
release_claimed_go: false
m6_rc_claimed_go: false
```

This artifact prepares a real CUDA LLaMA-Factory QLoRA adapter run. It does not run training in the current host and does not claim M6-RC or v0 release GO.

## Inputs

```yaml
dataset_jsonl: {report["inputs"]["dataset_jsonl"]}
dataset_id: {report["inputs"]["dataset_id"]}
dataset_sha256: {report["inputs"]["dataset_sha256"]}
base_model: {report["inputs"]["base_model"]}
model_cache_dir: {report["inputs"]["model_cache_dir"]}
output_root: {report["inputs"]["output_root"]}
training_preset: {report["inputs"]["training_preset"]}
seed: {report["inputs"]["seed"]}
max_seq_length: {report["inputs"]["max_seq_length"]}
```

## Backend Config

```yaml
lora_rank: {summary["lora_rank"]}
lora_alpha: {summary["lora_alpha"]}
lora_target: {summary["lora_target"]}
quantization_bit: {summary["quantization_bit"]}
template: {summary["template"]}
output_dir: {summary["output_dir"]}
```

## Operator Rules

{rules}

## Package Readiness Checks

The generated shell refuses to run until these package prerequisites are present:

{readiness}

## Command Sequence

{commands}
"""


def render_shell(report: dict[str, Any]) -> str:
    resolver = next(row for row in report["command_sequence"] if row["id"] == "resolve_cuda_base_image")
    commands = "\n\n".join(
        f"printf '\\n== {row['id']} ==\\n'\n{row['shell']}"
        for row in report["command_sequence"]
        if row["id"] != "resolve_cuda_base_image"
    )
    output_root = shlex.quote(report["inputs"]["output_root"])
    dataset_jsonl = shlex.quote(report["inputs"]["dataset_jsonl"])
    python_path = next(
        row["path"]
        for row in report["package_readiness_checks"]
        if row["id"] == "python_executable_present"
    )
    python = shlex.quote(python_path)
    rc_handoff_shell = shlex.quote(report["outputs"]["rc_handoff_shell"])
    cuda_base_image_env = shlex.quote(report["outputs"]["cuda_base_image_env"])
    llamafactory_cli_raw = report["inputs"]["llamafactory_cli"]
    llamafactory_cli = shlex.quote(llamafactory_cli_raw)
    if "/" in llamafactory_cli_raw:
        llamafactory_check = f"""if [ ! -x {llamafactory_cli} ]; then
  echo "Refusing to run: LLaMA-Factory CLI is not executable: {llamafactory_cli}" >&2
  exit 2
fi"""
    else:
        llamafactory_check = f"""if ! command -v {llamafactory_cli} >/dev/null 2>&1; then
  echo "Refusing to run: LLaMA-Factory CLI is not available: {llamafactory_cli}" >&2
  exit 2
fi"""
    return f"""#!/usr/bin/env bash
set -euo pipefail

# Generated by scripts/prepare_cuda_lora_training_run.py.
# Run only on the CUDA host that will produce the real trained lora_adapter.

if [ -n "${{MIB_RUNTIME_ALLOW_FAKE_BACKEND:-}}" ]; then
  echo "Refusing to run: MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset." >&2
  exit 2
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "Refusing to run: nvidia-smi is not available." >&2
  exit 2
fi

if [ ! -x {python} ]; then
  echo "Refusing to run: Python executable is missing or not executable: {python}" >&2
  exit 2
fi

if [ ! -f {dataset_jsonl} ]; then
  echo "Refusing to run: dataset JSONL is missing: {dataset_jsonl}" >&2
  exit 2
fi

{llamafactory_check}

if [ ! -f {output_root}/backend_config.yaml ]; then
  echo "Refusing to run: backend_config.yaml is missing under {output_root}" >&2
  exit 2
fi

if [ ! -f {rc_handoff_shell} ]; then
  echo "Refusing to run: RC handoff shell is missing: {rc_handoff_shell}" >&2
  exit 2
fi

if [ -z "${{{DOCKER_BASE_IMAGE_ENV}:-}}" ]; then
  printf '\\n== resolve_cuda_base_image ==\\n'
  {resolver['shell']}
  if [ ! -f {cuda_base_image_env} ]; then
    echo "Refusing to run: resolver did not write {cuda_base_image_env}" >&2
    exit 2
  fi
  . {cuda_base_image_env}
fi

case "${{{DOCKER_BASE_IMAGE_ENV}:-}}" in
  *@sha256:*) ;;
  *) echo "Refusing to run: {DOCKER_BASE_IMAGE_ENV} must include @sha256." >&2; exit 2 ;;
esac

{commands}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or finalize a real CUDA LLaMA-Factory LoRA adapter run.")
    parser.add_argument("--finalize-only", action="store_true")
    parser.add_argument("--dataset-jsonl")
    parser.add_argument("--dataset-id", default="router_dataset")
    parser.add_argument("--base-model", choices=sorted(LOCKED_BASE_MODELS), required=True)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--output-root", default="/tmp/mib-real-adapter")
    parser.add_argument("--training-preset", choices=["quick", "balanced", "production"], default="balanced")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--project-id", default="external_cuda_handoff")
    parser.add_argument("--job-id", default="external_cuda_train")
    parser.add_argument("--model-run-id", default="external_cuda_model_run")
    parser.add_argument("--hardware-profile-id", default="external_cuda_host")
    parser.add_argument("--python", default="./.venv/bin/python")
    parser.add_argument("--llamafactory-cli", default="./.venv/bin/llamafactory-cli")
    parser.add_argument("--cuda-base-image-candidate", action="append")
    parser.add_argument("--agent-id", default="finance.router.v1")
    parser.add_argument("--image", default="mib-export:test")
    parser.add_argument("--docker-context-output", default="/tmp/mib-real-adapter/docker_context")
    parser.add_argument("--cuda-base-image-json-output", default="artifacts/review/real_adapter_cuda_base_image_resolution.json")
    parser.add_argument("--cuda-base-image-env-output", default="artifacts/review/real_adapter_cuda_base_image.env")
    parser.add_argument("--model-cache-json-output", default="artifacts/review/strict_model_cache_preparation.json")
    parser.add_argument("--preflight-json-output", default="artifacts/review/real_adapter_cuda_training_prereq_preflight.json")
    parser.add_argument("--adapter-intake-json-output", default="artifacts/review/real_adapter_artifact_intake.json")
    parser.add_argument("--finalize-json-output", default="artifacts/review/real_adapter_cuda_training_finalize.json")
    parser.add_argument("--docker-handoff-json-output", default="artifacts/review/real_adapter_docker_image_handoff.json")
    parser.add_argument("--docker-handoff-markdown-output", default="artifacts/review/real_adapter_docker_image_handoff.md")
    parser.add_argument("--docker-handoff-shell-output", default="artifacts/review/real_adapter_docker_image_handoff.sh")
    parser.add_argument("--rc-handoff-shell", default="artifacts/review/real_adapter_cuda_handoff.sh")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_cuda_training_handoff.json")
    parser.add_argument("--markdown-output", default="artifacts/review/real_adapter_cuda_training_handoff.md")
    parser.add_argument("--shell-output", default="artifacts/review/real_adapter_cuda_training_handoff.sh")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.finalize_only:
        report = build_finalize_report(args)
        write_json(args.json_output, report)
        print(json.dumps({"json_output": args.json_output, "status": report["status"]}, sort_keys=True))
        return 0 if report["status"] == "GO_CUDA_LORA_TRAINING_FINALIZE" else 1

    if not args.dataset_jsonl:
        raise SystemExit("--dataset-jsonl is required unless --finalize-only is set")
    if not args.model_cache_dir:
        raise SystemExit("--model-cache-dir is required unless --finalize-only is set")
    report = build_prepare_report(args)
    write_json(args.json_output, report)
    write_text(args.markdown_output, render_markdown(report))
    write_text(args.shell_output, render_shell(report))
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "markdown_output": args.markdown_output,
                "shell_output": args.shell_output,
                "status": report["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
