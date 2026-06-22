#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.model_catalog import load_model_catalog
from verify_real_adapter_artifact import verify_adapter


SCHEMA_VERSION = "mib_real_adapter_docker_image_handoff.v1"
DEFAULT_CUDA_BASE_IMAGE_CANDIDATE = "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"
DOCKER_BASE_IMAGE_ENV = "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST"
ZIP_TEMPLATE = REPO_ROOT / "packages" / "agent-runtime" / "templates" / "zip_runtime"
LOADER_ROOT = REPO_ROOT / "packages" / "agent-runtime" / "loaders"
DOCKERFILE = REPO_ROOT / "packages" / "agent-runtime" / "templates" / "docker" / "Dockerfile.cuda"
SCHEMA_ROOT = REPO_ROOT / "schemas"
EXPORT_MANIFEST_SCHEMA = SCHEMA_ROOT / "export_manifest.schema.json"
ROUTE_IDS = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_text(path: str | Path, value: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, sort_keys=True, indent=2) + "\n")


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_entry(root: Path, relative: str, role: str, required: bool = True) -> dict[str, Any]:
    path = root / relative
    return {"path": relative, "role": role, "sha256": sha256_file(path), "size_bytes": path.stat().st_size, "required": required}


def route_catalog() -> dict[str, Any]:
    rows = [
        {
            "route_id": route_id,
            "description": route_id.replace("_", " "),
            "is_unsafe": route_id.startswith("blocked") or route_id.endswith("_block"),
            "order": index,
        }
        for index, route_id in enumerate(ROUTE_IDS)
    ]
    return {"schema_version": "route_catalog.v1", "sha256": sha256_text(canonical_json(rows)), "routes": rows}


def benchmark_report() -> dict[str, Any]:
    return {
        "schema_version": "mib_external_cuda_handoff_benchmark_placeholder.v1",
        "status": "handoff_context_only",
        "release_claimed_go": False,
        "note": "This placeholder satisfies runtime manifest structure only. Release benchmark evidence remains owned by committed review artifacts and v0 readiness verifiers.",
    }


