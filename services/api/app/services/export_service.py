from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.export import ExportParams, ExportRead
from services.api.app.schemas.job import JobAcceptedResponse
from services.shared.db.models import AgentPackage, ExportArtifact, Job, Project
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.repositories.export_store import ExportJobInput, ExportStore


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class ExportService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home
        self.store = ExportStore(session)

    def submit_export(
        self,
        project_id: str,
        payload: ExportParams,
        *,
        idempotency_key: str | None,
        trace_id: str,
    ) -> JobAcceptedResponse:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})
        package = self._package_or_404(payload.agent_package_id)
        if package.project_id != project_id:
            raise APIError("EXPORT_PROJECT_MISMATCH", "AgentPackage does not belong to the requested project.", status_code=409)
        if payload.export_type != "zip":
            raise APIError("MILESTONE_LOCKED", "Docker export is implemented in M6-002.", status_code=409, details={"export_type": payload.export_type})

        body_hash = sha256_text(canonical_json(payload.model_dump()))
        if idempotency_key:
            existing = self._job_by_project_idempotency_key(project_id, idempotency_key)
            if existing is not None:
                if existing.idempotency_body_sha256 != body_hash:
                    raise APIError("IDEMPOTENCY_CONFLICT", "Idempotency-Key was already used with a different export request.", status_code=409)
                return self._accepted_response(existing, idempotency_replayed=True)

        now = utc_now()
        rows = self.store.create_queued_export(
            ExportJobInput(
                project_id=project_id,
                agent_package_id=package.id,
                export_type=payload.export_type,
                job_params=payload.model_dump(),
                idempotency_key=idempotency_key,
                idempotency_body_sha256=body_hash if idempotency_key else None,
                idempotency_expires_at=_format_ts(datetime.now(UTC) + timedelta(hours=24)) if idempotency_key else None,
                trace_id=trace_id,
                created_at=now,
            )
        )
        return self._accepted_response(rows.job, idempotency_replayed=False)

    def get_export(self, job_id: str) -> ExportRead:
        return self._read_export(self._export_for_job_or_error(job_id))

    def artifact_path(self, job_id: str) -> Path:
        export = self._succeeded_export_or_409(job_id)
        return self._verified_artifact_path(export)

    def reveal_export(self, job_id: str) -> Path:
        return self.artifact_path(job_id)

    def _succeeded_export_or_409(self, job_id: str) -> ExportArtifact:
        export = self._export_for_job_or_error(job_id)
        if export.status != "SUCCEEDED" or not export.artifact_path or not export.artifact_sha256:
            raise APIError("EXPORT_NOT_READY", "Export artifact is not ready.", status_code=409, details={"job_id": job_id, "status": export.status})
        return export

    def _verified_artifact_path(self, export: ExportArtifact) -> Path:
        path = Path(str(export.artifact_path))
        if not path.is_file():
            raise APIError("EXPORT_ARTIFACT_MISSING", "Export artifact file is missing.", status_code=500, details={"job_id": export.job_id})
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != export.artifact_sha256:
            raise APIError(
                "EXPORT_HASH_MISMATCH",
                "Export artifact hash does not match.",
                status_code=409,
                details={"job_id": export.job_id, "expected_sha256": export.artifact_sha256, "actual_sha256": actual},
            )
        return path

    def _export_for_job_or_error(self, job_id: str) -> ExportArtifact:
        job = self.session.get(Job, job_id)
        export = self.store.artifact_for_job(job_id)
        if export is not None:
            return export
        if job is not None and job.type == "export":
            raise APIError("EXPORT_ARTIFACT_MISSING", "ExportArtifact row is missing for export job.", status_code=500, details={"job_id": job_id})
        raise APIError("EXPORT_NOT_FOUND", "Export does not exist.", status_code=404, details={"job_id": job_id})

    def _read_export(self, export: ExportArtifact) -> ExportRead:
        ready = export.status == "SUCCEEDED" and export.artifact_path and export.artifact_sha256
        return ExportRead(
            id=export.id,
            job_id=export.job_id,
            agent_package_id=export.agent_package_id,
            export_type=export.export_type,  # type: ignore[arg-type]
            status=export.status,  # type: ignore[arg-type]
            manifest_path=export.manifest_path,
            manifest_sha256=export.manifest_sha256,
            artifact_path=export.artifact_path,
            artifact_sha256=export.artifact_sha256,
            artifact_url=f"/exports/{export.job_id}/artifact" if ready else None,
            reveal_url=f"/exports/{export.job_id}/reveal" if ready else None,
            error_message=export.error_message,
            created_at=export.created_at,
            completed_at=export.completed_at,
        )

    def _accepted_response(self, job: Job, *, idempotency_replayed: bool) -> JobAcceptedResponse:
        return JobAcceptedResponse(
            job_id=job.id,
            status=job.status,  # type: ignore[arg-type]
            type=job.type,
            events_url=f"/jobs/{job.id}/events",
            created_resource_type="export",
            created_resource_id=self.store.artifact_for_job(job.id).id if self.store.artifact_for_job(job.id) is not None else None,
            idempotency_replayed=idempotency_replayed,
        )

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _package_or_404(self, package_id: str) -> AgentPackage:
        package = self.session.get(AgentPackage, package_id)
        if package is None:
            raise APIError("AGENT_PACKAGE_NOT_FOUND", "AgentPackage does not exist.", status_code=404, details={"package_id": package_id})
        return package

    def _job_by_project_idempotency_key(self, project_id: str, idempotency_key: str) -> Job | None:
        statement = select(Job).where(Job.project_id == project_id, Job.idempotency_key == idempotency_key).limit(1)
        return self.session.scalars(statement).first()


def _format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
