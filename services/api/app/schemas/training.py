from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
Backend = Literal["cuda", "mlx"]
ModelId = Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"]
TrainingMethod = Literal["qlora", "mlx_lora"]


class ModelRunRead(StrictModel):
    id: str
    job_id: str | None = None
    project_id: str
    dataset_id: str
    base_model: ModelId
    backend: Backend
    method: TrainingMethod
    adapter_path: str | None = None
    adapter_sha256: str | None = None
    artifact_manifest_sha256: str | None = None
    status: JobStatus
    seed: int
    config_hash: str
    best_checkpoint_id: str | None = None
    resumable: bool
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str


class ModelRunPage(StrictModel):
    items: list[ModelRunRead]
    next_cursor: str | None = None
