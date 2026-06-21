from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from services.shared.db.models import Preset


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_PRESET_PATH = REPO_ROOT / "presets" / "router.basic.v1.yaml"
MODEL_CATALOG_PATH = REPO_ROOT / "presets" / "model_catalog.yaml"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_router_preset(path: Path = ROUTER_PRESET_PATH) -> dict[str, Any]:
    data = load_yaml(path)
    required = {"id", "name", "preset_type", "version", "base_model_options", "training_defaults"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"router preset missing fields: {', '.join(missing)}")
    if data["id"] != "router.basic.v1" or data["preset_type"] != "router":
        raise ValueError("M1 seed supports only router.basic.v1")
    return data


def load_model_catalog(path: Path = MODEL_CATALOG_PATH) -> dict[str, Any]:
    data = load_yaml(path)
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("model catalog must contain at least one model")
    return data


def preset_from_yaml(data: dict[str, Any], created_at: str | None = None) -> Preset:
    data_template = {
        "route_rules": data.get("route_rules", {}),
        "dataset": data.get("dataset", {}),
        "benchmark_taxonomy": data.get("benchmark_taxonomy", {}),
        "schemas": data.get("schemas", {}),
        "prompts": data.get("prompts", {}),
        "rules": data.get("rules", {}),
    }
    return Preset(
        id=str(data["id"]),
        name=str(data["name"]),
        preset_type=str(data["preset_type"]),
        version=int(data["version"]),
        base_model_options_json=canonical_json(data["base_model_options"]),
        data_template_json=canonical_json(data_template),
        training_defaults_json=canonical_json(data["training_defaults"]),
        eval_options_json=canonical_json(data.get("eval_options", {})),
        export_options_json=canonical_json(data.get("export_options", [])),
        created_at=created_at or utc_now(),
    )


def seed_router_preset(session: Session, path: Path = ROUTER_PRESET_PATH) -> Preset:
    data = load_router_preset(path)
    existing = session.get(Preset, str(data["id"]))
    if existing is not None:
        return existing
    preset = preset_from_yaml(data)
    session.add(preset)
    session.flush()
    return preset
