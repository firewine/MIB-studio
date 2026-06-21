from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.job import JobControlResponse, ResumeJobRequest
from services.shared.db.models import AuditEvent, Checkpoint, Dataset, Job, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, new_id
from services.shared.db.repositories.training_store import TrainingStore


class JobControlService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home
        self.store = TrainingStore(session)

    def cancel_job(self, job_id: str) -> JobControlResponse:
        job = self._job_or_404(job_id)
        if job.status == "QUEUED":
            model_run = self._model_run_for_job(job)
            self.store.mark_cancelled(job=job, model_run=model_run, ts=utc_now())
            return self._response(job)
        if job.status == "RUNNING":
            if job.cancel_requested_at is not None:
                raise APIError(
                    "JOB_CANCEL_ALREADY_REQUESTED",
                    "Cancel has already been requested for this job.",
                    status_code=409,
                    details={"job_id": job.id},
                )
            self.store.request_cancel(job=job, ts=utc_now())
            return self._response(job)
        raise APIError(
            "JOB_NOT_CANCELLABLE",
            "Only QUEUED or RUNNING jobs can be cancelled.",
            status_code=409,
            details={"job_id": job.id, "status": job.status},
        )

    def resume_job(self, job_id: str, payload: ResumeJobRequest, *, trace_id: str) -> JobControlResponse:
        parent = self._job_or_404(job_id)
        if parent.type != "train" or parent.status not in {"FAILED", "INTERRUPTED"}:
            raise APIError(
                "JOB_NOT_RESUMABLE",
                "Only FAILED or INTERRUPTED train jobs can be resumed.",
                status_code=409,
                details={"job_id": parent.id, "status": parent.status},
            )
        model_run = self._required_model_run_for_job(parent)
        checkpoint = self._checkpoint_or_404(payload.checkpoint_id)
        self._validate_checkpoint(checkpoint, model_run)
        optimizer_rng_missing = self._optimizer_rng_missing(checkpoint)

        ts = utc_now()
        child = self._create_resume_child(parent, model_run, checkpoint, ts=ts, trace_id=trace_id)
        self.store.rebind_model_run_job(model_run=model_run, child_job=child, ts=ts)
        model_run.status = "QUEUED"
        model_run.ended_at = None
        model_run.resumable = 1
        self.store.append_event(
            job=child,
            ts=ts,
            level="info",
            event_type="status_change",
            payload={
                "status": "QUEUED",
                "phase": "resume_started",
                "parent_job_id": parent.id,
                "model_run_id": model_run.id,
                "checkpoint_id": checkpoint.id,
                "optimizer_rng_missing": optimizer_rng_missing,
            },
        )
        self._audit_resume(
            child_job=child,
            parent_job=parent,
            model_run=model_run,
            checkpoint=checkpoint,
            optimizer_rng_missing=optimizer_rng_missing,
            ts=ts,
            trace_id=trace_id,
        )
        self.session.flush()
        return self._response(parent, child_job_id=child.id)

    def _job_or_404(self, job_id: str) -> Job:
        job = self.session.get(Job, job_id)
        if job is None:
            raise APIError("JOB_NOT_FOUND", "Job does not exist.", status_code=404, details={"job_id": job_id})
        return job

    def _checkpoint_or_404(self, checkpoint_id: str) -> Checkpoint:
        checkpoint = self.session.get(Checkpoint, checkpoint_id)
        if checkpoint is None:
            raise APIError(
                "CHECKPOINT_NOT_FOUND",
                "Checkpoint does not exist.",
                status_code=404,
                details={"checkpoint_id": checkpoint_id},
            )
        return checkpoint

    def _model_run_for_job(self, job: Job) -> ModelRun | None:
        model_run_id = self.store.model_run_id_for_job(job.id)
        if model_run_id is None:
            return None
        return self.session.get(ModelRun, model_run_id)

    def _required_model_run_for_job(self, job: Job) -> ModelRun:
        model_run = self._model_run_for_job(job)
        if model_run is None:
            raise APIError(
                "JOB_NOT_RESUMABLE",
                "Train job is not linked to a ModelRun.",
                status_code=409,
                details={"job_id": job.id},
            )
        return model_run

    def _validate_checkpoint(self, checkpoint: Checkpoint, model_run: ModelRun) -> None:
        dataset = self.session.get(Dataset, model_run.dataset_id)
        if dataset is None:
            raise APIError(
                "DATASET_NOT_FOUND",
                "ModelRun dataset does not exist.",
                status_code=409,
                details={"model_run_id": model_run.id, "dataset_id": model_run.dataset_id},
            )
        if checkpoint.model_run_id != model_run.id or checkpoint.dataset_id != model_run.dataset_id:
            raise APIError(
                "CHECKPOINT_DATASET_MISMATCH",
                "Checkpoint dataset does not match the ModelRun dataset.",
                status_code=409,
                details={
                    "checkpoint_id": checkpoint.id,
                    "expected_dataset_id": model_run.dataset_id,
                    "actual_dataset_id": checkpoint.dataset_id,
                },
            )
        if checkpoint.dataset_version != dataset.version:
            raise APIError(
                "CHECKPOINT_DATASET_MISMATCH",
                "Checkpoint dataset version does not match the current dataset version.",
                status_code=409,
                details={
                    "checkpoint_id": checkpoint.id,
                    "expected_dataset_version": dataset.version,
                    "actual_dataset_version": checkpoint.dataset_version,
                },
            )
        if checkpoint.training_config_hash != model_run.config_hash:
            raise APIError(
                "CHECKPOINT_CONFIG_MISMATCH",
                "Checkpoint training config hash does not match the ModelRun config hash.",
                status_code=409,
                details={
                    "checkpoint_id": checkpoint.id,
                    "expected_config_hash": model_run.config_hash,
                    "actual_config_hash": checkpoint.training_config_hash,
                },
            )
        checkpoint_path = Path(checkpoint.path)
        if not checkpoint_path.exists() or not (checkpoint_path / "manifest.json").is_file():
            raise APIError(
                "CHECKPOINT_ARTIFACT_MISSING",
                "Checkpoint artifact is missing.",
                status_code=409,
                details={"checkpoint_id": checkpoint.id, "path": checkpoint.path},
            )

    def _optimizer_rng_missing(self, checkpoint: Checkpoint) -> bool:
        metrics = json.loads(checkpoint.metrics_json)
        return not bool(metrics.get("optimizer_state_present")) or not bool(metrics.get("rng_state_present"))

    def _create_resume_child(self, parent: Job, model_run: ModelRun, checkpoint: Checkpoint, *, ts: str, trace_id: str) -> Job:
        params = json.loads(parent.params_json)
        params["model_run_id"] = model_run.id
        params["checkpoint_id"] = checkpoint.id
        params["resume_from_checkpoint_path"] = checkpoint.path
        child = Job(
            id=new_id(),
            project_id=parent.project_id,
            type=parent.type,
            resource_class=parent.resource_class,
            status="QUEUED",
            priority=parent.priority,
            params_json=canonical_json(params),
            attempt_count=parent.attempt_count + 1,
            parent_job_id=parent.id,
            eval_set_id=parent.eval_set_id,
            preset_version=parent.preset_version,
            trace_id=trace_id,
            created_at=ts,
        )
        self.session.add(child)
        self.session.flush()
        return child

    def _audit_resume(
        self,
        *,
        child_job: Job,
        parent_job: Job,
        model_run: ModelRun,
        checkpoint: Checkpoint,
        optimizer_rng_missing: bool,
        ts: str,
        trace_id: str,
    ) -> None:
        details = {
            "parent_job_id": parent_job.id,
            "checkpoint_id": checkpoint.id,
            "model_run_id": model_run.id,
            "optimizer_rng_missing": optimizer_rng_missing,
        }
        self.session.add(
            AuditEvent(
                id=new_id(),
                ts=ts,
                event_type="job_control",
                resource_type="job",
                resource_id=child_job.id,
                action="resume",
                policy_version="M3-004",
                details_json=canonical_json(details),
                trace_id=trace_id,
                retention_until=format_ts(datetime.now(UTC) + timedelta(days=365)),
                created_at=ts,
            )
        )
        self.session.flush()

    def _response(self, job: Job, *, child_job_id: str | None = None) -> JobControlResponse:
        return JobControlResponse(
            job_id=job.id,
            status=job.status,  # type: ignore[arg-type]
            cancel_requested=job.cancel_requested_at is not None,
            child_job_id=child_job_id,
            events_url=f"/jobs/{job.id}/events",
        )


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
