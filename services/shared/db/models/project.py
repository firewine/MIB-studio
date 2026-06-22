from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    preset_id: Mapped[str] = mapped_column(ForeignKey("preset.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    archived_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 120", name="project_name_length"),
        Index("ix_project_updated_at", "updated_at"),
    )


class ProjectRoute(Base):
    __tablename__ = "project_route"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    route_id: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_unsafe: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_type: Mapped[str] = mapped_column(Text, nullable=False, default="generate_report")
    requires_calculation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_human_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    examples_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("length(route_id) BETWEEN 1 AND 64", name="project_route_id_length"),
        CheckConstraint("length(description) BETWEEN 1 AND 2000", name="project_route_description_length"),
        CheckConstraint("is_unsafe IN (0,1)", name="project_route_is_unsafe_bool"),
        CheckConstraint("task_type IN ('generate_report','provide_advice','escalate','block')", name="project_route_task_type"),
        CheckConstraint("requires_calculation IN (0,1)", name="project_route_requires_calculation_bool"),
        CheckConstraint("requires_human_review IN (0,1)", name="project_route_requires_human_review_bool"),
        CheckConstraint("is_default IN (0,1)", name="project_route_is_default_bool"),
        UniqueConstraint("project_id", "route_id", name="uq_project_route_project_route_id"),
        Index("ix_project_route_project_unsafe", "project_id", "is_unsafe"),
    )
