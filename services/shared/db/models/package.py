from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class AgentPackage(Base):
    __tablename__ = "agent_package"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    model_run_id: Mapped[str] = mapped_column(ForeignKey("model_run.id"), nullable=False)
    benchmark_id: Mapped[str] = mapped_column(ForeignKey("benchmark.id"), nullable=False)
    route_catalog_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    contract_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    contract_version: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("agent_id GLOB '[a-z0-9_]*.v[0-9]*'", name="agent_package_agent_id"),
        CheckConstraint("length(route_catalog_sha256) = 64", name="agent_package_route_catalog_sha256_length"),
        CheckConstraint("contract_version > 0", name="agent_package_contract_version_positive"),
        CheckConstraint("length(contract_sha256) = 64", name="agent_package_contract_sha256_length"),
        UniqueConstraint("project_id", "contract_version", name="uq_agent_package_project_contract_version"),
        UniqueConstraint("project_id", "agent_id", name="uq_agent_package_project_agent_id"),
    )


class ExportArtifact(Base):
    __tablename__ = "export_artifact"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("job.id"), nullable=False, unique=True)
    agent_package_id: Mapped[str] = mapped_column(ForeignKey("agent_package.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_path: Mapped[str | None] = mapped_column(Text)
    manifest_sha256: Mapped[str | None] = mapped_column(Text)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("export_type IN ('zip','docker')", name="export_artifact_type"),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')", name="export_artifact_status"),
        CheckConstraint("manifest_sha256 IS NULL OR length(manifest_sha256) = 64", name="export_manifest_sha256_length"),
        CheckConstraint("artifact_sha256 IS NULL OR length(artifact_sha256) = 64", name="export_artifact_sha256_length"),
        Index("ix_export_artifact_package_type", "agent_package_id", "export_type", "created_at"),
        Index("ix_export_artifact_job", "job_id"),
    )
