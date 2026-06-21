from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTER_OUTPUT_SCHEMA_PATH = REPO_ROOT / "schemas" / "router_output.schema.json"


@dataclass(frozen=True)
class VerificationResult:
    verifier_status: str
    verifier_errors: list[str]
    fallback_required: bool
    fallback_used: bool = False

    @property
    def passed(self) -> bool:
        return self.verifier_status == "PASS"


def verify_router_output(
    *,
    output: Any,
    contract: dict[str, Any],
    approve_fallback: bool = False,
) -> VerificationResult:
    parsed_output, errors = _parse_output(output)
    if parsed_output is not None:
        errors.extend(_schema_errors(parsed_output))
        errors.extend(_route_allowed_errors(parsed_output, contract))
        errors.extend(_confidence_errors(parsed_output, contract))
    fallback_required = bool(errors) and _fallback_enabled(contract) and not approve_fallback
    fallback_used = bool(errors) and _fallback_enabled(contract) and approve_fallback
    return VerificationResult(
        verifier_status="PASS" if not errors else "FAIL",
        verifier_errors=errors,
        fallback_required=fallback_required,
        fallback_used=fallback_used,
    )


def _parse_output(output: Any) -> tuple[dict[str, Any] | None, list[str]]:
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            return None, [f"json_parse: {exc.msg}"]
    else:
        parsed = output
    if not isinstance(parsed, dict):
        return None, ["json_parse: output must be a JSON object"]
    return parsed, []


def _schema_errors(output: dict[str, Any]) -> list[str]:
    schema = json.loads(ROUTER_OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(output), key=lambda item: list(item.path)):
        errors.append(f"output_schema: {_format_schema_error(error)}")
    return errors


def _route_allowed_errors(output: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    routes = contract.get("route_catalog", {}).get("routes", [])
    allowed_routes = {route.get("route_id") for route in routes if isinstance(route, dict)}
    route = output.get("route")
    if isinstance(route, str) and route not in allowed_routes:
        return [f"route_allowed: route '{route}' is not in contract route_catalog"]
    return []


def _confidence_errors(output: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    confidence = output.get("confidence")
    if not isinstance(confidence, int | float) or isinstance(confidence, bool):
        return []
    threshold = _confidence_threshold(contract)
    if threshold is not None and confidence < threshold:
        return [f"confidence_threshold: confidence {confidence:.4f} below {threshold:.4f}"]
    return []


def _confidence_threshold(contract: dict[str, Any]) -> float | None:
    thresholds = []
    for verifier in contract.get("verifiers", []):
        if not isinstance(verifier, dict) or verifier.get("name") != "confidence_threshold":
            continue
        threshold = verifier.get("config", {}).get("threshold")
        if isinstance(threshold, int | float) and not isinstance(threshold, bool):
            thresholds.append(float(threshold))
    fallback = contract.get("fallback", {})
    condition = fallback.get("condition", {}) if isinstance(fallback, dict) else {}
    threshold = condition.get("threshold") if condition.get("type") == "confidence_lt" else None
    if isinstance(threshold, int | float) and not isinstance(threshold, bool):
        thresholds.append(float(threshold))
    return max(thresholds) if thresholds else None


def _fallback_enabled(contract: dict[str, Any]) -> bool:
    fallback = contract.get("fallback", {})
    return isinstance(fallback, dict) and fallback.get("enabled") is True


def _format_schema_error(error: ValidationError) -> str:
    path = ".".join(str(item) for item in error.path)
    location = path or "<root>"
    return f"{location}: {error.message}"
