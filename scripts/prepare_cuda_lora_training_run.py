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


def build_prepare_report(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    trainer_input = build_trainer_input(args)
    config_path = write_llamafactory_artifacts(trainer_input, model_cache_path=Path(args.model_cache_dir), dataset_id=args.dataset_id)
    backend_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
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
        "--json-output",
        args.docker_handoff_json_output,
        "--markdown-output",
        args.docker_handoff_markdown_output,
        "--shell-output",
        args.docker_handoff_shell_output,
    ]
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
            "output_root": args.output_root,
            "training_preset": args.training_preset,
            "seed": args.seed,
            "max_seq_length": args.max_seq_length,
        },
        "outputs": {
            "train_config": str(output_root / "train_config.json"),
            "backend_config": str(config_path),
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
        "command_sequence": [
            command_row("preflight_cuda_training", preflight_command, note="Fail fast unless CUDA, LLaMA-Factory, Docker base image, backend config, dataset, and strict model cache prerequisites are ready."),
            command_row("train_real_adapter", train_command, note="Run actual CUDA QLoRA training with LLaMA-Factory on the CUDA host."),
            command_row("finalize_manifest", finalize_command, note="Write manifest.json from the trained adapter directory."),
            command_row("verify_adapter_intake", intake_command, note="Require GO_REAL_ADAPTER_ARTIFACT_INTAKE before export/endpoint evidence."),
            command_row("prepare_docker_image", docker_handoff_command, note="Create the guarded digest-pinned Docker image handoff before RC endpoint capture."),
            command_row("run_rc_handoff", handoff_command, note="Run the existing guarded no-fake endpoint/M6/v0 handoff after the real adapter exists."),
        ],
        "operator_rules": [
            "Run on a host with NVIDIA CUDA visible to nvidia-smi.",
            "Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.",
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

## Command Sequence

{commands}
"""


def render_shell(report: dict[str, Any]) -> str:
    commands = "\n\n".join(f"printf '\\n== {row['id']} ==\\n'\n{row['shell']}" for row in report["command_sequence"])
    output_root = shlex.quote(report["inputs"]["output_root"])
    model_cache_dir = shlex.quote(report["inputs"]["model_cache_dir"])
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

{llamafactory_check}

if [ ! -d {model_cache_dir} ]; then
  echo "Refusing to run: model cache directory is missing: {model_cache_dir}" >&2
  exit 2
fi

if [ ! -f {output_root}/backend_config.yaml ]; then
  echo "Refusing to run: backend_config.yaml is missing under {output_root}" >&2
  exit 2
fi

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
    parser.add_argument("--agent-id", default="finance.router.v1")
    parser.add_argument("--image", default="mib-export:test")
    parser.add_argument("--docker-context-output", default="/tmp/mib-real-adapter/docker_context")
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
