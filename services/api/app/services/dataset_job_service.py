from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from services.api.app.core.errors import APIError, json_safe_errors
from services.api.app.schemas.job import BenchmarkParams, DatasetGenParams, JobAcceptedResponse, JobSubmitRequest
from services.shared.db.models import Benchmark, Credential, Dataset, EvalSet, Job, JobResource, ModelRun, TeacherPacketApproval
from services.shared.db.repositories.dataset_store import canonical_json, new_id, sha256_text


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class DatasetJobServiceMixin:
    def submit_project_job(
        self,
        project_id: str,
        payload: JobSubmitRequest,
        *,
        idempotency_key: str | None,
        trace_id: str,
    ) -> JobAcceptedResponse:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})

        body_hash = sha256_text(canonical_json(payload.model_dump()))
        if idempotency_key:
            existing = self._job_by_project_idempotency_key(project_id, idempotency_key)
            if existing is not None:
                if existing.idempotency_body_sha256 != body_hash:
                    raise APIError(
                        "IDEMPOTENCY_CONFLICT",
                        "Idempotency-Key was already used with a different project job request.",
                        status_code=409,
                        details={"idempotency_key": idempotency_key},
                    )
                return self._accepted_response(existing, idempotency_replayed=True)

        if payload.type == "benchmark":
            return self._submit_benchmark_job(
                project_id,
                payload,
                idempotency_key=idempotency_key,
                idempotency_body_sha256=body_hash if idempotency_key else None,
                trace_id=trace_id,
            )

        if payload.type != "dataset_gen":
            raise APIError(
                "MILESTONE_LOCKED",
                "This job type is locked until its implementation milestone.",
                status_code=409,
                details={"type": payload.type, "current_milestone": "M2-003"},
            )

        params = self._dataset_gen_params(payload.params)
        if params.generation_mode != "teacher_synthetic":
            raise APIError(
                "MILESTONE_LOCKED",
                "build_from_user_examples jobs are not used by M2-003; use the synchronous dataset endpoint.",
                status_code=409,
                details={"generation_mode": params.generation_mode, "current_milestone": "M2-003"},
            )

        approval = self._teacher_packet_ready(params.teacher_packet_approval_id or "")
        dataset = self._dataset_or_404(approval.dataset_id)
        if dataset.project_id != project_id:
            raise APIError(
                "DATASET_PROJECT_MISMATCH",
                "Teacher Packet approval does not belong to the requested project.",
                status_code=409,
                details={"project_id": project_id, "dataset_id": dataset.id},
            )
        if params.dataset_id is not None and params.dataset_id != dataset.id:
            raise APIError(
                "DATASET_PROJECT_MISMATCH",
                "Dataset id does not match the approved Teacher Packet dataset.",
                status_code=409,
                details={"request_dataset_id": params.dataset_id, "approval_dataset_id": dataset.id},
            )
        if dataset.status != "APPROVED":
            raise APIError(
                "DATASET_NOT_APPROVED",
                "Teacher synthetic generation requires an approved source dataset.",
                status_code=409,
                details={"dataset_id": dataset.id, "status": dataset.status},
            )

        packet_sha256 = sha256_text(approval.packet_json)
        if approval.packet_sha256 != packet_sha256:
            raise APIError(
                "TEACHER_PACKET_HASH_MISMATCH",
                "Teacher Packet hash does not match the stored packet snapshot.",
                status_code=409,
                details={"approval_id": approval.id},
            )
        teacher_guard = self._teacher_guard_for_dataset(dataset)
        if teacher_guard is None:
            raise APIError(
                "TEACHER_GUARD_REQUIRED",
                "teacher_synthetic generation requires a frozen teacher_guard EvalSet for this dataset snapshot.",
                status_code=409,
                details={"dataset_id": dataset.id, "route_snapshot_sha256": dataset.route_snapshot_sha256},
            )

        now = utc_now()
        job_params = params.model_dump()
        job_params["dataset_id"] = dataset.id
        job_params["packet_sha256"] = packet_sha256
        job = Job(
            id=new_id(),
            project_id=project_id,
            type="dataset_gen",
            resource_class="cpu_shared",
            status="QUEUED",
            priority=0,
            params_json=canonical_json(job_params),
            idempotency_key=idempotency_key,
            idempotency_body_sha256=body_hash if idempotency_key else None,
            idempotency_expires_at=_format_ts(datetime.now(UTC) + timedelta(hours=24)) if idempotency_key else None,
            attempt_count=0,
            eval_set_id=teacher_guard.id,
            trace_id=trace_id,
            created_at=now,
        )
        self.session.add(job)
        self.session.flush()
        approval.used_job_id = job.id
        self.session.flush()
        return self._accepted_response(job, idempotency_replayed=False)

    def _submit_benchmark_job(
        self,
        project_id: str,
        payload: JobSubmitRequest,
        *,
        idempotency_key: str | None,
        idempotency_body_sha256: str | None,
        trace_id: str,
    ) -> JobAcceptedResponse:
        params = self._benchmark_params(payload.params)
        eval_set = self._benchmark_eval_set(project_id, params.eval_set_id)
        self._validate_benchmark_targets(project_id, params)

        now = utc_now()
        benchmark_id = new_id()
        job_params = params.model_dump()
        job_params["benchmark_id"] = benchmark_id
        job = Job(
            id=new_id(),
            project_id=project_id,
            type="benchmark",
            resource_class="gpu_exclusive",
            status="QUEUED",
            priority=0,
            params_json=canonical_json(job_params),
            idempotency_key=idempotency_key,
            idempotency_body_sha256=idempotency_body_sha256,
            idempotency_expires_at=_format_ts(datetime.now(UTC) + timedelta(hours=24)) if idempotency_key else None,
            attempt_count=0,
            eval_set_id=eval_set.id,
            trace_id=trace_id,
            created_at=now,
        )
        benchmark = Benchmark(
            id=benchmark_id,
            project_id=project_id,
            eval_set_id=eval_set.id,
            job_id=job.id,
            status="QUEUED",
            parity_status="NA",
            created_at=now,
        )
        self.session.add(job)
        self.session.flush()
        resource = JobResource(
            job_id=job.id,
            resource_type="benchmark",
            resource_id=benchmark_id,
            is_current=1,
            created_at=now,
        )
        self.session.add_all([benchmark, resource])
        self.session.flush()
        return self._accepted_response(job, idempotency_replayed=False)

    def _dataset_gen_params(self, raw_params: dict[str, Any]) -> DatasetGenParams:
        try:
            return DatasetGenParams.model_validate(raw_params)
        except ValidationError as exc:
            raise APIError(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status_code=422,
                details={"errors": json_safe_errors(exc.errors())},
            ) from exc

    def _benchmark_params(self, raw_params: dict[str, Any]) -> BenchmarkParams:
        try:
            return BenchmarkParams.model_validate(raw_params)
        except ValidationError as exc:
            raise APIError(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status_code=422,
                details={"errors": json_safe_errors(exc.errors())},
            ) from exc

    def _benchmark_eval_set(self, project_id: str, eval_set_id: str) -> EvalSet:
        eval_set = self.session.get(EvalSet, eval_set_id)
        if eval_set is None:
            raise APIError("EVAL_SET_NOT_FOUND", "EvalSet does not exist.", status_code=404, details={"eval_set_id": eval_set_id})
        if eval_set.project_id != project_id:
            raise APIError(
                "EVAL_SET_PROJECT_MISMATCH",
                "EvalSet does not belong to the requested project.",
                status_code=409,
                details={"project_id": project_id, "eval_set_id": eval_set.id},
            )
        if eval_set.purpose not in {"benchmark_gold", "finance_reference"} or eval_set.sample_count < 200:
            raise APIError(
                "BENCHMARK_EVAL_SET_REQUIRED",
                "Benchmark requires a frozen benchmark-quality EvalSet.",
                status_code=409,
                details={"eval_set_id": eval_set.id, "purpose": eval_set.purpose, "sample_count": eval_set.sample_count},
            )
        return eval_set

    def _validate_benchmark_targets(self, project_id: str, params: BenchmarkParams) -> None:
        by_type: dict[str, list[Any]] = {}
        for target in params.targets:
            by_type.setdefault(target.target_type, []).append(target)

        required_counts = {"prompt_only": 1, "teacher": 1, "rule_based": 1}
        for target_type, expected in required_counts.items():
            actual = len(by_type.get(target_type, []))
            if actual != expected:
                raise APIError(
                    "BENCHMARK_TARGETS_REQUIRED",
                    "Benchmark requires exactly one prompt_only, teacher, and rule_based target.",
                    status_code=422,
                    details={"target_type": target_type, "expected": expected, "actual": actual},
                )

        fine_tuned = by_type.get("fine_tuned", [])
        if not 1 <= len(fine_tuned) <= 2:
            raise APIError(
                "BENCHMARK_FINE_TUNED_TARGET_REQUIRED",
                "Benchmark requires one completed fine_tuned target, or two for CUDA/MLX parity.",
                status_code=422,
                details={"actual": len(fine_tuned)},
            )
        if len(by_type.get("local_large", [])) > 1:
            raise APIError(
                "BENCHMARK_TARGETS_REQUIRED",
                "Benchmark allows at most one optional local_large target.",
                status_code=422,
                details={"target_type": "local_large", "actual": len(by_type.get("local_large", []))},
            )

        for target in by_type["prompt_only"]:
            if target.backend != "prompt_only" or not target.base_model or not target.prompt_template_sha256:
                raise APIError(
                    "BENCHMARK_TARGET_INVALID",
                    "prompt_only target requires prompt_only backend, base_model, and prompt_template_sha256.",
                    status_code=422,
                    details={"target_key": target.target_key},
                )
        for target in by_type["teacher"]:
            credential = self.session.get(Credential, target.credential_id or "")
            if target.backend != "teacher" or credential is None or credential.is_revoked:
                raise APIError(
                    "BENCHMARK_TEACHER_CREDENTIAL_REQUIRED",
                    "teacher target requires an active local credential reference.",
                    status_code=409,
                    details={"target_key": target.target_key, "credential_id": target.credential_id},
                )
        for target in by_type["rule_based"]:
            if target.backend != "rule_based" or not target.routing_rules_path or not target.routing_rules_sha256:
                raise APIError(
                    "BENCHMARK_TARGET_INVALID",
                    "rule_based target requires routing_rules_path and routing_rules_sha256.",
                    status_code=422,
                    details={"target_key": target.target_key},
                )
        for target in fine_tuned:
            model_run = self.session.get(ModelRun, target.model_run_id or "")
            if model_run is None or model_run.project_id != project_id:
                raise APIError(
                    "MODEL_RUN_NOT_FOUND",
                    "fine_tuned benchmark target ModelRun does not exist for this project.",
                    status_code=404,
                    details={"target_key": target.target_key, "model_run_id": target.model_run_id},
                )
            if target.backend != model_run.backend:
                raise APIError(
                    "BENCHMARK_TARGET_BACKEND_MISMATCH",
                    "fine_tuned target backend must match the ModelRun backend.",
                    status_code=409,
                    details={"target_key": target.target_key, "target_backend": target.backend, "model_run_backend": model_run.backend},
                )
            if model_run.status != "SUCCEEDED" or not model_run.adapter_sha256 or not model_run.artifact_manifest_sha256:
                raise APIError(
                    "MODEL_RUN_NOT_READY",
                    "fine_tuned benchmark target requires a completed ModelRun with adapter lineage.",
                    status_code=409,
                    details={"target_key": target.target_key, "model_run_id": model_run.id, "status": model_run.status},
                )
        for target in by_type.get("local_large", []):
            if target.backend != "local_large" or target.required:
                raise APIError(
                    "BENCHMARK_TARGET_INVALID",
                    "local_large target must be optional and use local_large backend.",
                    status_code=422,
                    details={"target_key": target.target_key},
                )

    def _teacher_packet_ready(self, approval_id: str) -> TeacherPacketApproval:
        approval = self.session.get(TeacherPacketApproval, approval_id)
        now_dt = datetime.now(UTC)
        if approval is None or approval.approved_at is None or _parse_ts(approval.expires_at) <= now_dt:
            raise APIError(
                "TEACHER_PACKET_APPROVAL_REQUIRED",
                "teacher_synthetic generation requires an approved, unexpired Teacher Packet.",
                status_code=409,
                details={"approval_id": approval_id},
            )
        if approval.used_job_id is not None:
            raise APIError(
                "TEACHER_PACKET_APPROVAL_REQUIRED",
                "Teacher Packet approval has already been reserved by a job.",
                status_code=409,
                details={"approval_id": approval.id, "used_job_id": approval.used_job_id},
            )
        return approval

    def _teacher_guard_for_dataset(self, dataset: Dataset) -> EvalSet | None:
        statement = (
            select(EvalSet)
            .where(
                EvalSet.project_id == dataset.project_id,
                EvalSet.purpose == "teacher_guard",
                EvalSet.route_snapshot_sha256 == dataset.route_snapshot_sha256,
                EvalSet.frozen_at.is_not(None),
            )
            .order_by(EvalSet.version.desc())
            .limit(1)
        )
        return self.session.scalars(statement).first()

    def _job_by_project_idempotency_key(self, project_id: str, idempotency_key: str) -> Job | None:
        statement = select(Job).where(Job.project_id == project_id, Job.idempotency_key == idempotency_key).limit(1)
        return self.session.scalars(statement).first()

    def _accepted_response(self, job: Job, *, idempotency_replayed: bool) -> JobAcceptedResponse:
        resource = self.session.get(JobResource, job.id)
        return JobAcceptedResponse(
            job_id=job.id,
            status=job.status,  # type: ignore[arg-type]
            type=job.type,
            events_url=f"/jobs/{job.id}/events",
            created_resource_type=resource.resource_type if resource is not None else "none",  # type: ignore[arg-type]
            created_resource_id=resource.resource_id if resource is not None else None,
            idempotency_replayed=idempotency_replayed,
        )


def _format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
