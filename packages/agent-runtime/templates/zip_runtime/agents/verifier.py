from __future__ import annotations

from typing import Any


def route_ids(contract: dict[str, Any]) -> list[str]:
    return [row["route_id"] for row in contract["route_catalog"]["routes"]]


def verify_router_output(output: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if output.get("route") not in route_ids(contract):
        errors.append("route_not_allowed")
    confidence = output.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("confidence_invalid")
    for key in ["route", "task_type", "requires_calculation", "requires_human_review", "confidence"]:
        if key not in output:
            errors.append(f"missing_{key}")
    return not errors, errors
