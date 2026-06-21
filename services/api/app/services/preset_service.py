from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.preset import PresetPage, PresetRead
from services.shared.db.models import Preset


class PresetService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_presets(self) -> PresetPage:
        statement = select(Preset).where(Preset.preset_type == "router").order_by(Preset.name.asc(), Preset.version.asc())
        return PresetPage(items=[self._read_preset(preset) for preset in self.session.scalars(statement)])

    def get_preset(self, preset_id: str) -> PresetRead:
        preset = self.session.get(Preset, preset_id)
        if preset is None or preset.preset_type != "router":
            raise APIError("PRESET_NOT_FOUND", "Preset does not exist.", status_code=404, details={"preset_id": preset_id})
        return self._read_preset(preset)

    def _read_preset(self, preset: Preset) -> PresetRead:
        data_template = json.loads(preset.data_template_json)
        schema_refs = data_template.get("schemas", {})
        return PresetRead(
            id=preset.id,
            name=preset.name,
            preset_type="router",
            version=preset.version,
            schema_refs=schema_refs if isinstance(schema_refs, dict) else {},
            config_json={
                "base_model_options": json.loads(preset.base_model_options_json),
                "data_template": data_template,
                "training_defaults": json.loads(preset.training_defaults_json),
                "eval_options": json.loads(preset.eval_options_json),
                "export_options": json.loads(preset.export_options_json),
            },
            created_at=preset.created_at,
        )
