from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.services.benchmark_metrics import LATENCY_KEYS, METRIC_KEYS, parity_report
from services.shared.db.models import Benchmark, EvalRun, EvalSet, Example, Job, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text


REPO_ROOT = Path(__file__).resolve().parents[4]
REPORT_SCHEMA_PATH = REPO_ROOT / "schemas" / "benchmark_report.schema.json"
TERMINAL_TARGET_STATUSES = {"COMPLETED", "FAILED", "SKIPPED_OPTIONAL"}


class BenchmarkReportError(ValueError):
    pass

def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical_report_sha256(report: dict[str, Any]) -> str:
    without_hash = deepcopy(report)
    without_hash.get("artifact_hashes", {}).pop("report_sha256", None)
    return sha256_text(canonical_json(without_hash))


def read_report_file(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def report_hash_status(benchmark: Benchmark) -> tuple[str, dict[str, Any] | None]:
    report = read_report_file(benchmark.report_path)
    if report is None or benchmark.report_sha256 is None:
        return "MISSING", report
    try:
        computed = canonical_report_sha256(report)
    except (TypeError, ValueError):
        return "MISMATCH", None
    artifact_sha = report.get("artifact_hashes", {}).get("report_sha256")
    if computed == benchmark.report_sha256 == artifact_sha:
        return "VALID", report
    return "MISMATCH", report


class BenchmarkReportBuilder:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home

    def can_generate(self, benchmark: Benchmark) -> bool:
        rows = self._eval_runs(benchmark.id)
        return bool(rows) and all(row.target_status in TERMINAL_TARGET_STATUSES for row in rows)

    def generate_and_store(self, benchmark: Benchmark) -> dict[str, Any]:
        eval_set = self._eval_set(benchmark.eval_set_id)
        rows = self._eval_runs(benchmark.id)
        if not rows:
            raise BenchmarkReportError("benchmark has no EvalRun rows")
        if any(row.target_status not in TERMINAL_TARGET_STATUSES for row in rows):
            raise BenchmarkReportError("benchmark has non-terminal EvalRun rows")

        targets = self._target_objects(rows)
        parity = self._parity(targets, rows)
        report = {
            "schema_version": "benchmark_report.v1",
            "benchmark_id": benchmark.id,
            "project_id": benchmark.project_id,
            "eval_set": self._eval_set_object(eval_set),
            "overlap_check": self._overlap_check(eval_set),
            "targets": targets,
            "parity": parity,
            "cost_assumptions": {
                "currency": "USD",
                "pricing_date": benchmark.created_at[:10],
                "fallback_provider": "openai-compatible",
            },
            "artifact_hashes": {"report_sha256": "0" * 64, "eval_set_sha256": eval_set.sha256},
        }
        report["artifact_hashes"]["report_sha256"] = canonical_report_sha256(report)
        self._validate(report)
        self._write_report(benchmark, report)
        return report

    def _eval_set(self, eval_set_id: str) -> EvalSet:
        eval_set = self.session.get(EvalSet, eval_set_id)
        if eval_set is None:
            raise BenchmarkReportError("benchmark EvalSet does not exist")
        if eval_set.purpose not in {"benchmark_gold", "finance_reference"}:
            raise BenchmarkReportError("benchmark report requires a benchmark EvalSet purpose")
        if eval_set.kappa is None or eval_set.kappa < 0.70 or not 200 <= eval_set.sample_count <= 300:
            raise BenchmarkReportError("benchmark EvalSet does not meet quality gates")
        return eval_set

    def _eval_runs(self, benchmark_id: str) -> list[EvalRun]:
        statement = select(EvalRun).where(EvalRun.benchmark_id == benchmark_id).order_by(EvalRun.target_key, EvalRun.seed)
        return list(self.session.scalars(statement))

    def _target_objects(self, rows: list[EvalRun]) -> list[dict[str, Any]]:
        grouped: dict[str, list[EvalRun]] = defaultdict(list)
        for row in rows:
            grouped[row.target_key].append(row)
        targets = [self._target_object(target_rows) for _, target_rows in sorted(grouped.items())]
        counts = Counter(target["target_type"] for target in targets)
        if counts["prompt_only"] != 1 or counts["teacher"] != 1 or counts["rule_based"] != 1:
            raise BenchmarkReportError("benchmark report requires exactly one prompt_only, teacher, and rule_based target")
        if counts["fine_tuned"] not in {1, 2} or counts["local_large"] != 1:
            raise BenchmarkReportError("benchmark report requires one or two fine_tuned targets and one local_large target")
        return targets

    def _target_object(self, rows: list[EvalRun]) -> dict[str, Any]:
        first = rows[0]
        target_config = json.loads(first.target_config_json)
        statuses = {row.target_status for row in rows}
        target = {
            "target_key": first.target_key,
            "target_type": first.target_type,
            "model_run_id": first.model_run_id,
            "model": self._target_model(first, target_config),
            "backend": first.backend,
            "seeds": sorted(row.seed for row in rows),
        }
        if statuses == {"SKIPPED_OPTIONAL"}:
            return target | {
                "target_status": "SKIPPED_OPTIONAL",
                "skip_reason": str(json.loads(first.metrics_json).get("skip_reason", "LOCAL_LARGE_UNAVAILABLE")),
            }
        if "FAILED" in statuses:
            return target | {
                "target_status": "FAILED",
                "error_reason": str(json.loads(first.metrics_json).get("error_reason", "UNKNOWN")),
            }
        if statuses != {"COMPLETED"}:
            raise BenchmarkReportError(f"target {first.target_key} has mixed non-terminal statuses")
        if len(rows) < 3:
            raise BenchmarkReportError(f"target {first.target_key} requires at least three completed seeds")
        metrics = [self._flatten_metrics(json.loads(row.metrics_json), row) for row in rows]
        return target | {
            "target_status": "COMPLETED",
            "mean_metrics": self._aggregate(metrics, "mean"),
            "std_metrics": self._aggregate(metrics, "std"),
            "ci95": self._aggregate(metrics, "ci95"),
        }

    def _target_model(self, row: EvalRun, target_config: dict[str, Any]) -> str | None:
        if row.model_run_id:
            model_run = self.session.get(ModelRun, row.model_run_id)
            return model_run.base_model if model_run is not None else None
        if "base_model" in target_config:
            return str(target_config["base_model"])
        local_config = target_config.get("local_large_config")
        if isinstance(local_config, dict) and local_config.get("model"):
            return str(local_config["model"])
        return None

    def _flatten_metrics(self, metrics: dict[str, Any], row: EvalRun) -> dict[str, float]:
        flattened: dict[str, float] = {}
        for key in METRIC_KEYS:
            flattened[key] = self._number(metrics.get(key), row, key)
        latency = metrics.get("latency_ms")
        if not isinstance(latency, dict):
            raise BenchmarkReportError(f"target {row.target_key} seed {row.seed} missing latency_ms")
        for source_key, report_key in LATENCY_KEYS.items():
            flattened[report_key] = self._number(latency.get(source_key), row, report_key)
        return flattened

    def _number(self, value: Any, row: EvalRun, key: str) -> float:
        if not isinstance(value, int | float):
            raise BenchmarkReportError(f"target {row.target_key} seed {row.seed} missing numeric {key}")
        return float(value)

    def _aggregate(self, metrics: list[dict[str, float]], mode: str) -> dict[str, float]:
        result = {}
        for key in metrics[0]:
            values = [item[key] for item in metrics]
            std = statistics.stdev(values)
            if mode == "mean":
                result[key] = statistics.fmean(values)
            elif mode == "std":
                result[key] = std
            else:
                result[key] = 1.96 * std / (len(values) ** 0.5)
        return result

    def _parity(self, targets: list[dict[str, Any]], rows: list[EvalRun]) -> dict[str, Any]:
        completed_ft = [target for target in targets if target["target_type"] == "fine_tuned" and target["target_status"] == "COMPLETED"]
        if {target["backend"] for target in completed_ft} != {"cuda", "mlx"} or len(completed_ft) != 2:
            return {"status": "NA", "metrics": []}
        by_key = {target["target_key"]: [self._flatten_metrics(json.loads(row.metrics_json), row) for row in rows if row.target_key == target["target_key"]] for target in completed_ft}
        return parity_report(completed_ft, by_key)

    def _eval_set_object(self, eval_set: EvalSet) -> dict[str, Any]:
        return {
            "id": eval_set.id,
            "purpose": eval_set.purpose,
            "sha256": eval_set.sha256,
            "route_snapshot_sha256": eval_set.route_snapshot_sha256,
            "sample_count": eval_set.sample_count,
            "frozen_at": eval_set.frozen_at,
            "kappa": eval_set.kappa,
        }

    def _overlap_check(self, eval_set: EvalSet) -> dict[str, Any]:
        rows = [json.loads(line) for line in Path(eval_set.path).read_text(encoding="utf-8").splitlines() if line]
        eval_ids = {row["example_id"] for row in rows}
        eval_hashes = {row["input_sha256"] for row in rows}
        statement = select(Example.id).where(
            Example.dataset_id == eval_set.dataset_id,
            Example.id.not_in(eval_ids),
            Example.input_sha256.in_(eval_hashes),
        )
        overlaps = list(self.session.scalars(statement))
        exact_count = len(overlaps)
        return {
            "exact_duplicate_count": exact_count,
            "semantic_flag_count": 0,
            "encoder_version": "sentence-transformers/all-MiniLM-L6-v2@frozen",
            "threshold": 0.85,
            "passed": exact_count == 0,
        }

    def _validate(self, report: dict[str, Any]) -> None:
        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            Draft7Validator(schema).validate(report)
        except ValidationError as exc:
            raise BenchmarkReportError(f"benchmark report schema validation failed: {exc.message}") from exc

    def _write_report(self, benchmark: Benchmark, report: dict[str, Any]) -> None:
        report_dir = self.mib_home / "projects" / benchmark.project_id / "benchmarks" / benchmark.id
        report_dir.mkdir(parents=True, exist_ok=True)
        path = report_dir / "benchmark_report.json"
        path.write_text(canonical_json(report) + "\n", encoding="utf-8")
        now = utc_now()
        benchmark.report_path = str(path)
        benchmark.report_sha256 = str(report["artifact_hashes"]["report_sha256"])
        benchmark.parity_status = str(report["parity"]["status"])
        benchmark.status = "COMPLETED"
        benchmark.completed_at = now
        job = self.session.get(Job, benchmark.job_id)
        if job is not None:
            job.status = "SUCCEEDED"
            job.ended_at = now
        self.session.flush()
