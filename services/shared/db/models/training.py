from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class ModelRun(Base):
    __tablename__ = "model_run"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id"), nullable=False)
    base_model: Mapped[str] = mapped_column(Text, nullable=False)
    backend: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_path: Mapped[str | None] = mapped_column(Text)
    adapter_sha256: Mapped[str | None] = mapped_column(Text)
    artifact_manifest_sha256: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    best_checkpoint_id: Mapped[str | None] = mapped_column(Text)
    resumable: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[str | None] = mapped_column(Text)
    ended_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("base_model IN ('google/gemma-2b-it','microsoft/Phi-3.5-mini-instruct')", name="model_run_base_model"),
        CheckConstraint("backend IN ('cuda','mlx')", name="model_run_backend"),
        CheckConstraint("method IN ('qlora','mlx_lora')", name="model_run_method"),
        CheckConstraint("adapter_sha256 IS NULL OR length(adapter_sha256) = 64", name="model_run_adapter_sha256_length"),
        CheckConstraint(
            "artifact_manifest_sha256 IS NULL OR length(artifact_manifest_sha256) = 64",
            name="model_run_artifact_manifest_sha256_length",
        ),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')", name="model_run_status"),
        CheckConstraint("json_valid(config_json)", name="model_run_config_json"),
        CheckConstraint("length(config_hash) = 64", name="model_run_config_hash_length"),
        CheckConstraint("resumable IN (0,1)", name="model_run_resumable_bool"),
        Index("ix_model_run_project_created", "project_id", "created_at"),
    )


class Checkpoint(Base):
    __tablename__ = "checkpoint"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), nullable=False)
    model_run_id: Mapped[str] = mapped_column(ForeignKey("model_run.id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id"), nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    training_config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    weights_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("step >= 0", name="checkpoint_step_nonnegative"),
        CheckConstraint("json_valid(metrics_json)", name="checkpoint_metrics_json"),
        CheckConstraint("dataset_version > 0", name="checkpoint_dataset_version_positive"),
        CheckConstraint("length(training_config_hash) = 64", name="checkpoint_training_config_hash_length"),
        CheckConstraint("length(weights_sha256) = 64", name="checkpoint_weights_sha256_length"),
        UniqueConstraint("model_run_id", "step", name="uq_checkpoint_model_run_step"),
        Index("ix_checkpoint_model_step", "model_run_id", "step"),
    )
