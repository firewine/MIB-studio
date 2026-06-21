from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    ts: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(Text)
    retention_until: Mapped[str] = mapped_column(Text, nullable=False)
    contract_sha256: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('pii_mask','teacher_egress','credential_access','export','agent_run','job_failure','job_control','job_reconcile','security')",
            name="audit_event_type",
        ),
        CheckConstraint(
            "resource_type IN ('job','credential','eval_run','agent_package','export_artifact','dataset','project','system')",
            name="audit_event_resource_type",
        ),
        CheckConstraint("json_valid(details_json)", name="audit_event_details_json"),
        CheckConstraint("contract_sha256 IS NULL OR length(contract_sha256) = 64", name="audit_event_contract_sha256_length"),
        Index("ix_audit_event_ts", "ts"),
        Index("ix_audit_event_resource", "resource_type", "resource_id"),
        Index("ix_audit_event_retention", "retention_until"),
    )
