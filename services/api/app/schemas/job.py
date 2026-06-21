from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
CreatedResourceType = Literal["model_run", "benchmark", "export", "hardware_scan", "dataset", "none"]


class DatasetGenParams(StrictModel):
    dataset_id: str | None = None
    generation_mode: Literal["build_from_user_examples", "teacher_synthetic"]
    teacher_packet_approval_id: str | None = None
    packet_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    target_count: int = Field(default=200, ge=20, le=5000)

    @model_validator(mode="after")
    def require_teacher_approval(self) -> "DatasetGenParams":
        if self.generation_mode == "teacher_synthetic" and not self.teacher_packet_approval_id:
            raise ValueError("teacher_packet_approval_id is required for teacher_synthetic")
        return self


class JobSubmitRequest(StrictModel):
    type: Literal["dataset_gen", "train", "eval", "benchmark"]
    params: dict[str, Any]


class JobAcceptedResponse(StrictModel):
    job_id: str
    status: JobStatus
    type: str
    events_url: str
    created_resource_type: CreatedResourceType = "none"
    created_resource_id: str | None = None
    idempotency_replayed: bool = False
