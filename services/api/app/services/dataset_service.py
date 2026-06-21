from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError, json_safe_errors
from services.api.app.schemas.dataset import (
    DatasetBuildRequest,
    DatasetPage,
    DatasetPatch,
    DatasetRead,
    DatasetWithExamples,
    ExamplePatch,
    ExampleRead,
)
from services.api.app.schemas.job import DatasetGenParams, JobAcceptedResponse, JobSubmitRequest
from services.api.app.schemas.router_validation import validate_router_example
from services.shared.db.models import Dataset, EvalSet, Example, Job, JobResource, Project, TeacherPacketApproval
from services.shared.db.repositories.dataset_store import (
    DatasetExampleInput,
    DatasetStore,
    canonical_json,
    new_id,
    sha256_text,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class DatasetService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.store = DatasetStore(session, mib_home)

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

    def build_dataset(self, project_id: str, payload: DatasetBuildRequest) -> DatasetRead:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})

        route_snapshot = self.store.route_snapshot(project_id)
        route_ids = [route["route_id"] for route in route_snapshot]
        if len(route_ids) < 2:
            raise APIError("PROJECT_ROUTES_REQUIRED", "Project must have at least two routes.", status_code=409, details={"project_id": project_id})

        examples = [
            DatasetExampleInput(input=item.input, output=item.output, source=item.source)
            for item in payload.examples
        ]
        self._validate_examples(examples, route_ids)
        version = self.store.next_version(project_id)
        now = utc_now()
        route_snapshot_json = canonical_json(route_snapshot)
        dataset = self.store.create_dataset(
            project_id=project_id,
            version=version,
            status=payload.status,
            examples=examples,
            route_snapshot_json=route_snapshot_json,
            route_snapshot_sha256=sha256_text(route_snapshot_json),
            created_at=now,
        )
        return self._read_dataset(dataset)

    def list_datasets(
        self,
        project_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> DatasetPage:
        self._project_or_404(project_id)
        statement: Select[tuple[Dataset]] = select(Dataset).where(Dataset.project_id == project_id)
        if status:
            statement = statement.where(Dataset.status == status)
        if cursor:
            statement = statement.where(Dataset.version < int(cursor))
        statement = statement.order_by(Dataset.version.desc()).limit(limit + 1)
        datasets = list(self.session.scalars(statement))
        next_cursor = str(datasets[limit - 1].version) if len(datasets) > limit else None
        return DatasetPage(items=[self._read_dataset(dataset) for dataset in datasets[:limit]], next_cursor=next_cursor)

    def get_dataset(self, dataset_id: str, *, cursor: str | None = None, limit: int = 50) -> DatasetWithExamples:
        dataset = self._dataset_or_404(dataset_id)
        statement: Select[tuple[Example]] = select(Example).where(Example.dataset_id == dataset.id)
        if cursor:
            statement = statement.where(Example.row_index > int(cursor))
        statement = statement.order_by(Example.row_index.asc()).limit(limit + 1)
        examples = list(self.session.scalars(statement))
        next_cursor = str(examples[limit - 1].row_index) if len(examples) > limit else None
        base = self._read_dataset(dataset).model_dump()
        return DatasetWithExamples(
            **base,
            examples=[self._read_example(example) for example in examples[:limit]],
            next_cursor=next_cursor,
        )

    def patch_dataset(self, dataset_id: str, payload: DatasetPatch) -> DatasetRead:
        dataset = self._dataset_or_404(dataset_id)
        if dataset.status == "APPROVED" and payload.status != "ARCHIVED":
            raise APIError("DATASET_FROZEN", "Approved datasets are immutable.", status_code=409, details={"dataset_id": dataset_id})

        if payload.approved_example_ids is not None:
            selected = self._select_examples(dataset, payload.approved_example_ids)
            self._mark_approved_examples(dataset, selected)

        if payload.status == "APPROVED":
            self._require_generated_review_complete(dataset)
            selected = self._approved_examples(dataset)
            if len(selected) < 20:
                raise APIError(
                    "DATASET_APPROVAL_MIN_EXAMPLES",
                    "Dataset approval requires at least 20 approved examples.",
                    status_code=409,
                    details={"dataset_id": dataset.id, "approved_count": len(selected)},
                )
            route_ids = [route["route_id"] for route in json.loads(dataset.route_snapshot_json)]
            self._validate_examples(
                [
                    DatasetExampleInput(
                        input=json.loads(example.input_json),
                        output=json.loads(example.output_json),
                        source=example.source,
                    )
                    for example in selected
                ],
                route_ids,
            )
            self.store.rewrite_dataset_from_examples(dataset, selected)
            dataset.status = "APPROVED"
            dataset.frozen_at = utc_now()
        elif payload.status is not None:
            dataset.status = payload.status

        self.session.flush()
        return self._read_dataset(dataset)

    def patch_example(self, example_id: str, payload: ExamplePatch) -> ExampleRead:
        example = self._example_or_404(example_id)
        dataset = self._dataset_or_404(example.dataset_id)
        if dataset.status == "APPROVED":
            raise APIError("DATASET_FROZEN", "Approved datasets are immutable.", status_code=409, details={"dataset_id": dataset.id})

        input_payload = json.loads(example.input_json) if payload.input is None else payload.input
        output_payload = json.loads(example.output_json) if payload.output is None else payload.output
        route_ids = [route["route_id"] for route in json.loads(dataset.route_snapshot_json)]
        self._validate_examples(
            [DatasetExampleInput(input=input_payload, output=output_payload, source=example.source)],
            route_ids,
        )

        changed_payload = payload.input is not None or payload.output is not None
        example.input_json = canonical_json(input_payload)
        example.output_json = canonical_json(output_payload)
        example.input_sha256 = sha256_text(example.input_json)
        if payload.review_status is not None:
            example.review_status = payload.review_status
        elif changed_payload:
            example.review_status = "EDITED"
        example.approved = 1 if example.review_status == "APPROVED" else 0
        self.session.flush()
        return self._read_example(example)

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _dataset_or_404(self, dataset_id: str) -> Dataset:
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise APIError("DATASET_NOT_FOUND", "Dataset does not exist.", status_code=404, details={"dataset_id": dataset_id})
        return dataset

    def _example_or_404(self, example_id: str) -> Example:
        example = self.session.get(Example, example_id)
        if example is None:
            raise APIError("EXAMPLE_NOT_FOUND", "Example does not exist.", status_code=404, details={"example_id": example_id})
        return example

    def _select_examples(self, dataset: Dataset, example_ids: list[str]) -> list[Example]:
        examples = self.store.examples_for_dataset(dataset.id)
        by_id = {example.id: example for example in examples}
        missing = [example_id for example_id in example_ids if example_id not in by_id]
        if missing:
            raise APIError(
                "EXAMPLE_NOT_FOUND",
                "One or more examples do not exist for this dataset.",
                status_code=404,
                details={"dataset_id": dataset.id, "example_ids": missing},
            )
        return [by_id[example_id] for example_id in example_ids]

    def _mark_approved_examples(self, dataset: Dataset, selected: list[Example]) -> None:
        selected_ids = {example.id for example in selected}
        for example in self.store.examples_for_dataset(dataset.id):
            if example.id in selected_ids:
                example.review_status = "APPROVED"
                example.approved = 1
            else:
                example.approved = 0
                if example.review_status == "APPROVED":
                    example.review_status = "PENDING"

    def _approved_examples(self, dataset: Dataset) -> list[Example]:
        return [example for example in self.store.examples_for_dataset(dataset.id) if bool(example.approved)]

    def _require_generated_review_complete(self, dataset: Dataset) -> None:
        examples = self.store.examples_for_dataset(dataset.id)
        if not any(example.source in {"teacher", "hard_negative"} for example in examples):
            return
        pending = [example.id for example in examples if example.review_status == "PENDING"]
        if pending:
            raise APIError(
                "DATASET_REVIEW_INCOMPLETE",
                "Generated dataset approval requires a review decision for every generated example.",
                status_code=409,
                details={"dataset_id": dataset.id, "pending_example_ids": pending[:25], "pending_count": len(pending)},
            )

    def _validate_examples(self, examples: list[DatasetExampleInput], route_ids: list[str]) -> None:
        row_errors: list[dict[str, Any]] = []
        for index, example in enumerate(examples):
            errors = validate_router_example(example.input, example.output, route_ids)
            if errors:
                row_errors.append({"row_index": index, "errors": [error.model_dump() for error in errors]})

        if row_errors:
            raise APIError(
                "DATASET_ROW_INVALID",
                "Dataset examples failed router schema validation.",
                status_code=422,
                details={"row_errors": row_errors},
            )

    def _read_dataset(self, dataset: Dataset) -> DatasetRead:
        return DatasetRead(
            id=dataset.id,
            project_id=dataset.project_id,
            version=dataset.version,
            status=dataset.status,  # type: ignore[arg-type]
            path=dataset.path,
            sample_count=dataset.sample_count,
            sha256=dataset.sha256,
            schema_version=dataset.schema_version,
            route_snapshot_sha256=dataset.route_snapshot_sha256,
            created_at=dataset.created_at,
            frozen_at=dataset.frozen_at,
        )

    def _read_example(self, example: Example) -> ExampleRead:
        return ExampleRead(
            id=example.id,
            dataset_id=example.dataset_id,
            source=example.source,  # type: ignore[arg-type]
            input=json.loads(example.input_json),
            output=json.loads(example.output_json),
            review_status=example.review_status,  # type: ignore[arg-type]
            approved=bool(example.approved),
            validation_errors=[],
            created_at=example.created_at,
        )

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
