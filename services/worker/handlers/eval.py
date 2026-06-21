from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.orm import Session

from services.shared.db.models import Benchmark, Dataset, EvalRun, EvalSet, Job, ModelRun
from services.shared.db.repositories.benchmark_store import BenchmarkStore


TARGET_KEY_RE = re.compile(r"^[a-z0-9_:-]{1,80}$")
TARGET_TYPES = {"prompt_only", "fine_tuned", "teacher", "rule_based", "local_large"}
BACKENDS = {"cuda", "mlx", "teacher", "rule_based", "prompt_only", "local_large"}
REQUIRED_ROUTER_METRICS = {
    "route_accuracy",
    "route_accuracy_macro",
    "task_type_accuracy",
    "unsafe_recall",
    "safe_precision",
    "json_valid_rate",
    "schema_adherence",
    "latency_ms",
}


@dataclass(frozen=True)
class EvalTask:
    eval_run_id: str
    benchmark_id: str
    eval_set_path: str
    eval_set_sha256: str
    target: dict[str, Any]
    seed: int


class EvalTargetRunner(Protocol):
    def run(self, task: EvalTask) -> dict[str, Any]:
        """Evaluate one target+seed against the frozen EvalSet and return Router metrics."""


class BenchmarkEvalError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def run_benchmark_eval_job(
    session: Session,
    job_id: str,
    *,
    evaluator: EvalTargetRunner,
    local_large_available: bool = False,
    local_large_skip_reason: str = "LOCAL_LARGE_UNAVAILABLE",
) -> str:
    store = BenchmarkStore(session)
    job = session.get(Job, job_id)
    if job is None:
        raise BenchmarkEvalError("JOB_NOT_FOUND", "Benchmark job does not exist.")
    benchmark = store.benchmark_for_job(job.id)
    if benchmark is None:
        raise BenchmarkEvalError("BENCHMARK_NOT_FOUND", "Benchmark row does not exist for job.")

    try:
        params = json.loads(job.params_json)
        eval_set = _eval_set_for_params(session, params)
        _validate_job(job, benchmark, params, eval_set)
        targets = _targets_for_params(session, params, eval_set)
        seeds = _seeds_for_params(params)
        ts = utc_now()
        store.mark_benchmark_running(job=job, benchmark=benchmark, ts=ts)
        eval_runs = store.plan_eval_runs(
            benchmark=benchmark,
            targets=targets,
            seeds=seeds,
            local_large_available=local_large_available,
            local_large_skip_reason=local_large_skip_reason,
            ts=ts,
        )
        total_runs = sum(1 for row in eval_runs if row.target_status != "SKIPPED_OPTIONAL")
        completed = 0
        for eval_run in eval_runs:
            if eval_run.target_status == "SKIPPED_OPTIONAL":
                continue
            store.mark_eval_run_running(eval_run)
            task = EvalTask(
                eval_run_id=eval_run.id,
                benchmark_id=benchmark.id,
                eval_set_path=eval_set.path,
                eval_set_sha256=eval_set.sha256,
                target=json.loads(eval_run.target_config_json),
                seed=eval_run.seed,
            )
            metrics = evaluator.run(task)
            _validate_router_metrics(metrics)
            store.mark_eval_run_completed(eval_run, metrics)
            completed += 1
            store.append_event(
                job=job,
                ts=utc_now(),
                level="info",
                event_type="metric",
                payload={
                    "phase": "eval_run_completed",
                    "benchmark_id": benchmark.id,
                    "target_key": eval_run.target_key,
                    "target_type": eval_run.target_type,
                    "backend": eval_run.backend,
                    "seed": eval_run.seed,
                    "completed_runs": completed,
                    "total_runs": total_runs,
                },
            )
        return benchmark.id
    except BenchmarkEvalError as exc:
        store.mark_failed(job=job, benchmark=benchmark, error_message=exc.message, ts=utc_now())
        raise
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        store.mark_failed(job=job, benchmark=benchmark, error_message=message.replace("\n", " ")[:500], ts=utc_now())
        raise BenchmarkEvalError("BENCHMARK_EVAL_FAILED", message.replace("\n", " ")[:500]) from exc


def _eval_set_for_params(session: Session, params: dict[str, Any]) -> EvalSet:
    eval_set = session.get(EvalSet, str(params.get("eval_set_id") or ""))
    if eval_set is None:
        raise BenchmarkEvalError("EVAL_SET_NOT_FOUND", "Benchmark EvalSet does not exist.")
    if eval_set.purpose not in {"benchmark_gold", "finance_reference"} or not eval_set.frozen_at:
        raise BenchmarkEvalError("EVAL_SET_INVALID", "Benchmark requires a frozen benchmark EvalSet.")
    if eval_set.kappa is None or eval_set.kappa < 0.70 or not 200 <= eval_set.sample_count <= 300:
        raise BenchmarkEvalError("EVAL_SET_INVALID", "Benchmark EvalSet does not meet M4 quality gates.")
    return eval_set


