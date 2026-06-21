from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.teacher_packet import (
    TeacherPacketApprovalRead,
    TeacherPacketPreviewRead,
    TeacherPacketPreviewRequest,
)
from services.shared.db.models import AuditEvent, Dataset, Example, Project, TeacherPacketApproval
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.security.pii import PiiMaskSummary, mask_json


def new_id() -> str:
    return uuid.uuid4().hex


def utc_now_dt() -> datetime:
    return datetime.now(UTC)


def format_ts(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class TeacherPacketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def preview_packet(self, project_id: str, payload: TeacherPacketPreviewRequest) -> TeacherPacketPreviewRead:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})

        dataset = self._dataset_or_404(payload.dataset_id)
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
                "Teacher Packet Preview requires an approved dataset.",
                status_code=409,
                details={"dataset_id": dataset.id, "status": dataset.status},
            )

        examples = self._select_examples(dataset, payload.example_ids)
        self._require_approved(dataset, examples)

        pii_summary = PiiMaskSummary()
        anonymized_examples = [
            {
                "example_id": example.id,
                "input": mask_json(json.loads(example.input_json), pii_summary),
                "output": mask_json(json.loads(example.output_json), pii_summary),
            }
            for example in examples
        ]
        packet = {
            "rules": json.loads(dataset.route_snapshot_json),
            "schema": router_output_schema(),
            "anonymized_examples": anonymized_examples,
            "instruction": payload.instruction,
        }
        packet_json = canonical_json(packet)
        now_dt = utc_now_dt()
        now = format_ts(now_dt)
        expires_at = format_ts(now_dt + timedelta(minutes=30))
        row = TeacherPacketApproval(
            id=new_id(),
            project_id=project_id,
            dataset_id=dataset.id,
            packet_sha256=sha256_text(packet_json),
            packet_json=packet_json,
            pii_summary_json=canonical_json(pii_summary.as_dict(example_count=len(examples))),
            approved_at=None,
            expires_at=expires_at,
            created_at=now,
        )
        self.session.add(row)
        self.session.flush()
        self._audit_pii_mask(row, pii_summary.as_dict(example_count=len(examples)), now)
        return self._read_preview(row)

    def approve_packet(self, packet_id: str) -> TeacherPacketApprovalRead:
        row = self._packet_or_404(packet_id)
        now_dt = utc_now_dt()
        if _parse_ts(row.expires_at) <= now_dt:
            raise APIError(
                "TEACHER_PACKET_APPROVAL_EXPIRED",
                "Teacher Packet approval has expired.",
                status_code=409,
                details={"approval_id": row.id, "expired_at": row.expires_at},
            )
        if row.used_job_id is not None:
            raise APIError(
                "TEACHER_PACKET_ALREADY_USED",
                "Teacher Packet approval has already been reserved by a job.",
                status_code=409,
                details={"approval_id": row.id, "used_job_id": row.used_job_id},
            )
        if row.approved_at is None:
            row.approved_at = format_ts(now_dt)
            self.session.flush()
        return TeacherPacketApprovalRead(
            approval_id=row.id,
            project_id=row.project_id,
            packet_sha256=row.packet_sha256,
            approved_at=row.approved_at,
            expires_at=row.expires_at,
        )

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

    def _packet_or_404(self, packet_id: str) -> TeacherPacketApproval:
        row = self.session.get(TeacherPacketApproval, packet_id)
        if row is None:
            raise APIError("TEACHER_PACKET_NOT_FOUND", "Teacher Packet approval does not exist.", status_code=404, details={"approval_id": packet_id})
        return row

    def _select_examples(self, dataset: Dataset, example_ids: list[str]) -> list[Example]:
        examples = list(self.session.scalars(select(Example).where(Example.dataset_id == dataset.id).order_by(Example.row_index.asc())))
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

    def _require_approved(self, dataset: Dataset, examples: list[Example]) -> None:
        unapproved = [example.id for example in examples if not example.approved or example.review_status != "APPROVED"]
        if unapproved:
            raise APIError(
                "DATASET_NOT_APPROVED",
                "Teacher Packet Preview requires approved examples.",
                status_code=409,
                details={"dataset_id": dataset.id, "example_ids": unapproved},
            )

    def _read_preview(self, row: TeacherPacketApproval) -> TeacherPacketPreviewRead:
        return TeacherPacketPreviewRead(
            id=row.id,
            project_id=row.project_id,
            packet_sha256=row.packet_sha256,
            packet_preview=json.loads(row.packet_json),
            pii_summary=json.loads(row.pii_summary_json),
            expires_at=row.expires_at,
            approved_at=row.approved_at,
        )

    def _audit_pii_mask(self, row: TeacherPacketApproval, summary: dict[str, Any], ts: str) -> None:
        details = {
            "approval_id": row.id,
            "project_id": row.project_id,
            "dataset_id": row.dataset_id,
            "packet_sha256": row.packet_sha256,
            "policy_version": summary["policy_version"],
            "masked_count": summary["masked_count"],
            "entity_counts": summary["entity_counts"],
            "example_count": summary["example_count"],
        }
        self.session.add(
            AuditEvent(
                id=new_id(),
                ts=ts,
                event_type="pii_mask",
                resource_type="dataset",
                resource_id=row.dataset_id,
                action="teacher_packet_preview",
                policy_version=summary["policy_version"],
                details_json=canonical_json(details),
                trace_id=None,
                retention_until=format_ts(utc_now_dt() + timedelta(days=365)),
                created_at=ts,
            )
        )
        self.session.flush()


def router_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["route", "task_type", "requires_calculation", "requires_human_review", "confidence"],
        "additionalProperties": True,
        "properties": {
            "route": {"type": "string"},
            "task_type": {"type": "string"},
            "requires_calculation": {"type": "boolean"},
            "requires_human_review": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
