from __future__ import annotations

from typing import Any


def fallback_response(reason: str, contract: dict[str, Any]) -> dict[str, Any]:
    routes = contract["route_catalog"]["routes"]
    review_route = next((row["route_id"] for row in routes if row.get("is_unsafe")), routes[-1]["route_id"])
    return {
        "route": review_route,
        "task_type": "escalate",
        "requires_calculation": False,
        "requires_human_review": True,
        "confidence": 0.0,
        "fallback_reason": reason,
    }
