from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class HardwareProfile(Base):
    __tablename__ = "hardware_profile"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    machine_id: Mapped[str] = mapped_column(Text, nullable=False)
    os: Mapped[str] = mapped_column(Text, nullable=False)
    cpu: Mapped[str | None] = mapped_column(Text)
    ram_gb: Mapped[float] = mapped_column(Float, nullable=False)
    gpu_vendor: Mapped[str] = mapped_column(Text, nullable=False)
    gpu_name: Mapped[str | None] = mapped_column(Text)
    vram_gb: Mapped[float | None] = mapped_column(Float)
    unified_ram_gb: Mapped[float | None] = mapped_column(Float)
    cuda_status: Mapped[str | None] = mapped_column(Text)
    mlx_status: Mapped[str | None] = mapped_column(Text)
    capability_gate: Mapped[str] = mapped_column(Text, nullable=False)
    dry_run_result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("ram_gb > 0", name="hardware_profile_ram_positive"),
        CheckConstraint("gpu_vendor IN ('nvidia','apple','amd','intel','none','unknown')", name="hardware_profile_gpu_vendor"),
        CheckConstraint("cuda_status IN ('ok','missing','unsupported','na')", name="hardware_profile_cuda_status"),
        CheckConstraint("mlx_status IN ('ok','missing','unsupported','na')", name="hardware_profile_mlx_status"),
        CheckConstraint("capability_gate IN ('G0','G1','G2')", name="hardware_profile_capability_gate"),
        CheckConstraint("json_valid(dry_run_result_json)", name="hardware_profile_dry_run_result_json"),
        Index("ix_hardware_profile_machine_created", "machine_id", "created_at"),
    )
