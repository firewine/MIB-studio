from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .fallback import fallback_response
from .security import authorize
from .verifier import verify_router_output


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "agent_contract.yaml"


class RunRequest(BaseModel):
    text: str
    allowed_routes: list[str] | None = None


def load_contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text())


app = FastAPI(title="MIB Exported Agent Runtime")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/agents/{agent_id}/run")
def run_agent(agent_id: str, request: RunRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorize(authorization):
        raise HTTPException(status_code=401, detail="AUTH_INVALID")
    contract = load_contract()
    if agent_id != contract["agent_id"]:
        raise HTTPException(status_code=404, detail="AGENT_NOT_FOUND")
    route = (request.allowed_routes or [row["route_id"] for row in contract["route_catalog"]["routes"]])[0]
    output = {
        "route": route,
        "task_type": "generate_report",
        "requires_calculation": False,
        "requires_human_review": False,
        "confidence": 0.5,
    }
    ok, errors = verify_router_output(output, contract)
    if not ok:
        output = fallback_response(",".join(errors), contract)
    return {"output": output, "verifier_passed": ok}


@app.post("/v1/chat/completions")
def chat_completions(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if payload.get("stream") is True:
        raise HTTPException(status_code=400, detail="STREAMING_NOT_SUPPORTED_V0")
    message = (payload.get("messages") or [{"content": ""}])[-1]
    content = message.get("content", "")
    contract = load_contract()
    result = run_agent(contract["agent_id"], RunRequest(text=str(content)), authorization)
    return {
        "id": "mib-exported-runtime",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(result["output"])}, "finish_reason": "stop"}],
    }
