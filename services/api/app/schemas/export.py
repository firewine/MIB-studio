from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.schemas.job import JobStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportParams(StrictModel):
    agent_package_id: str
    export_type: Literal["zip", "docker"]


class ExportRead(StrictModel):
    id: str
    job_id: str
    agent_package_id: str
    export_type: Literal["zip", "docker"]
    status: JobStatus
    manifest_path: str | None = None
    manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_path: str | None = None
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_url: str | None = None
    reveal_url: str | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class RevealExportResponse(StrictModel):
    artifact_path: str
    revealed: bool
