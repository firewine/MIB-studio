from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.schemas.router_validation import validate_router_example
from services.shared.db.models import AuditEvent, Dataset, EvalSet, Job, JobEvent, JobResource, TeacherPacketApproval
from services.shared.db.repositories.dataset_store import DatasetExampleInput, DatasetStore, canonical_json, new_id, sha256_text


class TeacherSyntheticClient(Protocol):
    def generate_examples(self, packet: dict[str, Any], *, target_count: int) -> Sequence[dict[str, Any]]:
        """Return raw teacher examples shaped as {'input': {...}, 'output': {...}}."""


@dataclass(frozen=True)
class DatasetGenResult:
    job_id: str
    dataset_id: str
    generated_count: int
    validated_count: int
    rejected_count: int
    packet_sha256: str


class DatasetGenWorkerError(Exception):
    def __init__(self, code: str, message: str, *, error_class: str = "UNKNOWN") -> None:
        self.code = code
        self.message = message
        self.error_class = error_class
        super().__init__(message)


def run_dataset_gen_job(
    session: Session,
    mib_home: Path,
    job_id: str,
    *,
    teacher_client: TeacherSyntheticClient,
) -> DatasetGenResult:
    job = session.get(Job, job_id)
    if job is None:
        raise DatasetGenWorkerError("JOB_NOT_FOUND", "Job does not exist.")

    now = utc_now()
    job.status = "RUNNING"
    job.started_at = job.started_at or now
    job.attempt_count = job.attempt_count + 1
    session.flush()
    _job_event(session, job, level="info", event_type="status_change", payload={"status": "RUNNING"})

    try:
        result = _run_teacher_synthetic(session, mib_home, job, teacher_client)
    except DatasetGenWorkerError as exc:
        job.status = "FAILED"
        job.error_class = exc.error_class
        job.error_message = exc.message
        job.ended_at = utc_now()
        _job_event(session, job, level="error", event_type="error", payload={"code": exc.code, "message": exc.message})
        session.flush()
        raise

    job.status = "SUCCEEDED"
    job.ended_at = utc_now()
    _job_event(
        session,
        job,
        level="info",
        event_type="metric",
        payload={
            "phase": "done",
            "generation_mode": "teacher_synthetic",
            "generated_count": result.generated_count,
            "validated_count": result.validated_count,
            "rejected_count": result.rejected_count,
            "packet_sha256": result.packet_sha256,
        },
    )
    session.flush()
    return result


def _run_teacher_synthetic(
    session: Session,
    mib_home: Path,
    job: Job,
    teacher_client: TeacherSyntheticClient,
) -> DatasetGenResult:
    if job.type != "dataset_gen":
        raise DatasetGenWorkerError("JOB_TYPE_UNSUPPORTED", "Job is not a dataset_gen job.", error_class="UNKNOWN")
    params = json.loads(job.params_json)
    if params.get("generation_mode") != "teacher_synthetic":
        raise DatasetGenWorkerError(
            "GENERATION_MODE_UNSUPPORTED",
            "Only teacher_synthetic dataset_gen is implemented in M2-003.",
            error_class="UNKNOWN",
        )

    approval_id = str(params.get("teacher_packet_approval_id") or "")
    approval = session.get(TeacherPacketApproval, approval_id)
    if approval is None or approval.used_job_id != job.id:
        raise DatasetGenWorkerError(
            "TEACHER_PACKET_RESERVATION_INVALID",
            "Teacher Packet approval is not reserved for this job.",
            error_class="PERMISSION_DENIED",
        )
    packet_sha256 = str(params.get("packet_sha256") or "")
    if packet_sha256 != approval.packet_sha256 or sha256_text(approval.packet_json) != approval.packet_sha256:
        raise DatasetGenWorkerError(
            "TEACHER_PACKET_HASH_MISMATCH",
            "Teacher Packet hash does not match the reserved job.",
            error_class="PERMISSION_DENIED",
        )

    source_dataset = session.get(Dataset, approval.dataset_id)
    if source_dataset is None:
        raise DatasetGenWorkerError("SOURCE_DATASET_MISSING", "Approved source dataset is missing.", error_class="ARTIFACT_MISSING")
    teacher_guard = _teacher_guard(session, job, source_dataset)
    guard_hashes = _teacher_guard_input_hashes(teacher_guard)

    target_count = int(params.get("target_count") or 200)
    packet = json.loads(approval.packet_json)
    _audit_teacher_egress(session, job, approval, target_count=target_count)
    raw_examples = list(teacher_client.generate_examples(packet, target_count=target_count))
    examples = _validate_generated_examples(raw_examples, source_dataset, guard_hashes, target_count=target_count)

    now = utc_now()
    store = DatasetStore(session, mib_home)
    dataset = store.create_dataset(
        project_id=source_dataset.project_id,
        version=store.next_version(source_dataset.project_id),
        status="BUILT",
        examples=examples,
        route_snapshot_json=source_dataset.route_snapshot_json,
        route_snapshot_sha256=source_dataset.route_snapshot_sha256,
        created_at=now,
    )
    session.add(
        JobResource(
            job_id=job.id,
            resource_type="dataset",
            resource_id=dataset.id,
            is_current=1,
            created_at=now,
        )
    )
    session.flush()
    return DatasetGenResult(
        job_id=job.id,
        dataset_id=dataset.id,
        generated_count=len(raw_examples),
        validated_count=len(examples),
        rejected_count=len(raw_examples) - len(examples),
        packet_sha256=packet_sha256,
    )


