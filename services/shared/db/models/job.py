from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_class: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    idempotency_body_sha256: Mapped[str | None] = mapped_column(Text)
    idempotency_expires_at: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_job_id: Mapped[str | None] = mapped_column(ForeignKey("job.id"))
    eval_set_id: Mapped[str | None] = mapped_column(ForeignKey("eval_set.id"))
    preset_version: Mapped[int | None] = mapped_column(Integer)
    claimed_by: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[str | None] = mapped_column(Text)
    cancel_requested_at: Mapped[str | None] = mapped_column(Text)
    not_before_at: Mapped[str | None] = mapped_column(Text)
    error_class: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(Text)
    ended_at: Mapped[str | None] = mapped_column(Text)
    heartbeat_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("type IN ('dataset_gen','train','eval','benchmark','export','hardware_scan')", name="job_type"),
        CheckConstraint("resource_class IN ('cpu_shared','gpu_exclusive')", name="job_resource_class"),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')", name="job_status"),
        CheckConstraint("json_valid(params_json)", name="job_params_json"),
        CheckConstraint(
            "idempotency_body_sha256 IS NULL OR length(idempotency_body_sha256) = 64",
            name="job_idempotency_body_sha256_length",
        ),
        CheckConstraint("attempt_count >= 0", name="job_attempt_count_nonnegative"),
        CheckConstraint(
            "error_class IS NULL OR error_class IN ("
            "'CUDA_OOM','NAN_LOSS','DISK_FULL','MODEL_DOWNLOAD_FAIL','TEACHER_API_ERROR',"
            "'TIMEOUT','SCHEMA_VALIDATION_FAIL','PERMISSION_DENIED','ARTIFACT_MISSING','UNKNOWN'"
            ")",
            name="job_error_class",
        ),
        Index("ix_job_project_status_created", "project_id", "status", "created_at"),
        Index("ix_job_status_priority_created", "status", "priority", "created_at"),
        Index("ix_job_heartbeat", "status", "heartbeat_at"),
        Index(
            "ux_job_idempotency_project",
            "project_id",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL AND project_id IS NOT NULL"),
        ),
        Index(
            "ux_job_idempotency_system",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL AND project_id IS NULL"),
        ),
        Index(
            "ux_one_running_gpu_job",
            "resource_class",
            unique=True,
            sqlite_where=text("resource_class = 'gpu_exclusive' AND status = 'RUNNING'"),
        ),
    )


class JobEvent(Base):
    __tablename__ = "job_event"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("seq > 0", name="job_event_seq_positive"),
        CheckConstraint("level IN ('debug','info','warn','error')", name="job_event_level"),
        CheckConstraint(
            "event_type IN ('status_change','heartbeat','step','loss','vram','log','artifact','metric','error')",
            name="job_event_type",
        ),
        CheckConstraint("json_valid(payload_json)", name="job_event_payload_json"),
        UniqueConstraint("job_id", "seq", name="uq_job_event_job_seq"),
        Index("ix_job_event_job_seq", "job_id", "seq"),
    )


class JobResource(Base):
    __tablename__ = "job_resource"

    job_id: Mapped[str] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"), primary_key=True)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('dataset','model_run','benchmark','export_artifact','hardware_profile')",
            name="job_resource_type",
        ),
        CheckConstraint("is_current IN (0,1)", name="job_resource_is_current_bool"),
        Index("ix_job_resource_resource_current", "resource_type", "resource_id", "is_current"),
        Index(
            "ux_job_resource_current",
            "resource_type",
            "resource_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )


class TeacherPacketApproval(Base):
    __tablename__ = "teacher_packet_approval"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id"), nullable=False)
    packet_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    packet_json: Mapped[str] = mapped_column(Text, nullable=False)
    pii_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    used_job_id: Mapped[str | None] = mapped_column(ForeignKey("job.id"), unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("length(packet_sha256) = 64", name="teacher_packet_packet_sha256_length"),
        CheckConstraint("json_valid(packet_json)", name="teacher_packet_packet_json"),
        CheckConstraint("json_valid(pii_summary_json)", name="teacher_packet_pii_summary_json"),
        Index("ix_teacher_packet_project_created", "project_id", "created_at"),
        Index("ix_teacher_packet_sha", "packet_sha256"),
    )
