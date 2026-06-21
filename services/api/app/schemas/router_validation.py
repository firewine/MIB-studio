from __future__ import annotations

import re
from typing import Any

from services.api.app.schemas.dataset import RowValidationError


ROUTE_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
TASK_TYPES = {"generate_report", "provide_advice", "escalate", "block"}


def validate_router_example(
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    route_ids: list[str],
) -> list[RowValidationError]:
    errors = router_input_errors(input_payload)
    errors.extend(router_output_errors(output_payload))
    if input_payload.get("allowed_routes") != route_ids:
        errors.append(
            RowValidationError(
                field="input.allowed_routes",
                code="ROUTE_SNAPSHOT_MISMATCH",
                message="allowed_routes must match the locked project route order",
            )
        )
    if output_payload.get("route") not in route_ids:
        errors.append(
            RowValidationError(
                field="output.route",
                code="ROUTE_NOT_ALLOWED",
                message="output route must exist in the project route snapshot",
            )
        )
    return errors


def router_input_errors(value: dict[str, Any]) -> list[RowValidationError]:
    errors = additional_property_errors("input", value, {"text", "allowed_routes", "metadata"})
    text = value.get("text")
    if not isinstance(text, str) or not 1 <= len(text) <= 8000:
        errors.append(row_error("input.text", "text must be a string with length 1..8000"))
    routes = value.get("allowed_routes")
    if not isinstance(routes, list) or not 2 <= len(routes) <= 12:
        errors.append(row_error("input.allowed_routes", "allowed_routes must contain 2..12 route ids"))
    elif len(set(routes)) != len(routes):
        errors.append(row_error("input.allowed_routes", "allowed_routes must be unique"))
    elif any(not isinstance(route, str) or not ROUTE_ID_RE.fullmatch(route) for route in routes):
        errors.append(row_error("input.allowed_routes", "allowed_routes entries must match router route_id format"))
    metadata = value.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append(row_error("input.metadata", "metadata must be an object"))
    return errors


def router_output_errors(value: dict[str, Any]) -> list[RowValidationError]:
    errors = additional_property_errors(
        "output",
        value,
        {"route", "task_type", "requires_calculation", "requires_human_review", "confidence"},
    )
    route = value.get("route")
    if not isinstance(route, str) or not ROUTE_ID_RE.fullmatch(route):
        errors.append(row_error("output.route", "route must match router route_id format"))
    if value.get("task_type") not in TASK_TYPES:
        errors.append(row_error("output.task_type", "task_type must be a v0 router task type"))
    if type(value.get("requires_calculation")) is not bool:
        errors.append(row_error("output.requires_calculation", "requires_calculation must be boolean"))
    if type(value.get("requires_human_review")) is not bool:
        errors.append(row_error("output.requires_human_review", "requires_human_review must be boolean"))
    confidence = value.get("confidence")
    if not isinstance(confidence, int | float) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append(row_error("output.confidence", "confidence must be a number between 0 and 1"))
    return errors


def additional_property_errors(prefix: str, value: dict[str, Any], allowed: set[str]) -> list[RowValidationError]:
    return [
        row_error(f"{prefix}.{key}", f"additional property {key!r} is not allowed")
        for key in sorted(set(value) - allowed)
    ]


def row_error(field: str, message: str) -> RowValidationError:
    return RowValidationError(field=field, code="SCHEMA_VALIDATION_FAILED", message=message)
