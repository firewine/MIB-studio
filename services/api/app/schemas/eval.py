from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


EvalSetPurpose = Literal["teacher_guard", "benchmark_gold", "finance_reference"]


class EvalSetCreate(StrictModel):
    purpose: EvalSetPurpose = "benchmark_gold"
    dataset_id: str
    example_ids: list[str] = Field(min_length=20, max_length=300)
    labeler_ids: list[str] = Field(min_length=1)
    kappa: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def require_eval_quality(self) -> "EvalSetCreate":
        if len(self.example_ids) != len(set(self.example_ids)):
            raise ValueError("eval set example_ids must be unique")
        if self.purpose == "teacher_guard":
            if not 20 <= len(self.example_ids) <= 50:
                raise ValueError("teacher_guard eval set requires 20..50 approved examples")
            return self
        if not 200 <= len(self.example_ids) <= 300:
            raise ValueError("benchmark eval set requires 200..300 approved examples")
        if len(self.labeler_ids) < 3 or self.kappa is None or self.kappa < 0.70:
            raise ValueError("benchmark eval set requires >=3 labelers and Cohen kappa >= 0.70")
        return self


class EvalSetRead(StrictModel):
    id: str
    project_id: str
    dataset_id: str
    purpose: EvalSetPurpose
    version: int
    path: str
    sha256: str
    sample_count: int
    route_snapshot_sha256: str
    labeler_ids_json: list[str]
    kappa: float | None = None
    frozen_at: str
    created_at: str


class EvalSetPage(StrictModel):
    items: list[EvalSetRead]
    next_cursor: str | None = None