def base_model_manifest(base_model: str) -> dict[str, Any]:
    model = load_model_catalog().get(base_model)
    return {
        "id": model.id,
        "hf_commit_sha": model.hf_commit_sha,
        "cache_subdir": model.cache_subdir,
        "required_files": [{"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes} for item in model.required_files],
    }


def agent_contract(*, agent_id: str, base_model: str, adapter_sha256: str, route_catalog_data: dict[str, Any], benchmark_sha256: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "agent_type": "router",
        "base_model": base_model,
        "adapter": {"path": "adapter/", "sha256": adapter_sha256, "format": "lora_adapter"},
        "input_schema": "schemas/router_input.schema.json",
        "output_schema": "schemas/router_output.schema.json",
        "route_catalog": route_catalog_data,
        "runtime": {
            "engine": "transformers",
            "quantization": "q4",
            "max_tokens": 512,
            "temperature": 0,
            "deterministic": True,
            "compatible_backends": ["cuda"],
        },
        "verifiers": [
            {"name": "json_parse", "config": {}},
            {"name": "output_schema", "config": {"schema": "schemas/router_output.schema.json"}},
            {"name": "route_allowed", "config": {"route_catalog_sha256": route_catalog_data["sha256"]}},
            {"name": "confidence_threshold", "config": {"threshold": 0.0}},
        ],
        "fallback": {"enabled": False, "provider": "none", "condition": {"type": "disabled"}},
        "audit": {
            "log_input": False,
            "log_input_hash": True,
            "log_output": "redacted",
            "redaction_policy": "SECURITY_SPEC_19_6",
            "retention_days": 365,
        },
        "benchmark_report": {"path": "benchmark/report.json", "sha256": benchmark_sha256},
        "export_compatibility": {"supported_formats": ["zip", "docker"], "runtime_entrypoint": "agents.run:app"},
    }


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def validate_export_manifest(manifest: dict[str, Any]) -> None:
    schema = json.loads(EXPORT_MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        raise ValueError("; ".join(error.message for error in errors))


def materialize_context(args: argparse.Namespace) -> dict[str, Any]:
    adapter_root = Path(args.adapter_root)
    adapter_dir = adapter_root / "adapter"
    manifest_path = adapter_root / "manifest.json"
    intake = verify_adapter(adapter_dir=adapter_dir, expected_base_model=args.base_model, manifest_path=manifest_path)
    if intake["status"] != "GO_REAL_ADAPTER_ARTIFACT_INTAKE":
        raise ValueError("adapter intake is not GO: " + "; ".join(intake["errors"]))

    context = Path(args.context_output)
    reset_dir(context)
    copy_file(DOCKERFILE, context / "Dockerfile")
    for schema_name in ("router_input.schema.json", "router_output.schema.json"):
        copy_file(SCHEMA_ROOT / schema_name, context / "schemas" / schema_name)
    ignore_generated = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ZIP_TEMPLATE / "agents", context / "runtime" / "agents", ignore=ignore_generated)
    shutil.copytree(LOADER_ROOT, context / "runtime" / "loaders", ignore=ignore_generated)
    copy_file(ZIP_TEMPLATE / "requirements-runtime.txt", context / "requirements-runtime.txt")
    shutil.copytree(adapter_dir, context / "adapter")

    routes = route_catalog()
    benchmark = benchmark_report()
    benchmark_sha = sha256_text(canonical_json(benchmark))
    contract = agent_contract(
        agent_id=args.agent_id,
        base_model=args.base_model,
        adapter_sha256=str(intake["adapter_sha256"]),
        route_catalog_data=routes,
        benchmark_sha256=benchmark_sha,
    )
    contract_yaml = yaml.safe_dump(contract, sort_keys=False, allow_unicode=False)
    write_text(context / "agent_contract.yaml", contract_yaml)
    write_json(context / "route_catalog.json", routes)
    write_json(context / "benchmark" / "report.json", benchmark)
    write_json(context / "base_model_manifest.json", base_model_manifest(args.base_model))

    manifest = build_export_manifest(
        context=context,
        args=args,
        contract_sha256=sha256_text(canonical_json(contract)),
        route_catalog_sha256=routes["sha256"],
        benchmark_sha256=benchmark_sha,
    )
    validate_export_manifest(manifest)
    write_json(context / "manifest.json", manifest)
    return {
        "context_output": str(context),
        "manifest": str(context / "manifest.json"),
        "contract": str(context / "agent_contract.yaml"),
        "adapter_intake_status": intake["status"],
        "adapter_sha256": intake["adapter_sha256"],
        "manifest_valid": True,
    }


def build_export_manifest(
    *,
    context: Path,
    args: argparse.Namespace,
    contract_sha256: str,
    route_catalog_sha256: str,
    benchmark_sha256: str,
) -> dict[str, Any]:
    model = base_model_manifest(args.base_model)
    files = [
        file_entry(context, "agent_contract.yaml", "agent_contract"),
        file_entry(context, "route_catalog.json", "route_catalog"),
        file_entry(context, "schemas/router_input.schema.json", "input_schema"),
        file_entry(context, "schemas/router_output.schema.json", "output_schema"),
        file_entry(context, "benchmark/report.json", "benchmark_report"),
        file_entry(context, "base_model_manifest.json", "model_manifest"),
        file_entry(context, "adapter/adapter.safetensors", "adapter"),
        file_entry(context, "adapter/adapter_config.json", "adapter_config"),
        file_entry(context, "runtime/agents/run.py", "runtime_entrypoint"),
        file_entry(context, "runtime/agents/verifier.py", "runtime_code"),
        file_entry(context, "runtime/agents/router_inference.py", "runtime_code"),
        file_entry(context, "runtime/loaders/transformers_lora.py", "runtime_code"),
        file_entry(context, "runtime/loaders/mlx_lora.py", "runtime_code"),
        file_entry(context, "requirements-runtime.txt", "runtime_requirements"),
        file_entry(context, "Dockerfile", "runtime_code"),
    ]
    return {
        "schema_version": "export_manifest.v1",
        "agent_package_id": "external_cuda_real_adapter_handoff",
        "agent_id": args.agent_id,
        "contract_sha256": contract_sha256,
        "route_catalog_sha256": route_catalog_sha256,
        "benchmark_report_sha256": benchmark_sha256,
        "export_type": "docker",
        "created_at": now_utc(),
        "adapter": {"format": "lora_adapter", "required_paths": ["adapter/adapter.safetensors", "adapter/adapter_config.json"]},
        "base_model": {
            "id": model["id"],
            "hf_commit_sha": model["hf_commit_sha"],
            "materialization": "external_cache",
            "cache_env": "MIB_MODEL_CACHE_DIR",
            "cache_subdir": model["cache_subdir"],
            "required_files": model["required_files"],
        },
        "runtime": {
            "native_endpoint": "/agents/{agent_id}/run",
            "openai_endpoint": "/v1/chat/completions",
            "entrypoint": "agents.run:app",
            "run_command": f"docker run --rm -p 8000:8000 -v ${{MIB_MODEL_CACHE_DIR}}:/models:ro -e MIB_MODEL_CACHE_DIR=/models -e MIB_RUNTIME_BEARER_TOKEN {args.image}",
            "compatible_backends": ["cuda"],
            "requires_bearer_token_env": "MIB_RUNTIME_BEARER_TOKEN",
            "requires_bearer_token_min_length": 32,
        },
        "files": files,
    }


def command_row(command_id: str, shell: str, note: str) -> dict[str, str]:
    return {"id": command_id, "shell": shell, "note": note}


def shell_join(argv: list[str]) -> str:
    return shlex.join([str(part) for part in argv])


def cuda_base_image_candidates(args: argparse.Namespace) -> list[str]:
    return list(args.cuda_base_image_candidate or [DEFAULT_CUDA_BASE_IMAGE_CANDIDATE])


def cuda_base_image_resolver_shell(args: argparse.Namespace) -> str:
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
    return shell_join(command)


def plan_report(args: argparse.Namespace, *, materialized: dict[str, Any] | None = None) -> dict[str, Any]:
    materialized = materialized or {}
    resolver_cmd = cuda_base_image_resolver_shell(args)
    materialize_cmd = shell_join(
        [
            args.python,
            "scripts/prepare_real_adapter_docker_image.py",
            "--materialize-context",
            "--adapter-root",
            args.adapter_root,
            "--base-model",
            args.base_model,
            "--agent-id",
            args.agent_id,
            "--image",
            args.image,
            "--context-output",
            args.context_output,
            "--json-output",
            args.materialize_json_output,
        ]
    )
    build_cmd = (
        'docker build --pull=false --build-arg BASE_IMAGE_WITH_DIGEST="${MIB_DOCKER_BASE_IMAGE_WITH_DIGEST}" '
        f"-t {args.image} {args.context_output}"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date": now_utc(),
        "gate": "mib-studio-real-adapter-docker-image-handoff",
        "status": "CONTEXT_MATERIALIZED_NOT_BUILT" if materialized else "PLAN_PREPARED_NOT_RUN",
        "release_claimed_go": False,
        "m6_rc_claimed_go": False,
        "inputs": {
            "adapter_root": args.adapter_root,
            "base_model": args.base_model,
            "agent_id": args.agent_id,
            "image": args.image,
            "context_output": args.context_output,
            "cuda_base_image_candidates": cuda_base_image_candidates(args),
        },
        "outputs": {
            "context_output": args.context_output,
            "materialize_report": args.materialize_json_output,
            "cuda_base_image_resolution_report": args.cuda_base_image_json_output,
            "cuda_base_image_env": args.cuda_base_image_env_output,
            "shell_output": args.shell_output,
        },
        "materialized_context": materialized,
        "command_sequence": [
            command_row("resolve_cuda_base_image", resolver_cmd, f"Run only when {DOCKER_BASE_IMAGE_ENV} is unset; writes a digest-pinned CUDA base image env file."),
            command_row("materialize_context", materialize_cmd, "Copy existing runtime templates and the real adapter into a Docker build context."),
            command_row("build_image", build_cmd, "Build the digest-pinned real adapter Docker image."),
            command_row("inspect_image", f"docker image inspect {args.image}", "Require the image tag before RC endpoint capture."),
        ],
        "operator_rules": [
            "Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.",
            f"If {DOCKER_BASE_IMAGE_ENV} is unset, resolve a local CUDA/PyTorch base image with scripts/resolve_cuda_base_image.py before docker build.",
            f"{DOCKER_BASE_IMAGE_ENV} must include @sha256 before docker build.",
            "Do not use fixture-sized or self-test adapters as release evidence.",
            "Do not claim M6-RC or v0 GO until the downstream no-fake endpoint and bundle verifiers return GO.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    commands = "\n\n".join(f"### {row['id']}\n\n```bash\n{row['shell']}\n```" for row in report["command_sequence"])
    rules = "\n".join(f"- {item}" for item in report["operator_rules"])
    return f"""# Real Adapter Docker Image Handoff

```yaml
date: {report["date"]}
gate: {report["gate"]}
status: {report["status"]}
release_claimed_go: false
m6_rc_claimed_go: false
image: {report["inputs"]["image"]}
context_output: {report["inputs"]["context_output"]}
```

This artifact prepares the Docker image required by the downstream no-fake CUDA RC handoff. It does not build an image in the current host and does not claim release GO.

## Operator Rules

{rules}

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
    cuda_base_image_env = shlex.quote(report["outputs"]["cuda_base_image_env"])
    return f"""#!/usr/bin/env bash
set -euo pipefail

# Generated by scripts/prepare_real_adapter_docker_image.py.
# Run only after the real adapter exists under the configured adapter root.

if [ -n "${{MIB_RUNTIME_ALLOW_FAKE_BACKEND:-}}" ]; then
  echo "Refusing to run: MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset." >&2
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

if [ -z "${{{DOCKER_BASE_IMAGE_ENV}:-}}" ]; then
  echo "Refusing to run: {DOCKER_BASE_IMAGE_ENV} is required." >&2
  exit 2
fi

case "${{{DOCKER_BASE_IMAGE_ENV}}}" in
  *@sha256:*) ;;
  *) echo "Refusing to run: {DOCKER_BASE_IMAGE_ENV} must include @sha256." >&2; exit 2 ;;
esac

{commands}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a Docker image handoff for a real trained CUDA adapter.")
    parser.add_argument("--materialize-context", action="store_true")
    parser.add_argument("--adapter-root", default="/tmp/mib-real-adapter")
    parser.add_argument("--base-model", choices=["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"], required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--image", default="mib-export:test")
    parser.add_argument("--context-output", default="/tmp/mib-real-adapter/docker_context")
    parser.add_argument("--python", default="./.venv/bin/python")
    parser.add_argument("--cuda-base-image-candidate", action="append")
    parser.add_argument("--cuda-base-image-json-output", default="artifacts/review/real_adapter_cuda_base_image_resolution.json")
    parser.add_argument("--cuda-base-image-env-output", default="artifacts/review/real_adapter_cuda_base_image.env")
    parser.add_argument("--materialize-json-output", default="artifacts/review/real_adapter_docker_image_context.json")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_docker_image_handoff.json")
    parser.add_argument("--markdown-output", default="artifacts/review/real_adapter_docker_image_handoff.md")
    parser.add_argument("--shell-output", default="artifacts/review/real_adapter_docker_image_handoff.sh")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    materialized = materialize_context(args) if args.materialize_context else None
    report = plan_report(args, materialized=materialized)
    write_json(args.json_output, report)
    if not args.materialize_context:
        write_text(args.markdown_output, render_markdown(report))
        write_text(args.shell_output, render_shell(report))
    print(json.dumps({"json_output": args.json_output, "status": report["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
