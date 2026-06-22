from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.db.models import Job, JobEvent, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, new_id


class TrainingStatusStore:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    def mark_dry_run_succeeded(
        self,
        *,
        job: Job,
        model_run: ModelRun,
        report_path: str,
        report_sha256: str,
        report: dict[str, Any],
        ts: str,
    ) -> None:
        model_run.status = "SUCCEEDED"
        model_run.resumable = 0
        model_run.ended_at = ts
        job.status = "SUCCEEDED"
        job.ended_at = ts
        self.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="artifact",
            payload={
                "phase": "dry_run_completed",
                "model_run_id": model_run.id,
                "dry_run_report_path": report_path,
                "dry_run_report_sha256": report_sha256,
                "predicted_vram_peak_mb": report["predicted_vram_peak_mb"],
                "observed_vram_peak_mb": report["observed_vram_peak_mb"],
                "tokens_per_sec": report["tokens_per_sec"],
                "predicted_duration_seconds": report["predicted_duration_seconds"],
                "estimate_error_pct": report["estimate_error_pct"],
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

    def mark_cancelled(self, *, job: Job, model_run: ModelRun | None, ts: str) -> None:
        job.status = "CANCELLED"
        job.ended_at = ts
        if model_run is not None:
            model_run.status = "CANCELLED"
            model_run.ended_at = ts
        self.append_event(job=job, ts=ts, level="info", event_type="status_change", payload={"status": "CANCELLED"})
        self.session.flush()

    def request_cancel(self, *, job: Job, ts: str) -> None:
        job.cancel_requested_at = ts
        self.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="status_change",
            payload={"status": job.status, "cancel_requested": True},
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
