from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


RouterExamplePayload = dict[str, Any]
DatasetStatus = Literal["DRAFT", "BUILT", "REVIEWED", "APPROVED", "ARCHIVED"]
ExampleSource = Literal["user", "import", "teacher", "hard_negative", "eval_gold"]


class ExampleInput(StrictModel):
    input: RouterExamplePayload
    output: RouterExamplePayload
    source: Literal["user", "import"] = "user"


class DatasetBuildRequest(StrictModel):
    examples: list[ExampleInput] = Field(min_length=20)
    status: Literal["DRAFT", "BUILT"] = "BUILT"


class DatasetPatch(StrictModel):
    status: DatasetStatus | None = None
    approved_example_ids: list[str] | None = None

    @model_validator(mode="after")
    def require_change(self) -> "DatasetPatch":
        if self.status is None and self.approved_example_ids is None:
            raise ValueError("at least one dataset field must change")
        return self


class ExamplePatch(StrictModel):
    input: RouterExamplePayload | None = None
    output: RouterExamplePayload | None = None
    review_status: Literal["PENDING", "APPROVED", "REJECTED", "EDITED"] | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ExamplePatch":
        if self.input is None and self.output is None and self.review_status is None:
            raise ValueError("at least one example field must change")
        return self


class RowValidationError(StrictModel):
    field: str
    code: str
    message: str


class ExampleRead(StrictModel):
    id: str
    dataset_id: str
    source: ExampleSource
    input: RouterExamplePayload
    output: RouterExamplePayload
    review_status: Literal["PENDING", "APPROVED", "REJECTED", "EDITED"]
    approved: bool
    validation_errors: list[RowValidationError] = Field(default_factory=list)
    created_at: str


class DatasetRead(StrictModel):
    id: str
    project_id: str
    version: int
    status: DatasetStatus
    path: str
    sample_count: int
    sha256: str
    schema_version: str
    route_snapshot_sha256: str
    created_at: str
    frozen_at: str | None = None


class DatasetWithExamples(DatasetRead):
    examples: list[ExampleRead]
    next_cursor: str | None = None


class DatasetPage(StrictModel):
    items: list[DatasetRead]
    next_cursor: str | None = None
