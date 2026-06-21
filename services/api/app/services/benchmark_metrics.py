from __future__ import annotations

import math
import statistics
from typing import Any


METRIC_KEYS = (
    "route_accuracy",
    "route_accuracy_macro",
    "task_type_accuracy",
    "unsafe_recall",
    "safe_precision",
    "requires_calculation_accuracy",
    "requires_calculation_f1",
    "requires_human_review_accuracy",
    "requires_human_review_f1",
    "json_valid_rate",
    "schema_adherence",
    "verifier_pass_rate",
    "fallback_rate",
    "cost_per_task_usd",
    "effective_cost_per_task_usd",
)
LATENCY_KEYS = {"p50": "latency_p50_ms", "p95": "latency_p95_ms", "p99": "latency_p99_ms"}
PARITY_THRESHOLDS = {
    "route_accuracy": ("pp", 2.0),
    "task_type_accuracy": ("pp", 2.0),
    "unsafe_recall": ("pp", 1.5),
    "latency_p50_ms": ("relative_pct", 20.0),
    "cost_per_task_usd": ("relative_pct", 10.0),
}


def parity_report(targets: list[dict[str, Any]], metrics_by_target: dict[str, list[dict[str, float]]]) -> dict[str, Any]:
    completed_ft = [
        target for target in targets if target["target_type"] == "fine_tuned" and target["target_status"] == "COMPLETED"
    ]
    if {target["backend"] for target in completed_ft} != {"cuda", "mlx"} or len(completed_ft) != 2:
        return {"status": "NA", "metrics": []}
    metric_rows = [
        _parity_metric(name, metrics_by_target[completed_ft[0]["target_key"]], metrics_by_target[completed_ft[1]["target_key"]])
        for name in PARITY_THRESHOLDS
    ]
    status = "FAIL" if any(item["failed"] for item in metric_rows) else "PASS"
    return {"status": status, "metrics": [{key: item[key] for key in ("name", "delta_pp", "p_value")} for item in metric_rows]}


def _parity_metric(name: str, left: list[dict[str, float]], right: list[dict[str, float]]) -> dict[str, Any]:
    left_values = [item[name] for item in left]
    right_values = [item[name] for item in right]
    left_mean = statistics.fmean(left_values)
    right_mean = statistics.fmean(right_values)
    kind, threshold = PARITY_THRESHOLDS[name]
    delta = abs(left_mean - right_mean) * 100 if kind == "pp" else _relative_delta_pct(left_mean, right_mean)
    p_value = _normal_p_value(left_values, right_values)
    return {"name": name, "delta_pp": delta, "p_value": p_value, "failed": delta > threshold and p_value < 0.05}


def _relative_delta_pct(left: float, right: float) -> float:
    baseline = max(abs(left), 1e-12)
    return abs(left - right) / baseline * 100


def _normal_p_value(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return 1.0
    variance = statistics.variance(left) / len(left) + statistics.variance(right) / len(right)
    if variance <= 0:
        return 0.0 if statistics.fmean(left) != statistics.fmean(right) else 1.0
    z = abs(statistics.fmean(left) - statistics.fmean(right)) / math.sqrt(variance)
    return math.erfc(z / math.sqrt(2))
