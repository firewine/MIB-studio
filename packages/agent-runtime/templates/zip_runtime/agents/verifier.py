from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_SCHEMA_PATH = ROOT / "schemas" / "router_output.schema.json"


def verify_router_output(output: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    for error in sorted(Draft7Validator(schema).iter_errors(output), key=lambda item: list(item.path)):
        location = ".".join(str(item) for item in error.path) or "<root>"
        errors.append(f"output_schema: {location}: {error.message}")
    route = output.get("route")
    route_ids = {row["route_id"] for row in contract["route_catalog"]["routes"]}
    if isinstance(route, str) and route not in route_ids:
        errors.append(f"route_allowed: route '{route}' is not in contract route_catalog")
    threshold = confidence_threshold(contract)
    confidence = output.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and confidence < threshold:
        errors.append(f"confidence_threshold: confidence {confidence:.4f} below {threshold:.4f}")
    fallback_required = bool(errors) and contract.get("fallback", {}).get("enabled") is True
    return {
        "verifier_status": "PASS" if not errors else "FAIL",
        "verifier_errors": errors,
        "fallback_required": fallback_required,
        "fallback_used": False,
    }


def confidence_threshold(contract: dict[str, Any]) -> float:
    thresholds = [0.0]
    for verifier in contract.get("verifiers", []):
        if isinstance(verifier, dict) and verifier.get("name") == "confidence_threshold":
            value = verifier.get("config", {}).get("threshold")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                thresholds.append(float(value))
    fallback = contract.get("fallback", {})
    condition = fallback.get("condition", {}) if isinstance(fallback, dict) else {}
    value = condition.get("threshold") if condition.get("type") == "confidence_lt" else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        thresholds.append(float(value))
    return max(thresholds)
