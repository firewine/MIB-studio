from __future__ import annotations

from pathlib import Path


def test_cuda_dockerfile_is_digest_pinned_non_root_and_runtime_only() -> None:
    text = Path("packages/agent-runtime/templates/docker/Dockerfile.cuda").read_text(encoding="utf-8")
    assert "ARG BASE_IMAGE_WITH_DIGEST" in text
    assert "FROM ${BASE_IMAGE_WITH_DIGEST}" in text
    assert "*@sha256:*" in text
    assert "USER mib:mib" in text
    assert "EXPOSE 8000" in text
    assert "HEALTHCHECK" in text
    assert "MIB_MODEL_CACHE_DIR=/models" in text
    assert "MIB_LOCAL_API_TOKEN" not in text
    assert "MIB_RUNTIME_BEARER_TOKEN=" not in text
    assert "MIB_FALLBACK_API_KEY=" not in text
