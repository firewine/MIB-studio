from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    route_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    route_snapshot_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    frozen_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("version > 0", name="dataset_version_positive"),
        CheckConstraint("length(sha256) = 64", name="dataset_sha256_length"),
        CheckConstraint("sample_count >= 0", name="dataset_sample_count_nonnegative"),
        CheckConstraint("status IN ('DRAFT','BUILT','REVIEWED','APPROVED','ARCHIVED')", name="dataset_status"),
        CheckConstraint("json_valid(route_snapshot_json)", name="dataset_route_snapshot_json"),
        CheckConstraint("length(route_snapshot_sha256) = 64", name="dataset_route_snapshot_sha256_length"),
        UniqueConstraint("project_id", "version", name="uq_dataset_project_version"),
        Index("ix_dataset_project_version", "project_id", "version"),
    )


class Example(Base):
    __tablename__ = "example"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    split: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    approved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("row_index >= 0", name="example_row_index_nonnegative"),
        CheckConstraint("json_valid(input_json)", name="example_input_json"),
        CheckConstraint("json_valid(output_json)", name="example_output_json"),
        CheckConstraint("length(input_sha256) = 64", name="example_input_sha256_length"),
        CheckConstraint("source IN ('user','import','teacher','hard_negative','eval_gold')", name="example_source"),
        CheckConstraint("split IN ('train','validation','eval')", name="example_split"),
        CheckConstraint("review_status IN ('PENDING','APPROVED','REJECTED','EDITED')", name="example_review_status"),
        CheckConstraint("approved IN (0,1)", name="example_approved_bool"),
        UniqueConstraint("dataset_id", "row_index", name="uq_example_dataset_row_index"),
        Index("ix_example_dataset_approved", "dataset_id", "approved"),
        Index("ix_example_input_sha256", "input_sha256"),
    )
