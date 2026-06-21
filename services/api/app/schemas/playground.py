from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlaygroundRunRequest(StrictModel):
    input: dict[str, Any]
    approve_fallback: bool = False


class PlaygroundRunResponse(StrictModel):
    output: dict[str, Any]
    verifier_status: Literal["PASS", "FAIL"]
    verifier_errors: list[str]
    fallback_required: bool = False
    fallback_used: bool = False
    audit_event_id: str | None = None