def _validate_generated_examples(
    raw_examples: list[dict[str, Any]],
    source_dataset: Dataset,
    guard_hashes: set[str],
    *,
    target_count: int,
) -> list[DatasetExampleInput]:
    if len(raw_examples) < target_count:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_UNDER_GENERATED",
            "Teacher response produced fewer examples than requested.",
            error_class="TEACHER_API_ERROR",
        )

    route_ids = [route["route_id"] for route in json.loads(source_dataset.route_snapshot_json)]
    examples: list[DatasetExampleInput] = []
    row_errors: list[dict[str, Any]] = []
    overlaps: list[str] = []
    for index, raw in enumerate(raw_examples):
        input_payload = raw.get("input")
        output_payload = raw.get("output")
        if not isinstance(input_payload, dict) or not isinstance(output_payload, dict):
            row_errors.append({"row_index": index, "code": "ROW_SHAPE_INVALID"})
            continue
        input_sha256 = sha256_text(canonical_json(input_payload))
        if input_sha256 in guard_hashes:
            overlaps.append(input_sha256)
        errors = validate_router_example(input_payload, output_payload, route_ids)
        if errors:
            row_errors.append(
                {"row_index": index, "errors": [error.model_dump() for error in errors], "code": "SCHEMA_VALIDATION_FAILED"}
            )
            continue
        examples.append(DatasetExampleInput(input=input_payload, output=output_payload, source="teacher"))

    if overlaps:
        raise DatasetGenWorkerError(
            "TEACHER_GUARD_SYNTHETIC_OVERLAP",
            "Teacher synthetic examples overlap with the frozen teacher_guard inputs.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    if row_errors:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_SCHEMA_INVALID",
            "Teacher synthetic examples failed router schema validation.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    if len(examples) < target_count:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_UNDER_VALIDATED",
            "Teacher response did not produce enough schema-valid examples.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    return examples


def _teacher_guard(session: Session, job: Job, dataset: Dataset) -> EvalSet:
    if job.eval_set_id:
        eval_set = session.get(EvalSet, job.eval_set_id)
        if eval_set is not None:
            return eval_set
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
    eval_set = session.scalars(statement).first()
    if eval_set is None:
        raise DatasetGenWorkerError(
            "TEACHER_GUARD_REQUIRED",
            "teacher_synthetic generation requires a frozen teacher_guard EvalSet.",
            error_class="PERMISSION_DENIED",
        )
    return eval_set


def _teacher_guard_input_hashes(eval_set: EvalSet) -> set[str]:
    path = Path(eval_set.path)
    if not path.exists():
        raise DatasetGenWorkerError("TEACHER_GUARD_ARTIFACT_MISSING", "teacher_guard artifact is missing.", error_class="ARTIFACT_MISSING")
    hashes: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            hashes.add(str(json.loads(line)["input_sha256"]))
    return hashes


def _audit_teacher_egress(session: Session, job: Job, approval: TeacherPacketApproval, *, target_count: int) -> None:
    ts = utc_now()
    details = {
        "approval_id": approval.id,
        "project_id": approval.project_id,
        "dataset_id": approval.dataset_id,
        "packet_sha256": approval.packet_sha256,
        "approved_by_user": True,
        "target_count": target_count,
    }
    session.add(
        AuditEvent(
            id=new_id(),
            ts=ts,
            event_type="teacher_egress",
            resource_type="job",
            resource_id=job.id,
            action="teacher_synthetic_generate",
            policy_version="M2-003",
            details_json=canonical_json(details),
            trace_id=job.trace_id,
            retention_until=_format_ts(datetime.now(UTC) + timedelta(days=365)),
            created_at=ts,
        )
    )
    session.flush()


def _job_event(session: Session, job: Job, *, level: str, event_type: str, payload: dict[str, Any]) -> None:
    next_seq = int(session.scalar(select(func.max(JobEvent.seq)).where(JobEvent.job_id == job.id)) or 0) + 1
    session.add(
        JobEvent(
            id=new_id(),
            job_id=job.id,
            seq=next_seq,
            ts=utc_now(),
            level=level,
            event_type=event_type,
            payload_json=canonical_json(payload),
            trace_id=job.trace_id,
        )
    )
    session.flush()


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
