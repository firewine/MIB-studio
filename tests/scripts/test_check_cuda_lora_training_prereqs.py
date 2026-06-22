from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = load_module("scripts/check_cuda_lora_training_prereqs.py", "check_cuda_lora_training_prereqs")


def completed(command: list[str], returncode: int = 0, stdout: str = "ok", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def args_for(tmp_path: Path) -> SimpleNamespace:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(json.dumps({"instruction": "route", "input": {}, "output": {"route": "finance_income"}}) + "\n", encoding="utf-8")
    backend_config = tmp_path / "backend_config.yaml"
    backend_config.write_text(
        "\n".join(
            [
                "do_train: true",
                f"model_name_or_path: {tmp_path / 'model_cache'}",
                "finetuning_type: lora",
                f"output_dir: {tmp_path / 'run' / 'adapter'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return SimpleNamespace(
        dataset_jsonl=str(dataset),
        base_model="microsoft/Phi-3.5-mini-instruct",
        model_cache_dir=str(tmp_path / "model_cache"),
        output_root=str(tmp_path / "run"),
        backend_config=str(backend_config),
        image="mib-export:test",
        llamafactory_cli="./.venv/bin/llamafactory-cli",
        verify_model_cache_hashes=True,
        json_output=str(tmp_path / "preflight.json"),
        expected_status=None,
    )


def test_preflight_reports_not_ready_without_cuda_docker_digest_or_cache(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    commands: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[0] == "nvidia-smi":
            return completed(command, 127, stderr="nvidia-smi: not found")
        if command[0] == args.llamafactory_cli:
            return completed(command, 127, stderr="llamafactory-cli: not found")
        if command[:2] == ["docker", "version"]:
            return completed(command, 1, stderr="docker daemon unavailable")
        raise AssertionError(f"unexpected command: {command}")

    report = preflight.build_report(args, runner=runner, env={})

    assert report["status"] == preflight.NOT_READY_STATUS
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert {
        "docker_base_image_env_digest",
        "strict_model_cache_files",
        "cuda_visible",
        "llamafactory_cli_available",
        "docker_daemon_available",
        "docker_base_image_available",
    } <= set(report["blockers"])
    assert "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST" in json.dumps(report)
    assert "MIB_RUNTIME_ALLOW_FAKE_BACKEND" in json.dumps(report)
    assert "nvidia-smi" in json.dumps(report)
    assert args.llamafactory_cli in json.dumps(report)
    assert [args.llamafactory_cli, "version"] in commands
    assert [args.llamafactory_cli, "--version"] not in commands


def test_preflight_ready_with_digest_env_strict_cache_and_commands(tmp_path: Path, monkeypatch) -> None:
    args = args_for(tmp_path)
    cache_subdir = "test__model@1234567890abcdef1234567890abcdef12345678"
    cache_root = Path(args.model_cache_dir) / cache_subdir
    cache_root.mkdir(parents=True)
    files = []
    for name, payload in {"config.json": b"{}", "model.safetensors": b"weights"}.items():
        path = cache_root / name
        path.write_bytes(payload)
        files.append(SimpleNamespace(path=name, sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload), required=True))
    monkeypatch.setattr(
        preflight,
        "load_model_catalog",
        lambda: SimpleNamespace(get=lambda model_id: SimpleNamespace(id=model_id, cache_subdir=cache_subdir, required_files=tuple(files))),
    )

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if command[0] == "nvidia-smi":
            return completed(command)
        if command == [args.llamafactory_cli, "version"]:
            return completed(command, stdout="Welcome to LLaMA Factory, version 0.9.5")
        if command[:2] == ["docker", "version"]:
            return completed(command, stdout="24.0")
        if command[:3] == ["docker", "image", "inspect"]:
            return completed(command, stdout="[]")
        raise AssertionError(f"unexpected command: {command}")

    report = preflight.build_report(
        args,
        runner=runner,
        env={"MIB_DOCKER_BASE_IMAGE_WITH_DIGEST": "local-cuda-base@sha256:" + "a" * 64},
    )

    cache_check = next(row for row in report["checks"] if row["id"] == "strict_model_cache_files")
    assert report["status"] == preflight.READY_STATUS
    assert report["blockers"] == []
    assert cache_check["verify_hashes"] is True
    assert cache_check["hash_mismatches"] == []
