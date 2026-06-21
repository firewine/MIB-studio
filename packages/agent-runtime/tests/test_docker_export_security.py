from __future__ import annotations

from pathlib import Path


def test_dockerfile_uses_digest_arg_and_non_root_user() -> None:
    text = Path("packages/agent-runtime/templates/docker/Dockerfile.cuda").read_text()
    assert "BASE_IMAGE_WITH_DIGEST" in text
    assert "USER mib" in text
    assert "HEALTHCHECK" in text
