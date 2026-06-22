from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError, json_safe_errors
from services.api.app.schemas.job import JobAcceptedResponse, JobSubmitRequest, TrainParams
from services.api.app.schemas.training import ModelRunPage, ModelRunRead
from services.api.app.services.training_read_models import read_model_run
from services.shared.db.models import Dataset, Example, HardwareProfile, Job, JobResource, ModelRun, Preset, Project
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.repositories.training_store import TrainingRunInput, TrainingStore
from services.shared.model_catalog import ModelCatalogError, load_model_catalog


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class TrainingService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home
        self.store = TrainingStore(session)

    def submit_train_job(
        self,
        project_id: str,
        payload: JobSubmitRequest,
        *,
        idempotency_key: str | None,
        trace_id: str,
    ) -> JobAcceptedResponse:
        if payload.type != "train":
            raise APIError(
                "MILESTONE_LOCKED",
                "This job type is locked until its implementation milestone.",
                status_code=409,
                details={"type": payload.type, "current_milestone": "M3-001"},
            )
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

        params = self._train_params(payload.params)
        self._preset_or_404(params.preset_id)
        dataset = self._approved_dataset(project_id, params.dataset_id)
        model = self._catalog_model(params.base_model)
        if params.backend not in model.allowed_backends:
            raise APIError(
                "MODEL_BACKEND_UNSUPPORTED",
                "Base model is not allowed for the requested backend.",
                status_code=409,
                details={"model_id": model.id, "backend": params.backend, "allowed_backends": list(model.allowed_backends)},
            )
        hardware = self._training_hardware(params.backend)
        self._require_route_snapshot_consistency(dataset)

        now = utc_now()
        method = "qlora" if params.backend == "cuda" else "mlx_lora"
        config = {
            "schema_version": "training_config.v1",
            "preset_id": params.preset_id,
            "dataset_id": dataset.id,
            "dataset_version": dataset.version,
            "route_snapshot_sha256": dataset.route_snapshot_sha256,
            "base_model": params.base_model,
            "backend": params.backend,
            "method": method,
            "training_preset": params.training_preset,
            "seed": params.seed,
            "model_cache_subdir": model.cache_subdir,
            "hardware_profile_id": hardware.id,
        }
        rows = self.store.create_queued_training_run(
            TrainingRunInput(
                project_id=project_id,
                dataset_id=dataset.id,
                base_model=params.base_model,
                backend=params.backend,
                method=method,
                seed=params.seed,
                config=config,
                job_params=params.model_dump(),
                idempotency_key=idempotency_key,
                idempotency_body_sha256=body_hash if idempotency_key else None,
                idempotency_expires_at=_format_ts(datetime.now(UTC) + timedelta(hours=24)) if idempotency_key else None,
                trace_id=trace_id,
                created_at=now,
            )
        )
        return self._accepted_response(rows.job, idempotency_replayed=False)

    def list_model_runs(
        self,
        project_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
        backend: str | None = None,
    ) -> ModelRunPage:
        self._project_or_404(project_id)
        rows = self.store.list_model_runs(project_id, cursor=cursor, limit=limit, status=status, backend=backend)
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = json.dumps([last.created_at, last.id], separators=(",", ":"))
        return ModelRunPage(items=[self._read_model_run(row) for row in rows[:limit]], next_cursor=next_cursor)

    def get_model_run(self, model_run_id: str) -> ModelRunRead:
        model_run = self.session.get(ModelRun, model_run_id)
        if model_run is None:
            raise APIError("MODEL_RUN_NOT_FOUND", "ModelRun does not exist.", status_code=404, details={"model_run_id": model_run_id})
        return self._read_model_run(model_run)

    def _train_params(self, raw_params: dict[str, Any]) -> TrainParams:
        try:
            return TrainParams.model_validate(raw_params)
        except ValidationError as exc:
            raise APIError(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status_code=422,
                details={"errors": json_safe_errors(exc.errors())},
            ) from exc

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _preset_or_404(self, preset_id: str) -> Preset:
        preset = self.session.get(Preset, preset_id)
        if preset is None:
            raise APIError("PRESET_NOT_FOUND", "Preset does not exist.", status_code=404, details={"preset_id": preset_id})
        return preset

    def _approved_dataset(self, project_id: str, dataset_id: str) -> Dataset:
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise APIError("DATASET_NOT_FOUND", "Dataset does not exist.", status_code=404, details={"dataset_id": dataset_id})
        if dataset.project_id != project_id:
            raise APIError(
                "DATASET_PROJECT_MISMATCH",
                "Dataset does not belong to the requested project.",
                status_code=409,
                details={"project_id": project_id, "dataset_id": dataset.id},
            )
        if dataset.status != "APPROVED":
            raise APIError(
                "DATASET_NOT_APPROVED",
                "Training preflight requires an approved dataset.",
                status_code=409,
                details={"dataset_id": dataset.id, "status": dataset.status},
            )
        return dataset

    def _catalog_model(self, model_id: str) -> Any:
        try:
            return load_model_catalog().get(model_id)
        except ModelCatalogError as exc:
            raise APIError(
                "MODEL_CATALOG_INVALID",
                "Strict model catalog is not ready.",
                status_code=409,
                details={"errors": exc.errors},
            ) from exc

    def _training_hardware(self, backend: str) -> HardwareProfile:
        profile = self.session.scalars(select(HardwareProfile).order_by(HardwareProfile.created_at.desc()).limit(1)).first()
        if profile is None:
            raise APIError(
                "HARDWARE_PROFILE_REQUIRED",
                "Training preflight requires a successful hardware scan.",
                status_code=409,
                details={"backend": backend},
            )
        dry_run = json.loads(profile.dry_run_result_json)
        allowed_backends = dry_run.get("allowed_backends", [])
        if profile.capability_gate == "G0" or backend not in allowed_backends or not dry_run.get("training_enabled", False):
            raise APIError(
                "HARDWARE_BACKEND_UNAVAILABLE",
                "Requested backend is not enabled by the latest hardware scan.",
                status_code=409,
                details={
                    "backend": backend,
                    "capability_gate": profile.capability_gate,
                    "allowed_backends": allowed_backends,
                    "reason_code": dry_run.get("training_disabled_reason_code", "UNKNOWN"),
                },
            )
        return profile

    def _require_route_snapshot_consistency(self, dataset: Dataset) -> None:
        if sha256_text(dataset.route_snapshot_json) != dataset.route_snapshot_sha256:
            raise APIError(
                "DATASET_ROUTE_SNAPSHOT_MISMATCH",
                "Dataset route snapshot hash does not match its stored snapshot.",
                status_code=409,
                details={"dataset_id": dataset.id},
            )
        route_ids = [route["route_id"] for route in json.loads(dataset.route_snapshot_json)]
        statement: Select[tuple[Example]] = select(Example).where(Example.dataset_id == dataset.id, Example.approved == 1)
        mismatches = []
        for example in self.session.scalars(statement):
            input_payload = json.loads(example.input_json)
            if input_payload.get("allowed_routes") != route_ids:
                mismatches.append(example.id)
        if mismatches:
            raise APIError(
                "DATASET_ROUTE_SNAPSHOT_MISMATCH",
                "Approved examples do not match the dataset route snapshot.",
                status_code=409,
                details={"dataset_id": dataset.id, "example_ids": mismatches[:25], "mismatch_count": len(mismatches)},
            )

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

    def _read_model_run(self, model_run: ModelRun) -> ModelRunRead:
        return read_model_run(model_run, job_id=self.store.current_job_id_for_model_run(model_run.id))


def _format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
