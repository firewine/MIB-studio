from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.db.models import Benchmark, EvalRun, Job, JobEvent
from services.shared.db.repositories.dataset_store import canonical_json, new_id


class BenchmarkStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def benchmark_for_job(self, job_id: str) -> Benchmark | None:
        return self.session.scalars(select(Benchmark).where(Benchmark.job_id == job_id).limit(1)).first()

    def eval_runs_for_benchmark(self, benchmark_id: str) -> list[EvalRun]:
        statement = (
            select(EvalRun)
            .where(EvalRun.benchmark_id == benchmark_id)
            .order_by(EvalRun.target_key.asc(), EvalRun.seed.asc())
        )
        return list(self.session.scalars(statement))

    def mark_benchmark_running(self, *, job: Job, benchmark: Benchmark, ts: str) -> None:
        job.status = "RUNNING"
        job.started_at = job.started_at or ts
        benchmark.status = "RUNNING"
        self.session.flush()

    def plan_eval_runs(
        self,
        *,
        benchmark: Benchmark,
        targets: list[dict[str, Any]],
        seeds: list[int],
        local_large_available: bool,
        local_large_skip_reason: str,
        ts: str,
    ) -> list[EvalRun]:
        existing = self.eval_runs_for_benchmark(benchmark.id)
        if existing:
            return existing

        planned = []
        for target in targets:
            if target["target_type"] == "local_large" and not local_large_available:
                planned.append(
                    self._add_eval_run(
                        benchmark_id=benchmark.id,
                        target=target,
                        seed=0,
                        status="SKIPPED_OPTIONAL",
                        metrics={"skip_reason": local_large_skip_reason},
                        ts=ts,
                    )
                )
                continue
            for seed in seeds:
                planned.append(
                    self._add_eval_run(
                        benchmark_id=benchmark.id,
                        target=target,
                        seed=seed,
                        status="QUEUED",
                        metrics={},
                        ts=ts,
                    )
                )
        self.session.flush()
        return planned

    def mark_eval_run_running(self, eval_run: EvalRun) -> None:
        eval_run.target_status = "RUNNING"
        self.session.flush()

    def mark_eval_run_completed(self, eval_run: EvalRun, metrics: dict[str, Any]) -> None:
        eval_run.metrics_json = canonical_json(metrics)
        eval_run.target_status = "COMPLETED"
        self.session.flush()

    def mark_failed(self, *, job: Job, benchmark: Benchmark, error_message: str, ts: str) -> None:
        job.status = "FAILED"
        job.error_class = "UNKNOWN"
        job.error_message = error_message
        job.ended_at = ts
        benchmark.status = "FAILED"
        benchmark.completed_at = ts
        self.session.flush()

    def append_event(self, *, job: Job, ts: str, level: str, event_type: str, payload: dict[str, Any]) -> None:
        current_seq = self.session.scalar(select(func.max(JobEvent.seq)).where(JobEvent.job_id == job.id))
        self.session.add(
            JobEvent(
                id=new_id(),
                job_id=job.id,
                seq=int(current_seq or 0) + 1,
                ts=ts,
                level=level,
                event_type=event_type,
                payload_json=canonical_json(payload),
                trace_id=job.trace_id,
            )
        )
        self.session.flush()

    def _add_eval_run(
        self,
        *,
        benchmark_id: str,
        target: dict[str, Any],
        seed: int,
        status: str,
        metrics: dict[str, Any],
        ts: str,
    ) -> EvalRun:
        eval_run = EvalRun(
            id=new_id(),
            benchmark_id=benchmark_id,
            model_run_id=target.get("model_run_id"),
            target_key=str(target["target_key"]),
            target_type=str(target["target_type"]),
            backend=str(target["backend"]),
            target_status=status,
            target_config_json=canonical_json(target),
            seed=seed,
            credential_id=target.get("credential_id"),
            metrics_json=canonical_json(metrics),
            created_at=ts,
        )
        self.session.add(eval_run)
        return eval_run