def _validate_job(job: Job, benchmark: Benchmark, params: dict[str, Any], eval_set: EvalSet) -> None:
    if job.type != "benchmark":
        raise BenchmarkEvalError("JOB_TYPE_UNSUPPORTED", "Job is not a benchmark job.")
    if job.status not in {"QUEUED", "RUNNING"} or benchmark.status not in {"QUEUED", "RUNNING"}:
        raise BenchmarkEvalError("BENCHMARK_NOT_RUNNABLE", "Benchmark job is not runnable.")
    if benchmark.id != str(params.get("benchmark_id") or benchmark.id):
        raise BenchmarkEvalError("BENCHMARK_PARAMS_INVALID", "Benchmark params benchmark_id does not match row.")
    if benchmark.eval_set_id != eval_set.id or job.eval_set_id != eval_set.id:
        raise BenchmarkEvalError("BENCHMARK_PARAMS_INVALID", "Benchmark EvalSet linkage is inconsistent.")


def _targets_for_params(session: Session, params: dict[str, Any], eval_set: EvalSet) -> list[dict[str, Any]]:
    raw_targets = [dict(target) for target in params.get("targets", [])]
    target_types = [target.get("target_type") for target in raw_targets]
    if "local_large" not in target_types:
        raw_targets.append({"target_key": "local_large_optional", "target_type": "local_large", "backend": "local_large", "required": False})
    _validate_target_cardinality(raw_targets)
    fine_tuned_base_model = _validate_fine_tuned_targets(session, raw_targets, eval_set)
    for target in raw_targets:
        _validate_target_shape(target, fine_tuned_base_model)
        if target["target_type"] == "local_large":
            target["required"] = False
    return raw_targets


def _validate_target_cardinality(targets: list[dict[str, Any]]) -> None:
    target_types = [target.get("target_type") for target in targets]
    target_keys = [target.get("target_key") for target in targets]
    for target_type in ["prompt_only", "teacher", "rule_based"]:
        if target_types.count(target_type) != 1:
            raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", f"{target_type} target must appear exactly once.")
    if target_types.count("fine_tuned") not in {1, 2}:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "fine_tuned target count must be one, or two for CUDA/MLX parity.")
    if target_types.count("local_large") > 1:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "local_large target may appear at most once.")
    if len(set(target_keys)) != len(target_keys):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "duplicate benchmark target_key.")
    fine_tuned_backends = {target.get("backend") for target in targets if target.get("target_type") == "fine_tuned"}
    if target_types.count("fine_tuned") == 2 and fine_tuned_backends != {"cuda", "mlx"}:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "CUDA/MLX parity requires exactly one cuda and one mlx fine_tuned target.")


def _validate_fine_tuned_targets(session: Session, targets: list[dict[str, Any]], eval_set: EvalSet) -> str:
    base_models = set()
    for target in targets:
        if target.get("target_type") != "fine_tuned":
            continue
        model_run = session.get(ModelRun, str(target.get("model_run_id") or ""))
        if model_run is None or model_run.status != "SUCCEEDED" or not model_run.adapter_sha256 or not model_run.adapter_path:
            raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "fine_tuned target requires a succeeded adapter ModelRun.")
        dataset = session.get(Dataset, model_run.dataset_id)
        if dataset is None or dataset.route_snapshot_sha256 != eval_set.route_snapshot_sha256:
            raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "fine_tuned target route snapshot must match EvalSet.")
        if target.get("backend") != model_run.backend:
            raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "fine_tuned target backend must match ModelRun backend.")
        base_models.add(model_run.base_model)
    if len(base_models) != 1:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "fine_tuned targets must share one base model family.")
    return next(iter(base_models))


def _validate_target_shape(target: dict[str, Any], fine_tuned_base_model: str) -> None:
    if not TARGET_KEY_RE.match(str(target.get("target_key") or "")):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "target_key must match BenchmarkTargetConfig.")
    if target.get("target_type") not in TARGET_TYPES or target.get("backend") not in BACKENDS:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "target_type/backend is unsupported.")
    expected_backend = {
        "prompt_only": "prompt_only",
        "teacher": "teacher",
        "rule_based": "rule_based",
        "local_large": "local_large",
    }
    target_type = str(target["target_type"])
    if target_type in expected_backend and target.get("backend") != expected_backend[target_type]:
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", f"{target_type} target requires backend={expected_backend[target_type]}.")
    if target_type == "prompt_only" and (target.get("base_model") != fine_tuned_base_model or not target.get("prompt_template_sha256")):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "prompt_only requires matching base_model and prompt_template_sha256.")
    if target_type == "teacher" and (not target.get("credential_id") or not target.get("teacher_base_url_origin")):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "teacher requires credential_id and teacher_base_url_origin.")
    if target_type == "rule_based" and (not target.get("routing_rules_path") or not target.get("routing_rules_sha256")):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "rule_based requires routing_rules_path and routing_rules_sha256.")


def _seeds_for_params(params: dict[str, Any]) -> list[int]:
    seeds = [int(seed) for seed in params.get("seeds", [])]
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise BenchmarkEvalError("BENCHMARK_TARGET_INVALID", "benchmark seeds must contain at least three distinct values.")
    return seeds


def _validate_router_metrics(metrics: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_ROUTER_METRICS - set(metrics))
    latency = metrics.get("latency_ms")
    if missing or not isinstance(latency, dict) or not {"p50", "p95", "p99"} <= set(latency):
        raise BenchmarkEvalError("BENCHMARK_METRICS_INVALID", "Router metrics must include required M4 metric fields and latency p50/p95/p99.")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
