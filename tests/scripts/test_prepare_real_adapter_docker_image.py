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


docker = load_module("scripts/prepare_real_adapter_docker_image.py", "prepare_real_adapter_docker_image")
adapter_verify = load_module("scripts/verify_real_adapter_artifact.py", "verify_real_adapter_artifact_for_docker_test")


def args_for(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        materialize_context=False,
        adapter_root=str(tmp_path / "mib-real-adapter"),
        base_model="microsoft/Phi-3.5-mini-instruct",
        agent_id="finance.router.v1",
        image="mib-export:test",
        context_output=str(tmp_path / "docker_context"),
        python="./.venv/bin/python",
        materialize_json_output=str(tmp_path / "docker_context_report.json"),
        json_output=str(tmp_path / "handoff.json"),
        markdown_output=str(tmp_path / "handoff.md"),
        shell_output=str(tmp_path / "handoff.sh"),
    )


def test_plan_report_refuses_fake_backend_and_requires_digest_base_image(tmp_path: Path) -> None:
    args = args_for(tmp_path)

    report = docker.plan_report(args)
    markdown = docker.render_markdown(report)
    shell = docker.render_shell(report)

    assert report["status"] == "PLAN_PREPARED_NOT_RUN"
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset" in shell
    assert "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is required" in shell
    assert "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST must include @sha256" in shell
    assert "docker build --pull=false" in shell
    assert "docker image inspect mib-export:test" in shell
    assert "mib-export:test" in markdown


def test_materialize_context_reuses_runtime_templates_and_validates_export_manifest(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    adapter_dir, _manifest_path = adapter_verify.write_self_test_adapter(Path(args.adapter_root).parent)
    args.adapter_root = str(adapter_dir.parent)

    materialized = docker.materialize_context(args)
    context = Path(args.context_output)
    manifest = json.loads((context / "manifest.json").read_text(encoding="utf-8"))
    contract = yaml.safe_load((context / "agent_contract.yaml").read_text(encoding="utf-8"))

    assert materialized["manifest_valid"] is True
    assert materialized["adapter_intake_status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE"
    assert (context / "Dockerfile").is_file()
    assert (context / "adapter" / "adapter.safetensors").is_file()
    assert (context / "adapter" / "adapter_config.json").is_file()
    assert (context / "runtime" / "agents" / "run.py").is_file()
    assert (context / "runtime" / "loaders" / "transformers_lora.py").is_file()
    assert (context / "requirements-runtime.txt").is_file()
    assert manifest["export_type"] == "docker"
    assert manifest["agent_id"] == "finance.router.v1"
    assert manifest["adapter"]["format"] == "lora_adapter"
    assert manifest["base_model"]["id"] == "microsoft/Phi-3.5-mini-instruct"
    assert manifest["base_model"]["materialization"] == "external_cache"
    assert contract["agent_id"] == "finance.router.v1"
    assert contract["adapter"]["sha256"] == materialized["adapter_sha256"]
    assert {item["role"] for item in manifest["files"]} >= {
        "agent_contract",
        "adapter",
        "adapter_config",
        "runtime_entrypoint",
        "runtime_requirements",
    }
