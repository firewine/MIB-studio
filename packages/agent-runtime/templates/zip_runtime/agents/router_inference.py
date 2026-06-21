from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


CALCULATION_HINTS = {
    "calculate",
    "calculation",
    "income",
    "revenue",
    "salary",
    "tax",
    "profit",
    "expense",
    "margin",
    "cost",
}
LOW_CONFIDENCE_HINTS = {"ambiguous", "unclear", "uncertain", "maybe", "low confidence"}
HUMAN_REVIEW_HINTS = {"human", "review", "manual", "escalate", "approval", "compliance"}
BLOCKED_HINTS = {"blocked", "unsafe", "pii", "ssn", "passport", "unsupported", "illegal", "exploit"}
ROUTE_KEYWORDS = {
    "finance_income": {"finance", "income", "revenue", "salary", "tax", "profit"},
    "risk_summary": {"risk", "summary", "exposure", "downside", "volatility"},
    "investment_advice_block": {"investment", "advice", "stock", "buy", "sell", "portfolio"},
    "human_review": HUMAN_REVIEW_HINTS,
    "blocked_pii": {"pii", "ssn", "passport", "private", "personal"},
    "blocked_unsupported": {"unsupported", "illegal", "exploit", "hack", "malware"},
}


@dataclass(frozen=True)
class RouteDefinition:
    route_id: str
    description: str
    is_unsafe: bool
    order: int


def run_router_inference(
    *,
    input_payload: dict[str, Any],
    contract: dict[str, Any],
    adapter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del adapter
    routes = _allowed_routes(input_payload, _catalog_routes(contract))
    if not routes:
        raise ValueError("contract route_catalog must include at least one route")

    normalized = _normalize_text(str(input_payload.get("text", "")).strip())
    route, matched = _select_route(normalized, routes)
    low_confidence = any(hint in normalized for hint in LOW_CONFIDENCE_HINTS)
    human_review = _requires_human_review(route, normalized)
    return {
        "route": route.route_id,
        "task_type": _task_type(route, human_review),
        "requires_calculation": _requires_calculation(normalized),
        "requires_human_review": human_review,
        "confidence": _confidence(matched=matched, low_confidence=low_confidence),
    }


def _catalog_routes(contract: dict[str, Any]) -> list[RouteDefinition]:
    rows = contract.get("route_catalog", {}).get("routes", [])
    routes: list[RouteDefinition] = []
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, dict) or not isinstance(row.get("route_id"), str):
            continue
        routes.append(
            RouteDefinition(
                route_id=row["route_id"],
                description=str(row.get("description", "")),
                is_unsafe=bool(row.get("is_unsafe")),
                order=int(row.get("order", index)),
            )
        )
    return sorted(routes, key=lambda item: item.order)


def _allowed_routes(input_payload: dict[str, Any], catalog: list[RouteDefinition]) -> list[RouteDefinition]:
    requested = input_payload.get("allowed_routes")
    if not isinstance(requested, list):
        return catalog
    requested_ids = {item for item in requested if isinstance(item, str)}
    filtered = [route for route in catalog if route.route_id in requested_ids]
    return filtered if filtered else catalog


def _select_route(text: str, routes: list[RouteDefinition]) -> tuple[RouteDefinition, bool]:
    for route in routes:
        if _route_name_matches(route.route_id, text):
            return route, True
    text_tokens = set(re.findall(r"[a-z0-9]+", text))
    best_route = routes[0]
    best_score = 0
    for route in routes:
        keywords = ROUTE_KEYWORDS.get(route.route_id, set()) | set(re.findall(r"[a-z0-9]+", route.description.lower()))
        score = len(text_tokens & keywords)
        if score > best_score:
            best_route = route
            best_score = score
    return best_route, best_score > 0


def _route_name_matches(route_id: str, text: str) -> bool:
    candidates = {route_id, route_id.replace("_", " "), route_id.replace("_", "-")}
    return any(candidate in text for candidate in candidates)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _requires_calculation(text: str) -> bool:
    if re.search(r"[$]?\d", text):
        return True
    return any(hint in text for hint in CALCULATION_HINTS)


def _requires_human_review(route: RouteDefinition, text: str) -> bool:
    if route.is_unsafe or route.route_id.startswith("blocked") or route.route_id.endswith("_block"):
        return True
    if route.route_id == "human_review":
        return True
    return any(hint in text for hint in HUMAN_REVIEW_HINTS | BLOCKED_HINTS)


def _task_type(route: RouteDefinition, human_review: bool) -> str:
    if route.is_unsafe or route.route_id.startswith("blocked") or route.route_id.endswith("_block"):
        return "block"
    if route.route_id == "human_review" or human_review:
        return "escalate"
    if "advice" in route.route_id or route.route_id.startswith("finance"):
        return "provide_advice"
    return "generate_report"


def _confidence(*, matched: bool, low_confidence: bool) -> float:
    if low_confidence:
        return 0.42
    return 0.94 if matched else 0.74
