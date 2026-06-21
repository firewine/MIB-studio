from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
import httpx
import yaml
from jsonschema import Draft7Validator


ROUTES = ["finance_income", "risk_summary", "human_review", "blocked_pii"]


def create_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / "exported"
    shutil.copytree("packages/agent-runtime/templates/zip_runtime/agents", root / "runtime" / "agents")
    shutil.copytree("packages/agent-runtime/loaders", root / "runtime" / "loaders")
    shutil.copy2("packages/agent-runtime/templates/zip_runtime/requirements-runtime.txt", root / "requirements-runtime.txt")
    shutil.copytree("schemas", root / "schemas", ignore=shutil.ignore_patterns("openapi.json", "export_manifest.schema.json"))
    adapter = root / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter.safetensors").write_bytes(b"fake adapter")
    (adapter / "adapter_config.json").write_text('{"format":"lora_adapter"}\n', encoding="utf-8")
    contract = runtime_contract()
    (root / "agent_contract.yaml").write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    cache_root = tmp_path / "cache"
    cache_subdir = "google__gemma-2b-it@" + "0" * 40
    required_files = []
    for index, name in enumerate(["config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors"]):
        data = f"cache-{index}".encode()
        path = cache_root / cache_subdir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        required_files.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    manifest = {
        "base_model": {"cache_subdir": cache_subdir, "required_files": required_files},
        "adapter": {"format": "lora_adapter"},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def runtime_app(root: Path, monkeypatch: pytest.MonkeyPatch, token: str | None = "x" * 32) -> Any:
    if token is None:
        monkeypatch.delenv("MIB_RUNTIME_BEARER_TOKEN", raising=False)
    else:
        monkeypatch.setenv("MIB_RUNTIME_BEARER_TOKEN", token)
    monkeypatch.setenv("MIB_RUNTIME_ALLOW_FAKE_BACKEND", "1")
    monkeypatch.setenv("MIB_MODEL_CACHE_DIR", str(root.parent / "cache"))
    monkeypatch.syspath_prepend(str(root / "runtime"))
    for name in list(sys.modules):
        if name == "agents" or name.startswith("agents.") or name == "loaders" or name.startswith("loaders."):
            sys.modules.pop(name, None)
    return __import__("agents.run", fromlist=["app"]).app


def runtime_contract() -> dict[str, Any]:
    return {
        "agent_id": "support_router.v1",
        "base_model": "google/gemma-2b-it",
        "adapter": {"format": "lora_adapter"},
        "route_catalog": {
            "schema_version": "route_catalog.v1",
            "sha256": "0" * 64,
            "routes": [
                {"route_id": "finance_income", "description": "Finance income route", "is_unsafe": False, "order": 0},
                {"route_id": "risk_summary", "description": "Risk route", "is_unsafe": False, "order": 1},
                {"route_id": "human_review", "description": "Human review", "is_unsafe": True, "order": 2},
                {"route_id": "blocked_pii", "description": "PII block", "is_unsafe": True, "order": 3},
            ],
        },
        "verifiers": [{"name": "confidence_threshold", "config": {"threshold": 0.0}}],
        "fallback": {"enabled": False},
    }


def load_core_router() -> Any:
    spec = importlib.util.spec_from_file_location("test_core_router_inference", "packages/agent-runtime/core/router_inference.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_exported_runtime_native_and_openai_endpoints(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_runtime_root(tmp_path)
    app = runtime_app(root, monkeypatch)
    headers = {"Authorization": "Bearer " + "x" * 32}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://runtime.test") as client:
        assert (await client.get("/healthz")).json() == {"ok": True}
        unauthorized = await client.post("/agents/support_router.v1/run", json={"input": {"text": "finance_income income", "allowed_routes": ROUTES}})
        assert unauthorized.status_code == 401

        native = await client.post(
            "/agents/support_router.v1/run",
            json={"input": {"text": "finance_income income calculation", "allowed_routes": ROUTES}},
            headers=headers,
        )
        assert native.status_code == 200
        body = native.json()
        assert body["verifier_status"] == "PASS"
        Draft7Validator(json.loads(Path("schemas/router_output.schema.json").read_text(encoding="utf-8"))).validate(body["output"])

        openai = await client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "finance_income income calculation"}]},
            headers=headers,
        )
        assert openai.status_code == 200
        content = json.loads(openai.json()["choices"][0]["message"]["content"])
        assert content == body["output"]
        stream = await client.post("/v1/chat/completions", json={"messages": [], "stream": True}, headers=headers)
        assert stream.status_code == 400


@pytest.mark.asyncio
async def test_exported_runtime_validates_model_cache_before_inference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_runtime_root(tmp_path)
    (root.parent / "cache" / ("google__gemma-2b-it@" + "0" * 40) / "config.json").unlink()
    app = runtime_app(root, monkeypatch)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://runtime.test",
    ) as client:
        unauthorized = await client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "finance"}]})
        assert unauthorized.status_code == 401
        response = await client.get("/healthz")
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_exported_runtime_requires_valid_token_env_before_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for token in [None, "short-token"]:
        root = create_runtime_root(tmp_path / str(token))
        app = runtime_app(root, monkeypatch, token=token)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://runtime.test",
        ) as client:
            response = await client.get("/healthz")
            assert response.status_code == 500
