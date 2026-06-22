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
    hard_negative_min_count: int = Field(default=40, ge=0, le=5000)

    @model_validator(mode="after")
    def require_teacher_approval(self) -> "DatasetGenParams":
        if self.generation_mode == "teacher_synthetic" and not self.teacher_packet_approval_id:
            raise ValueError("teacher_packet_approval_id is required for teacher_synthetic")
        if self.hard_negative_min_count > self.target_count:
            raise ValueError("hard_negative_min_count must not exceed target_count")
        return self


class TrainParams(StrictModel):
    preset_id: str = "router.basic.v1"
    dataset_id: str
    base_model: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"]
    backend: Literal["cuda", "mlx"]
    training_preset: Literal["quick", "balanced", "production"] = "balanced"
    seed: int = 42


class BenchmarkTargetConfig(StrictModel):
    target_key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    target_type: Literal["prompt_only", "fine_tuned", "teacher", "rule_based", "local_large"]
    backend: Literal["cuda", "mlx", "teacher", "rule_based", "prompt_only", "local_large"]
    model_run_id: str | None = None
    base_model: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"] | None = None
    prompt_template_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    credential_id: str | None = None
    teacher_base_url_origin: str | None = None
    routing_rules_path: str | None = None
    routing_rules_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    local_large_config: dict[str, Any] | None = None
    required: bool = True


class BenchmarkParams(StrictModel):
    eval_set_id: str
    targets: list[BenchmarkTargetConfig] = Field(min_length=1, max_length=6)
    seeds: list[int] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def require_stable_target_and_seed_keys(self) -> "BenchmarkParams":
        target_keys = [target.target_key for target in self.targets]
        if len(target_keys) != len(set(target_keys)):
            raise ValueError("benchmark target_key values must be unique")
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("benchmark seeds must be unique")
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


class JobControlResponse(StrictModel):
    job_id: str
    status: JobStatus
    events_url: str
    cancel_requested: bool = False
    child_job_id: str | None = None


class ResumeJobRequest(StrictModel):
    checkpoint_id: str
