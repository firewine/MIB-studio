from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class EvalSet(Base):
    __tablename__ = "eval_set"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    route_snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    labeler_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    kappa: Mapped[float | None] = mapped_column(Float)
    frozen_at: Mapped[str] = mapped_column(Text, nullable=False)
    is_holdout: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("version > 0", name="eval_set_version_positive"),
        CheckConstraint("length(sha256) = 64", name="eval_set_sha256_length"),
        CheckConstraint("sample_count > 0", name="eval_set_sample_count_positive"),
        CheckConstraint("purpose IN ('teacher_guard','benchmark_gold','finance_reference')", name="eval_set_purpose"),
        CheckConstraint("length(route_snapshot_sha256) = 64", name="eval_set_route_snapshot_sha256_length"),
        CheckConstraint("json_valid(labeler_ids_json)", name="eval_set_labeler_ids_json"),
        CheckConstraint("kappa IS NULL OR (kappa >= 0 AND kappa <= 1)", name="eval_set_kappa_range"),
        CheckConstraint("is_holdout IN (0,1)", name="eval_set_is_holdout_bool"),
        UniqueConstraint("project_id", "version", name="uq_eval_set_project_version"),
        Index("ix_eval_set_project_version", "project_id", "version"),
        Index("ix_eval_set_dataset", "dataset_id"),
    )


class Benchmark(Base):
    __tablename__ = "benchmark"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    eval_set_id: Mapped[str] = mapped_column(ForeignKey("eval_set.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    report_path: Mapped[str | None] = mapped_column(Text)
    report_sha256: Mapped[str | None] = mapped_column(Text)
    parity_status: Mapped[str] = mapped_column(Text, nullable=False, default="NA")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','INTERRUPTED')", name="benchmark_status"),
        CheckConstraint("report_sha256 IS NULL OR length(report_sha256) = 64", name="benchmark_report_sha256_length"),
        CheckConstraint("parity_status IN ('PASS','FAIL','NA')", name="benchmark_parity_status"),
        Index("ix_benchmark_project_eval_set", "project_id", "eval_set_id"),
    )


class EvalRun(Base):
    __tablename__ = "eval_run"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    benchmark_id: Mapped[str] = mapped_column(ForeignKey("benchmark.id", ondelete="CASCADE"), nullable=False)
    model_run_id: Mapped[str | None] = mapped_column(ForeignKey("model_run.id"))
    target_key: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    backend: Mapped[str] = mapped_column(Text, nullable=False)
    target_status: Mapped[str] = mapped_column(Text, nullable=False, default="QUEUED")
    target_config_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credential.id"))
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("length(target_key) BETWEEN 1 AND 80", name="eval_run_target_key_length"),
        CheckConstraint("target_type IN ('prompt_only','fine_tuned','teacher','local_large','rule_based')", name="eval_run_target_type"),
        CheckConstraint("backend IN ('cuda','mlx','teacher','rule_based','prompt_only','local_large')", name="eval_run_backend"),
        CheckConstraint(
            "target_status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','INTERRUPTED','SKIPPED_OPTIONAL')",
            name="eval_run_target_status",
        ),
        CheckConstraint("json_valid(target_config_json)", name="eval_run_target_config_json"),
        CheckConstraint("json_valid(metrics_json)", name="eval_run_metrics_json"),
        CheckConstraint(
            "target_status != 'SKIPPED_OPTIONAL' OR (target_type = 'local_large' AND seed = 0)",
            name="eval_run_skipped_optional_shape",
        ),
        UniqueConstraint("benchmark_id", "target_key", "seed", name="uq_eval_run_benchmark_target_seed"),
        Index("ix_eval_run_benchmark_target_key", "benchmark_id", "target_key"),
        Index("ix_eval_run_benchmark_target_type", "benchmark_id", "target_type"),
    )
