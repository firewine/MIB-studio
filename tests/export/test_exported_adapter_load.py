from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.export.test_exported_runtime_smoke import ROUTES, create_runtime_root


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def infer(self, *, input_payload: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"input_payload": input_payload, "agent_id": contract["agent_id"]})
        return {
            "route": "finance_income",
            "task_type": "provide_advice",
            "requires_calculation": True,
            "requires_human_review": False,
            "confidence": 0.94,
        }


def _clear_exported_runtime_modules() -> None:
    for name in list(sys.modules):
        if name == "agents" or name.startswith("agents.") or name == "loaders" or name.startswith("loaders."):
            sys.modules.pop(name, None)


def _runtime_module(root: Path, monkeypatch: pytest.MonkeyPatch, *, fake_backend: bool = False) -> Any:
    monkeypatch.setenv("MIB_RUNTIME_BEARER_TOKEN", "x" * 32)
    monkeypatch.setenv("MIB_MODEL_CACHE_DIR", str(root.parent / "cache"))
    if fake_backend:
        monkeypatch.setenv("MIB_RUNTIME_ALLOW_FAKE_BACKEND", "1")
    else:
        monkeypatch.delenv("MIB_RUNTIME_ALLOW_FAKE_BACKEND", raising=False)
    monkeypatch.syspath_prepend(str(root / "runtime"))
    _clear_exported_runtime_modules()
    return importlib.import_module("agents.run")


@pytest.mark.asyncio
async def test_exported_runtime_fake_backend_requires_explicit_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_runtime_root(tmp_path)
    module = _runtime_module(root, monkeypatch, fake_backend=False)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=module.app, raise_app_exceptions=False),
        base_url="http://runtime.test",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_exported_runtime_invokes_loaded_adapter_for_native_and_openai_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = create_runtime_root(tmp_path)
    module = _runtime_module(root, monkeypatch, fake_backend=False)
    loader_module = importlib.import_module("loaders.transformers_lora")
    adapter = RecordingAdapter()

    monkeypatch.setattr(loader_module, "load_transformers_lora", lambda *args, **kwargs: adapter)
    module.state.cache_clear()

    headers = {"Authorization": "Bearer " + "x" * 32}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=module.app), base_url="http://runtime.test") as client:
        assert (await client.get("/healthz")).json() == {"ok": True}
        native = await client.post(
            "/agents/support_router.v1/run",
            json={"input": {"text": "finance income calculation", "allowed_routes": ROUTES}},
            headers=headers,
        )
        openai = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "finance income calculation"}]},
            headers=headers,
        )

    assert native.status_code == 200
    assert openai.status_code == 200
    assert [call["input_payload"]["text"] for call in adapter.calls] == [
        "finance income calculation",
        "finance income calculation",
    ]
    assert all(call["agent_id"] == "support_router.v1" for call in adapter.calls)


def test_exported_transformers_adapter_cannot_infer_with_metadata_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_runtime_root(tmp_path)
    _runtime_module(root, monkeypatch, fake_backend=False)
    loader_module = importlib.import_module("loaders.transformers_lora")
    adapter = loader_module.TransformersLoraAdapter(adapter_dir=root / "adapter", model_cache_dir=root.parent / "cache")

    with pytest.raises(RuntimeError, match="TRANSFORMERS_BACKEND_NOT_LOADED"):
        adapter.infer(input_payload={"text": "finance"}, contract={"agent_id": "support_router.v1"})


def test_exported_mlx_adapter_cannot_infer_with_metadata_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_runtime_root(tmp_path)
    _runtime_module(root, monkeypatch, fake_backend=False)
    loader_module = importlib.import_module("loaders.mlx_lora")
    adapter = loader_module.MlxLoraAdapter(adapter_dir=root / "adapter", model_cache_dir=root.parent / "cache")

    with pytest.raises(RuntimeError, match="MLX_BACKEND_NOT_LOADED"):
        adapter.infer(input_payload={"text": "finance"}, contract={"agent_id": "support_router.v1"})
