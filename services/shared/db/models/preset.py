from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class Preset(Base):
    __tablename__ = "preset"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    preset_type: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    base_model_options_json: Mapped[str] = mapped_column(Text, nullable=False)
    data_template_json: Mapped[str] = mapped_column(Text, nullable=False)
    training_defaults_json: Mapped[str] = mapped_column(Text, nullable=False)
    eval_options_json: Mapped[str] = mapped_column(Text, nullable=False)
    export_options_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("preset_type IN ('router')", name="preset_type"),
        CheckConstraint("version > 0", name="preset_version_positive"),
        CheckConstraint("json_valid(base_model_options_json)", name="preset_base_models_json"),
        CheckConstraint("json_valid(data_template_json)", name="preset_data_template_json"),
        CheckConstraint("json_valid(training_defaults_json)", name="preset_training_defaults_json"),
        CheckConstraint("json_valid(eval_options_json)", name="preset_eval_options_json"),
        CheckConstraint("json_valid(export_options_json)", name="preset_export_options_json"),
        UniqueConstraint("name", "version", name="uq_preset_name_version"),
    )
