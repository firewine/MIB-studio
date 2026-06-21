from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .security import authorize
from .verifier import verify_router_output


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "agent_contract.yaml"
MANIFEST_PATH = ROOT / "manifest.json"
ADAPTER_DIR = ROOT / "adapter"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunRequest(StrictModel):
    input: dict[str, Any] = Field(default_factory=dict)
    text: str | None = None
    allowed_routes: list[str] | None = None

    @model_validator(mode="after")
    def normalize_input(self) -> "RunRequest":
        if self.input:
            return self
        if self.text is None:
            raise ValueError("input or text is required")
        payload: dict[str, Any] = {"text": self.text}
        if self.allowed_routes is not None:
            payload["allowed_routes"] = self.allowed_routes
        self.input = payload
        return self


class RuntimeState:
    def __init__(self) -> None:
        self.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self._validate_model_cache()
        self.adapter = self._load_adapter()

    def infer(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        return self.adapter.infer(input_payload=input_payload, contract=self.contract)

    def _load_adapter(self) -> Any:
        adapter_format = self.contract.get("adapter", {}).get("format")
        model_cache_dir = model_cache_subdir(self.manifest)
        if adapter_format == "mlx_lora_adapter":
            from loaders.mlx_lora import load_mlx_lora

            return load_mlx_lora(ADAPTER_DIR, self.contract, model_cache_dir=model_cache_dir)
        from loaders.transformers_lora import load_transformers_lora

        return load_transformers_lora(ADAPTER_DIR, self.contract, model_cache_dir=model_cache_dir)

    def _validate_model_cache(self) -> None:
        cache_root = os.environ.get("MIB_MODEL_CACHE_DIR")
        if not cache_root:
            raise RuntimeError("MODEL_CACHE_MISSING: MIB_MODEL_CACHE_DIR is required")
        cache_dir = model_cache_subdir(self.manifest)
        for item in self.manifest["base_model"]["required_files"]:
            path = cache_dir / item["path"]
            if not path.is_file():
                raise RuntimeError(f"MODEL_CACHE_MISSING: {item['path']}")
            if path.stat().st_size != item["size_bytes"]:
                raise RuntimeError(f"MODEL_CACHE_HASH_MISMATCH: {item['path']}")
            import hashlib

            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError(f"MODEL_CACHE_HASH_MISMATCH: {item['path']}")


app = FastAPI(title="MIB Exported Agent Runtime")


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    state()
    return {"ok": True}


@app.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, request: RunRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorize(authorization):
        raise HTTPException(status_code=401, detail="AUTH_INVALID")
    runtime = state()
    if agent_id != runtime.contract["agent_id"]:
        raise HTTPException(status_code=404, detail="AGENT_NOT_FOUND")
    output = runtime.infer(request.input)
    verification = verify_router_output(output, runtime.contract)
    if verification["fallback_required"]:
        raise HTTPException(status_code=409, detail="FALLBACK_CREDENTIAL_REQUIRED")
    return {"output": output, **verification}


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if payload.get("stream") is True:
        raise HTTPException(status_code=400, detail="STREAMING_NOT_SUPPORTED_V0")
    if not authorize(authorization):
        raise HTTPException(status_code=401, detail="AUTH_INVALID")
    message = (payload.get("messages") or [{"content": ""}])[-1]
    runtime = state()
    input_payload = {
        "text": str(message.get("content", "")),
        "allowed_routes": [row["route_id"] for row in runtime.contract["route_catalog"]["routes"]],
    }
    result = await run_agent(runtime.contract["agent_id"], RunRequest(input=input_payload), authorization)
    return {
        "id": "mib-exported-runtime",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(result["output"], sort_keys=True)},
                "finish_reason": "stop",
            }
        ],
    }


@lru_cache(maxsize=1)
def state() -> RuntimeState:
    return RuntimeState()


def model_cache_subdir(manifest: dict[str, Any]) -> Path:
    return Path(os.environ["MIB_MODEL_CACHE_DIR"]) / manifest["base_model"]["cache_subdir"]
