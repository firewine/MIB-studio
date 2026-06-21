from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FallbackConditionInput(StrictModel):
    type: Literal["confidence_lt", "verifier_failed", "disabled"] = "disabled"
    threshold: float | None = Field(default=None, ge=0, le=1)


class FallbackConfigInput(StrictModel):
    enabled: bool = False
    provider: Literal["openai", "openai_compatible", "none"] = "none"
    model: str | None = None
    condition: FallbackConditionInput = Field(default_factory=FallbackConditionInput)

    @model_validator(mode="after")
    def validate_fallback_shape(self) -> "FallbackConfigInput":
        if not self.enabled:
            if self.provider != "none" or self.condition.type != "disabled":
                raise ValueError("disabled fallback must use provider=none and condition.type=disabled")
            return self
        if self.provider == "none" or not self.model:
            raise ValueError("enabled fallback requires provider and model")
        if self.condition.type == "disabled":
            raise ValueError("enabled fallback requires an active condition")
        if self.condition.type == "confidence_lt" and self.condition.threshold is None:
            raise ValueError("confidence_lt fallback requires threshold")
        return self


class AgentPackageCreate(StrictModel):
    agent_slug: str | None = Field(default=None, pattern=r"^[a-z0-9_]{1,48}$")
    model_run_id: str
    benchmark_id: str
    fallback: FallbackConfigInput = Field(default_factory=FallbackConfigInput)


class AgentPackageRead(StrictModel):
    id: str
    agent_id: str
    project_id: str
    model_run_id: str
    benchmark_id: str
    route_catalog_sha256: str
    contract_version: int
    contract_yaml: str
    contract_sha256: str
    created_at: str


class AgentPackagePage(StrictModel):
    items: list[AgentPackageRead]
    next_cursor: str | None = None
