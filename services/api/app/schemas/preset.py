from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PresetRead(StrictModel):
    id: str
    name: str
    preset_type: Literal["router"]
    version: int
    schema_refs: dict[str, str]
    config_json: dict[str, Any]
    created_at: str


class PresetPage(StrictModel):
    items: list[PresetRead]
    next_cursor: str | None = None
