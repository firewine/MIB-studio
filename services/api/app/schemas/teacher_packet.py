from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TeacherPacketPreviewRequest(StrictModel):
    dataset_id: str
    example_ids: list[str] = Field(min_length=20, max_length=50)
    instruction: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def require_unique_examples(self) -> "TeacherPacketPreviewRequest":
        if len(self.example_ids) != len(set(self.example_ids)):
            raise ValueError("teacher packet example_ids must be unique")
        return self


class TeacherPacketPreviewRead(StrictModel):
    id: str
    project_id: str
    packet_sha256: str
    packet_preview: dict[str, Any]
    pii_summary: dict[str, Any]
    expires_at: str
    approved_at: str | None = None


class TeacherPacketApprovalRead(StrictModel):
    approval_id: str
    project_id: str
    packet_sha256: str
    approved_at: str
    expires_at: str
