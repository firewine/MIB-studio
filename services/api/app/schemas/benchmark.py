from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


BenchmarkStatus = Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"]
HashStatus = Literal["VALID", "MISMATCH", "MISSING"]
ParityStatus = Literal["PASS", "FAIL", "NA"]


class BenchmarkRead(StrictModel):
    id: str
    project_id: str
    job_id: str
    eval_set_id: str
    status: BenchmarkStatus
    report_sha256: str | None = None
    hash_status: HashStatus = "MISSING"
    parity_status: ParityStatus
    created_at: str
    completed_at: str | None = None


class BenchmarkPage(StrictModel):
    items: list[BenchmarkRead]
    next_cursor: str | None = None


class BenchmarkReportRead(StrictModel):
    benchmark_id: str
    report_sha256: str | None = None
    hash_status: HashStatus
    report: dict[str, Any] | None = None
