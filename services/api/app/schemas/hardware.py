from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
CreatedResourceType = Literal["model_run", "benchmark", "export", "hardware_scan", "dataset", "none"]
Backend = Literal["cuda", "mlx", "auto"]
GpuVendor = Literal["nvidia", "apple", "amd", "intel", "none", "unknown"]
BackendRecommendation = Literal["cuda", "mlx", "cpu", "unsupported"]
TrainingDisabledReason = Literal["NO_GPU", "LOW_VRAM", "UNSUPPORTED_VENDOR", "MISSING_DRIVER", "PYTHON_UNSUPPORTED", "NONE"]


class HardwareScanRequest(StrictModel):
    dry_run: bool = True
    target_backend: Backend = "auto"


class JobAcceptedResponse(StrictModel):
    job_id: str
    status: JobStatus
    type: str
    events_url: str
    created_resource_type: CreatedResourceType = "none"
    created_resource_id: str | None = None
    idempotency_replayed: bool = False


class HardwareProfileRead(StrictModel):
    id: str
    machine_id: str
    os: str
    cpu: str | None = None
    gpu_vendor: GpuVendor
    gpu_name: str | None = None
    vram_gb: float | None = None
    unified_ram_gb: float | None = None
    ram_gb: float
    cuda_status: Literal["ok", "missing", "unsupported", "na"] | None = None
    mlx_status: Literal["ok", "missing", "unsupported", "na"] | None = None
    capability_gate: Literal["G0", "G1", "G2"]
    backend_recommendation: BackendRecommendation
    training_enabled: bool
    training_disabled_reason_code: TrainingDisabledReason
    training_disabled_reason_message: str
    allowed_backends: list[Literal["cuda", "mlx"]]
    unlock_requirements: list[str]
    dry_run_result_json: dict[str, Any]
    created_at: str
