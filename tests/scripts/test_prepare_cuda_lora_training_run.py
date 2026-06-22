from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prepare = load_module("scripts/prepare_cuda_lora_training_run.py", "prepare_cuda_lora_training_run")


def write_dataset(path: Path) -> Path:
    routes = ["finance_income", "risk_summary", "blocked_pii"]
    rows = []
    for index in range(12):
        route = routes[index % len(routes)]
        rows.append(
            {
                "instruction": "Classify the request into one of the allowed routes.",
                "input": {"text": f"row {index}", "allowed_routes": routes},
                "output": {
                    "route": route,
                    "task_type": "block" if route.startswith("blocked") else "generate_report",
                    "requires_calculation": route == "finance_income",
                    "requires_human_review": route.startswith("blocked"),
                    "confidence": 0.9,
                },
            }
        )
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return path


def args_for(tmp_path: Path) -> SimpleNamespace:
    dataset = write_dataset(tmp_path / "dataset.jsonl")
    model_cache = tmp_path / "model_cache"
    model_cache.mkdir()
    return SimpleNamespace(
        finalize_only=False,
        dataset_jsonl=str(dataset),
        dataset_id="unit_router",
        base_model="microsoft/Phi-3.5-mini-instruct",
        model_cache_dir=str(model_cache),
        output_root=str(tmp_path / "mib-real-adapter"),
        training_preset="balanced",
        seed=42,
        max_seq_length=1024,
        project_id="project",
        job_id="job",
        model_run_id="model_run",
        hardware_profile_id="gpu",
        python="./.venv/bin/python",
        llamafactory_cli="./.venv/bin/llamafactory-cli",
        cuda_base_image_candidate=None,
        agent_id="finance.router.v1",
        image="mib-export:test",
        docker_context_output=str(tmp_path / "mib-real-adapter" / "docker_context"),
        cuda_base_image_json_output="artifacts/review/real_adapter_cuda_base_image_resolution.json",
        cuda_base_image_env_output="artifacts/review/real_adapter_cuda_base_image.env",
        model_cache_json_output="artifacts/review/strict_model_cache_preparation.json",
        preflight_json_output="artifacts/review/real_adapter_cuda_training_prereq_preflight.json",
        adapter_intake_json_output="artifacts/review/real_adapter_artifact_intake.json",
        finalize_json_output="artifacts/review/real_adapter_cuda_training_finalize.json",
        docker_handoff_json_output="artifacts/review/real_adapter_docker_image_handoff.json",
        docker_handoff_markdown_output="artifacts/review/real_adapter_docker_image_handoff.md",
        docker_handoff_shell_output="artifacts/review/real_adapter_docker_image_handoff.sh",
        rc_handoff_shell="artifacts/review/real_adapter_cuda_handoff.sh",
        json_output=str(tmp_path / "handoff.json"),
        markdown_output=str(tmp_path / "handoff.md"),
        shell_output=str(tmp_path / "handoff.sh"),
    )


def test_prepare_writes_llamafactory_config_and_operator_shell(tmp_path: Path) -> None:
    args = args_for(tmp_path)

    report = prepare.build_prepare_report(args)
    markdown = prepare.render_markdown(report)
    shell = prepare.render_shell(report)
    backend_config = yaml.safe_load((Path(args.output_root) / "backend_config.yaml").read_text(encoding="utf-8"))
    dataset_info = json.loads((Path(args.output_root) / "dataset" / "llamafactory" / "dataset_info.json").read_text(encoding="utf-8"))

    assert report["status"] == "PREPARED_NOT_RUN"
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert [row["id"] for row in report["package_readiness_checks"]] == [
        "dataset_jsonl_present",
        "python_executable_present",
        "llamafactory_cli_present",
        "model_cache_dir_present",
        "backend_config_present",
        "rc_handoff_shell_present",
    ]
    assert all(row["required_before_run"] is True for row in report["package_readiness_checks"])
    assert all(row["shell_guard"] is True for row in report["package_readiness_checks"])
    assert backend_config["lora_rank"] == 8
    assert backend_config["lora_alpha"] == 16
    assert report["backend_config_summary"]["lora_rank"] == 8
    assert "mib_router_unit_router" in dataset_info
    assert "scripts/check_cuda_lora_training_prereqs.py" in shell
    assert "scripts/prepare_strict_model_cache.py" in shell
    assert "--model-cache-dir" in shell
    assert "--allow-download" in shell
    assert "READY_STRICT_MODEL_CACHE" in shell
    assert "Python executable is missing or not executable" in shell
    assert "dataset JSONL is missing" in shell
    assert "RC handoff shell is missing" in shell
    assert "scripts/resolve_cuda_base_image.py" in shell
    assert "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime" in shell
    assert "artifacts/review/real_adapter_cuda_base_image.env" in shell
    assert shell.index("== resolve_cuda_base_image ==") < shell.index("== preflight_cuda_training ==")
    assert shell.index("== prepare_strict_model_cache ==") < shell.index("== preflight_cuda_training ==")
    assert "--llamafactory-cli ./.venv/bin/llamafactory-cli" in shell
    assert "./.venv/bin/llamafactory-cli train" in shell
    assert "scripts/verify_real_adapter_artifact.py" in shell
    assert "scripts/prepare_real_adapter_docker_image.py" in shell
    assert "--cuda-base-image-json-output artifacts/review/real_adapter_cuda_base_image_resolution.json" in shell
    assert "--cuda-base-image-env-output artifacts/review/real_adapter_cuda_base_image.env" in shell
    assert "--cuda-base-image-candidate pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime" in shell
    assert [row["id"] for row in report["command_sequence"]][-3:] == [
        "prepare_docker_image",
        "run_docker_image_handoff",
        "run_rc_handoff",
    ]
    assert "artifacts/review/real_adapter_docker_image_handoff.sh" in shell
    assert "artifacts/review/real_adapter_cuda_handoff.sh" in shell
    assert shell.index("== preflight_cuda_training ==") < shell.index("== train_real_adapter ==")
    assert shell.index("== verify_adapter_intake ==") < shell.index("== prepare_docker_image ==")
    assert shell.index("== prepare_docker_image ==") < shell.index("== run_docker_image_handoff ==")
    assert shell.index("== run_docker_image_handoff ==") < shell.index("== run_rc_handoff ==")
    assert "bash artifacts/review/real_adapter_docker_image_handoff.sh" in shell
    assert shell.index("== prepare_docker_image ==") < shell.index("== run_rc_handoff ==")
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset" in shell
    assert "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST must include @sha256" in shell
    assert "model cache directory is missing" not in shell
    assert "## Package Readiness Checks" in markdown
    assert "`dataset_jsonl_present`" in markdown
    assert "`python_executable_present`" in markdown
    assert "`rc_handoff_shell_present`" in markdown
    assert "lora_rank: 8" in markdown
    assert "lora_alpha: 16" in markdown
