from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RouteInput(StrictModel):
    route_id: str = Field(pattern=r"^[a-z0-9_]+$", min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    is_unsafe: bool = False


def ensure_unique_routes(routes: list[RouteInput] | None) -> list[RouteInput] | None:
    if routes is None:
        return None
    route_ids = [route.route_id for route in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("route_id values must be unique")
    return routes


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    preset_id: str = "router.basic.v1"
    routes: list[RouteInput] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def validate_routes(self) -> "ProjectCreate":
        ensure_unique_routes(self.routes)
        return self


class ProjectPatch(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    routes: list[RouteInput] | None = Field(default=None, min_length=2, max_length=12)

    @model_validator(mode="after")
    def validate_routes(self) -> "ProjectPatch":
        ensure_unique_routes(self.routes)
        return self


class RouteRead(StrictModel):
    id: str
    route_id: str
    description: str
    is_unsafe: bool
    created_at: str


class ProjectRead(StrictModel):
    id: str
    name: str
    preset_id: str
    routes: list[RouteRead]
    archived_at: str | None = None
    route_taxonomy_locked: bool = False
    created_at: str
    updated_at: str


class ProjectPage(StrictModel):
    items: list[ProjectRead]
    next_cursor: str | None = None


class HealthRead(StrictModel):
    status: Literal["ok"]
    version: str
