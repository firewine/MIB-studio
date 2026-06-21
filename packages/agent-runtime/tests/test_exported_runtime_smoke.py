from __future__ import annotations

from pathlib import Path


def test_runtime_template_files_exist() -> None:
    root = Path("packages/agent-runtime/templates/zip_runtime")
    for relative in [
        "agents/run.py",
        "agents/verifier.py",
        "agents/fallback.py",
        "agents/router_inference.py",
        "agents/security.py",
        "requirements-runtime.txt",
    ]:
        assert (root / relative).is_file()


def test_runtime_template_loaders_are_not_metadata_only() -> None:
    for path in [
        Path("packages/agent-runtime/loaders/transformers_lora.py"),
        Path("packages/agent-runtime/loaders/mlx_lora.py"),
    ]:
        text = path.read_text(encoding="utf-8")
        assert "def infer(" in text
        assert "invocation_count" in text
