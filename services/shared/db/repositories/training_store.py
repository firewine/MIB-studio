from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from services.shared.db.models import Job, JobEvent, JobResource, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, new_id, sha256_text


@dataclass(frozen=True)
class TrainingRunInput:
    project_id: str
    dataset_id: str
    base_model: str
    backend: str
    method: str
    seed: int
    config: dict[str, Any]
    job_params: dict[str, Any]
    idempotency_key: str | None
    idempotency_body_sha256: str | None
    idempotency_expires_at: str | None
    trace_id: str
    created_at: str


@dataclass(frozen=True)
class TrainingRunRows:
    model_run: ModelRun
    job: Job
    job_resource: JobResource


class TrainingStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_queued_training_run(self, payload: TrainingRunInput) -> TrainingRunRows:
        model_run_id = new_id()
        job_id = new_id()
        config_json = canonical_json(payload.config)
        job_params = dict(payload.job_params)
        job_params["model_run_id"] = model_run_id
        model_run = ModelRun(
            id=model_run_id,
            project_id=payload.project_id,
            dataset_id=payload.dataset_id,
            base_model=payload.base_model,
            backend=payload.backend,
            method=payload.method,
            status="QUEUED",
            seed=payload.seed,
            config_json=config_json,
            config_hash=sha256_text(config_json),
            resumable=0,
            created_at=payload.created_at,
        )
        job = Job(
            id=job_id,
            project_id=payload.project_id,
            type="train",
            resource_class="gpu_exclusive",
            status="QUEUED",
            priority=0,
            params_json=canonical_json(job_params),
            idempotency_key=payload.idempotency_key,
            idempotency_body_sha256=payload.idempotency_body_sha256,
            idempotency_expires_at=payload.idempotency_expires_at,
            attempt_count=0,
            trace_id=payload.trace_id,
            created_at=payload.created_at,
        )
        resource = JobResource(
            job_id=job_id,
            resource_type="model_run",
            resource_id=model_run_id,
            is_current=1,
            created_at=payload.created_at,
        )
        self.session.add_all([model_run, job, resource])
        self.session.flush()
        return TrainingRunRows(model_run=model_run, job=job, job_resource=resource)

    def current_job_id_for_model_run(self, model_run_id: str) -> str | None:
        statement = select(JobResource).where(
            JobResource.resource_type == "model_run",
            JobResource.resource_id == model_run_id,
            JobResource.is_current == 1,
        )
        row = self.session.scalars(statement).first()
        return row.job_id if row is not None else None

    def mark_running(self, *, job: Job, model_run: ModelRun, ts: str) -> None:
        job.status = "RUNNING"
        job.started_at = job.started_at or ts
        job.attempt_count = job.attempt_count + 1
        model_run.status = "RUNNING"
        model_run.started_at = model_run.started_at or ts
        self.append_event(job=job, ts=ts, level="info", event_type="status_change", payload={"status": "RUNNING"})
        self.session.flush()

    def mark_succeeded(
        self,
        *,
        job: Job,
        model_run: ModelRun,
        adapter_path: str,
        adapter_sha256: str,
        artifact_manifest_sha256: str,
        ts: str,
    ) -> None:
        model_run.status = "SUCCEEDED"
        model_run.adapter_path = adapter_path
        model_run.adapter_sha256 = adapter_sha256
        model_run.artifact_manifest_sha256 = artifact_manifest_sha256
        model_run.resumable = 1
        model_run.ended_at = ts
        job.status = "SUCCEEDED"
        job.ended_at = ts
        self.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="artifact",
            payload={
                "phase": "completed",
                "model_run_id": model_run.id,
                "adapter_sha256": adapter_sha256,
                "artifact_manifest_sha256": artifact_manifest_sha256,
            },
        )
        self.session.flush()

    def mark_failed(self, *, job: Job, model_run: ModelRun, error_class: str, error_message: str, ts: str) -> None:
        job.status = "FAILED"
        job.error_class = error_class
        job.error_message = error_message
        job.ended_at = ts
        model_run.status = "FAILED"
        model_run.ended_at = ts
        self.append_event(
            job=job,
            ts=ts,
            level="error",
            event_type="error",
            payload={"phase": "failed", "model_run_id": model_run.id, "error_class": error_class, "message": error_message},
        )
        self.session.flush()

    def append_event(self, *, job: Job, ts: str, level: str, event_type: str, payload: dict[str, Any]) -> None:
        next_seq = int(self.session.scalar(select(func.max(JobEvent.seq)).where(JobEvent.job_id == job.id)) or 0) + 1
        self.session.add(
            JobEvent(
                id=new_id(),
                job_id=job.id,
                seq=next_seq,
                ts=ts,
                level=level,
                event_type=event_type,
                payload_json=canonical_json(payload),
                trace_id=job.trace_id,
            )
        )
        self.session.flush()

    def list_model_runs(
        self,
        project_id: str,
        *,
        cursor: str | None,
        limit: int,
        status: str | None,
        backend: str | None,
    ) -> list[ModelRun]:
        statement: Select[tuple[ModelRun]] = select(ModelRun).where(ModelRun.project_id == project_id)
        if status:
            statement = statement.where(ModelRun.status == status)
        if backend:
            statement = statement.where(ModelRun.backend == backend)
        if cursor:
            cursor_created_at, cursor_id = json.loads(cursor)
            statement = statement.where(
                (ModelRun.created_at < cursor_created_at)
                | ((ModelRun.created_at == cursor_created_at) & (ModelRun.id < cursor_id))
            )
        statement = statement.order_by(ModelRun.created_at.desc(), ModelRun.id.desc()).limit(limit + 1)
        return list(self.session.scalars(statement))
