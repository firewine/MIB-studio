from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolver = load_module("scripts/resolve_cuda_base_image.py", "resolve_cuda_base_image")


def completed(command: list[str], returncode: int = 0, stdout: str = "[]", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def args_for(*candidates: str) -> SimpleNamespace:
    return SimpleNamespace(candidate=list(candidates), timeout=30)


def inspect_stdout(*, repo_digests: list[str], env: list[str], labels: dict[str, str] | None = None) -> str:
    return json.dumps(
        [
            {
                "Id": "sha256:" + "1" * 64,
                "RepoDigests": repo_digests,
                "RepoTags": ["pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"],
                "Config": {
                    "Env": env,
                    "Labels": labels or {},
                },
            }
        ]
    )


def test_resolves_local_pytorch_cuda_repo_digest_and_env() -> None:
    digest = "pytorch/pytorch@sha256:" + "a" * 64

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        assert command == ["docker", "image", "inspect", "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"]
        return completed(
            command,
            stdout=inspect_stdout(
                repo_digests=[digest],
                env=["CUDA_VERSION=12.1.1", "NVIDIA_VISIBLE_DEVICES=all", "PYTHON_VERSION=3.11.8"],
            ),
        )

    report = resolver.build_report(args_for("pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"), runner=runner)

    assert report["status"] == resolver.READY_STATUS
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert report["env"]["MIB_DOCKER_BASE_IMAGE_WITH_DIGEST"] == digest
    assert report["selected"]["digest_reference"] == digest
    assert "env:CUDA_VERSION" in report["selected"]["cuda_markers"]
    assert "reference_is_pytorch_runtime" in report["selected"]["python_runtime_markers"]
    assert resolver.render_env(report) == f"export MIB_DOCKER_BASE_IMAGE_WITH_DIGEST={digest}\n"


def test_rejects_non_cuda_image_even_with_repo_digest() -> None:
    digest = "getbeta-backend@sha256:" + "b" * 64

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return completed(command, stdout=inspect_stdout(repo_digests=[digest], env=["PATH=/usr/local/bin"]))

    report = resolver.build_report(args_for("getbeta-backend:latest"), runner=runner)

    assert report["status"] == resolver.NOT_READY_STATUS
    assert report["blockers"] == ["cuda_base_image_not_resolved"]
    assert report["env"] == {}
    assert report["candidates"][0]["status"] == "cuda_markers_missing"
    assert report["candidates"][0]["digest_reference"] == digest


def test_rejects_cuda_image_without_python_runtime_markers() -> None:
    digest = "nvidia/cuda@sha256:" + "c" * 64

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return completed(command, stdout=inspect_stdout(repo_digests=[digest], env=["CUDA_VERSION=12.1.1", "NVIDIA_VISIBLE_DEVICES=all"]))

    report = resolver.build_report(args_for("nvidia/cuda:12.1.1-runtime-ubuntu22.04"), runner=runner)

    candidate = report["candidates"][0]
    assert report["status"] == resolver.NOT_READY_STATUS
    assert report["env"] == {}
    assert candidate["status"] == "python_runtime_markers_missing"
    assert candidate["cuda_markers"] != []
    assert candidate["python_runtime_markers"] == []


def test_rejects_cuda_tag_without_repo_digest() -> None:
    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return completed(command, stdout=inspect_stdout(repo_digests=[], env=["CUDA_VERSION=12.1.1"]))

    report = resolver.build_report(args_for("pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"), runner=runner)

    assert report["status"] == resolver.NOT_READY_STATUS
    assert report["candidates"][0]["status"] == "no_digest_reference"
    assert report["candidates"][0]["repo_digests"] == []


def test_uses_default_candidate_when_none_is_supplied() -> None:
    seen: list[list[str]] = []

    def runner(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        return completed(command, returncode=1, stderr="No such image")

    report = resolver.build_report(args_for(), runner=runner)

    assert report["status"] == resolver.NOT_READY_STATUS
    assert seen == [["docker", "image", "inspect", "pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime"]]
