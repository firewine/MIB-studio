from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.db.models import ExportArtifact, Job, JobEvent, JobResource
from services.shared.db.repositories.dataset_store import canonical_json, new_id


@dataclass(frozen=True)
class ExportJobInput:
    project_id: str
    agent_package_id: str
    export_type: str
    job_params: dict[str, Any]
    idempotency_key: str | None
    idempotency_body_sha256: str | None
    idempotency_expires_at: str | None
    trace_id: str
    created_at: str


@dataclass(frozen=True)
class ExportJobRows:
    export_artifact: ExportArtifact
    job: Job
    job_resource: JobResource


class ExportStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_queued_export(self, payload: ExportJobInput) -> ExportJobRows:
        export_id = new_id()
        job_id = new_id()
        job_params = dict(payload.job_params)
        job_params["export_artifact_id"] = export_id
        job = Job(
            id=job_id,
            project_id=payload.project_id,
            type="export",
            resource_class="cpu_shared",
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
        export = ExportArtifact(
            id=export_id,
            job_id=job_id,
            agent_package_id=payload.agent_package_id,
            export_type=payload.export_type,
            status="QUEUED",
            created_at=payload.created_at,
        )
        resource = JobResource(
            job_id=job_id,
            resource_type="export_artifact",
            resource_id=export_id,
            is_current=1,
            created_at=payload.created_at,
        )
        self.session.add_all([job, export, resource])
        self.session.flush()
        return ExportJobRows(export_artifact=export, job=job, job_resource=resource)

    def artifact_for_job(self, job_id: str) -> ExportArtifact | None:
        return self.session.scalars(select(ExportArtifact).where(ExportArtifact.job_id == job_id).limit(1)).first()

    def mark_running(self, *, job: Job, export: ExportArtifact, ts: str) -> None:
        job.status = "RUNNING"
        job.started_at = job.started_at or ts
        job.attempt_count = job.attempt_count + 1
        export.status = "RUNNING"
        self.append_event(job=job, ts=ts, level="info", event_type="status_change", payload={"status": "RUNNING"})
        self.session.flush()

    def mark_succeeded(
        self,
        *,
        job: Job,
        export: ExportArtifact,
        manifest_path: str,
        manifest_sha256: str,
        artifact_path: str,
        artifact_sha256: str,
        ts: str,
    ) -> None:
        export.status = "SUCCEEDED"
        export.manifest_path = manifest_path
        export.manifest_sha256 = manifest_sha256
        export.artifact_path = artifact_path
        export.artifact_sha256 = artifact_sha256
        export.completed_at = ts
        job.status = "SUCCEEDED"
        job.ended_at = ts
        self.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="artifact",
            payload={
                "phase": "completed",
                "export_artifact_id": export.id,
                "agent_package_id": export.agent_package_id,
                "export_type": export.export_type,
                "manifest_sha256": manifest_sha256,
                "artifact_sha256": artifact_sha256,
            },
        )
        self.session.flush()

    def mark_failed(self, *, job: Job, export: ExportArtifact, error_message: str, ts: str) -> None:
        job.status = "FAILED"
        job.error_class = "UNKNOWN"
        job.error_message = error_message
        job.ended_at = ts
        export.status = "FAILED"
        export.error_message = error_message
        export.completed_at = ts
        self.append_event(job=job, ts=ts, level="error", event_type="error", payload={"phase": "failed", "message": error_message})
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
