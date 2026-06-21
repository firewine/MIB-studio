from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

from services.shared.db.models import Benchmark, Credential, Dataset, EvalRun, Example, Job, ModelRun, Project, ProjectRoute
from services.shared.db.repositories.dataset_store import DatasetExampleInput, DatasetStore, canonical_json, new_id, sha256_text
from services.shared.db.repositories.eval_store import EvalSetStore
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.eval import EvalTask, run_benchmark_eval_job


ROUTES = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


@dataclass(frozen=True)
class BenchmarkFixture:
    project_id: str
    dataset_id: str
    eval_set_id: str
    benchmark_id: str
    job_id: str
    targets: list[dict[str, Any]]
    seeds: list[int]


class FakeEvaluator:
    def __init__(self) -> None:
        self.tasks: list[EvalTask] = []

    def run(self, task: EvalTask) -> dict[str, Any]:
        self.tasks.append(task)
        offset = (task.seed % 10) / 1000
        return {
            "route_accuracy": round(0.91 + offset, 4),
            "route_accuracy_macro": round(0.90 + offset, 4),
            "task_type_accuracy": round(0.88 + offset, 4),
            "unsafe_recall": round(0.96 + offset, 4),
            "safe_precision": round(0.98 + offset, 4),
            "requires_calculation_accuracy": round(0.89 + offset, 4),
            "requires_calculation_f1": round(0.87 + offset, 4),
            "requires_human_review_accuracy": round(0.94 + offset, 4),
            "requires_human_review_f1": round(0.93 + offset, 4),
            "json_valid_rate": 1.0,
            "schema_adherence": 1.0,
            "verifier_pass_rate": 0.97,
            "fallback_rate": 0.0,
            "latency_ms": {"p50": 380 + task.seed % 10, "p95": 790 + task.seed % 10, "p99": 1120 + task.seed % 10},
            "cost_per_task_usd": 0.0001,
            "effective_cost_per_task_usd": 0.0001,
            "invalid_outputs": {"invalid_json": 0, "schema_failed": 0, "route_not_allowed": 0, "missing_required_field": 0},
        }


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "eval_runner.db"
    command.upgrade(alembic_config(db_path), "head")
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return f"sqlite:///{db_path}"


def test_benchmark_eval_runner_creates_required_target_seed_rows_and_skips_unavailable_local_large(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    evaluator = FakeEvaluator()
    try:
        with factory() as session:
            fixture = create_benchmark_fixture(session, mib_home, fine_tuned_backends=("cuda",), include_local_large=False)
            assert run_benchmark_eval_job(session, fixture.job_id, evaluator=evaluator, local_large_available=False) == fixture.benchmark_id
            session.commit()

        with factory() as session:
            rows = session.query(EvalRun).filter_by(benchmark_id=fixture.benchmark_id).order_by(EvalRun.target_key, EvalRun.seed).all()
            benchmark = session.get(Benchmark, fixture.benchmark_id)
            job = session.get(Job, fixture.job_id)
            assert benchmark is not None
            assert job is not None
            assert benchmark.status == "RUNNING"
            assert job.status == "RUNNING"
            assert len(rows) == 13
            completed = [row for row in rows if row.target_status == "COMPLETED"]
            skipped = [row for row in rows if row.target_status == "SKIPPED_OPTIONAL"]
            assert len(completed) == 12
            assert len(skipped) == 1
            assert skipped[0].target_key == "local_large_optional"
            assert skipped[0].seed == 0
            assert json.loads(skipped[0].metrics_json)["skip_reason"] == "LOCAL_LARGE_UNAVAILABLE"
            assert {task.target["target_key"] for task in evaluator.tasks} == {"prompt_gemma", "ft_cuda", "teacher_gpt", "rule_router"}
            sample_metrics = json.loads(completed[0].metrics_json)
            assert sample_metrics["route_accuracy"] >= 0.91
            assert set(sample_metrics["latency_ms"]) == {"p50", "p95", "p99"}
    finally:
        engine.dispose()


def test_benchmark_eval_runner_preserves_cuda_mlx_parity_fine_tuned_rows(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    evaluator = FakeEvaluator()
    try:
        with factory() as session:
            fixture = create_benchmark_fixture(session, mib_home, fine_tuned_backends=("cuda", "mlx"), include_local_large=False)
            run_benchmark_eval_job(session, fixture.job_id, evaluator=evaluator, local_large_available=False)
            session.commit()

        with factory() as session:
            rows = session.query(EvalRun).filter_by(benchmark_id=fixture.benchmark_id, target_type="fine_tuned").order_by(EvalRun.target_key, EvalRun.seed).all()
            assert len(rows) == 6
            assert {row.backend for row in rows} == {"cuda", "mlx"}
            assert {row.target_key for row in rows} == {"ft_cuda", "ft_mlx"}
            assert {json.loads(row.target_config_json)["model_run_id"] for row in rows} == {target["model_run_id"] for target in fixture.targets if target["target_type"] == "fine_tuned"}
    finally:
        engine.dispose()


def test_benchmark_eval_runner_runs_available_local_large_for_each_seed(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    evaluator = FakeEvaluator()
    try:
        with factory() as session:
            fixture = create_benchmark_fixture(session, mib_home, fine_tuned_backends=("cuda",), include_local_large=True)
            run_benchmark_eval_job(session, fixture.job_id, evaluator=evaluator, local_large_available=True)
            session.commit()

        with factory() as session:
            rows = session.query(EvalRun).filter_by(benchmark_id=fixture.benchmark_id).all()
            local_rows = [row for row in rows if row.target_type == "local_large"]
            assert len(rows) == 15
            assert len(local_rows) == 3
            assert {row.seed for row in local_rows} == {42, 123, 456}
            assert {row.target_status for row in local_rows} == {"COMPLETED"}
            assert {task.target["target_type"] for task in evaluator.tasks if task.target["target_key"] == "local_large_q4"} == {"local_large"}
    finally:
        engine.dispose()


def create_benchmark_fixture(
    session: Any,
    mib_home: Path,
    *,
    fine_tuned_backends: tuple[str, ...],
    include_local_large: bool,
) -> BenchmarkFixture:
    now = "2026-01-01T00:00:00.000Z"
    project = Project(id=new_id(), name="Eval Runner Project", preset_id="router.basic.v1", created_at=now, updated_at=now)
    session.add(project)
    for index, route_id in enumerate(ROUTES):
        session.add(
            ProjectRoute(
                id=new_id(),
                project_id=project.id,
                route_id=route_id,
                description=f"{route_id} route",
                is_unsafe=1 if route_id.startswith("blocked") else 0,
                created_at=f"2026-01-01T00:00:{index:02d}.000Z",
            )
        )
    session.flush()

    dataset_store = DatasetStore(session, mib_home)
    route_snapshot = dataset_store.route_snapshot(project.id)
    route_snapshot_json = canonical_json(route_snapshot)
    dataset = dataset_store.create_dataset(
        project_id=project.id,
        version=1,
        status="APPROVED",
        examples=benchmark_examples(),
        route_snapshot_json=route_snapshot_json,
        route_snapshot_sha256=sha256_text(route_snapshot_json),
        created_at=now,
    )
    dataset.frozen_at = now
    examples = session.query(Example).filter_by(dataset_id=dataset.id).order_by(Example.row_index.asc()).all()
    for example in examples:
        example.review_status = "APPROVED"
        example.approved = 1
    eval_set = EvalSetStore(session, mib_home).create_eval_set(
        project_id=project.id,
        dataset_id=dataset.id,
        purpose="benchmark_gold",
        examples=examples,
        route_snapshot_sha256=dataset.route_snapshot_sha256,
        labeler_ids_json=canonical_json(["domain_labeler", "security_labeler", "tie_breaker"]),
        kappa=0.78,
        frozen_at=now,
        created_at=now,
    )
    credential = Credential(
        id=new_id(),
        provider="openai_compatible",
        base_url="https://teacher.example.test/v1",
        keychain_ref="keychain://teacher",
        created_at=now,
    )
    session.add(credential)
    model_runs = {backend: create_model_run(session, project.id, dataset, backend, now) for backend in fine_tuned_backends}
    targets = benchmark_targets(model_runs=model_runs, credential_id=credential.id, include_local_large=include_local_large)
    seeds = [42, 123, 456]
    benchmark_id = new_id()
    job = Job(
        id=new_id(),
        project_id=project.id,
        type="benchmark",
        resource_class="gpu_exclusive",
        status="QUEUED",
        priority=0,
        params_json=canonical_json({"benchmark_id": benchmark_id, "eval_set_id": eval_set.id, "targets": targets, "seeds": seeds}),
        attempt_count=0,
        eval_set_id=eval_set.id,
        trace_id="trace_eval_runner",
        created_at=now,
    )
    session.add(job)
    session.flush()
    session.add(Benchmark(id=benchmark_id, project_id=project.id, eval_set_id=eval_set.id, job_id=job.id, status="QUEUED", created_at=now))
    session.flush()
    return BenchmarkFixture(
        project_id=project.id,
        dataset_id=dataset.id,
        eval_set_id=eval_set.id,
        benchmark_id=benchmark_id,
        job_id=job.id,
        targets=targets,
        seeds=seeds,
    )


def benchmark_examples(count: int = 200) -> list[DatasetExampleInput]:
    examples = []
    for index in range(count):
        route_id = ROUTES[index % len(ROUTES)]
        examples.append(
            DatasetExampleInput(
                input={"text": f"benchmark eval case {index}", "allowed_routes": ROUTES, "metadata": {"gold_index": index}},
                output={
                    "route": route_id,
                    "task_type": "block" if route_id.startswith("blocked") else "generate_report",
                    "requires_calculation": route_id == "finance_income",
                    "requires_human_review": route_id.startswith("blocked") or route_id == "human_review",
                    "confidence": 0.93,
                },
                source="user",
            )
        )
    return examples


def create_model_run(session: Any, project_id: str, dataset: Dataset, backend: str, now: str) -> ModelRun:
    config_json = canonical_json({"schema_version": "training_config.v1", "backend": backend, "model_cache_subdir": "cache"})
    model_run = ModelRun(
        id=new_id(),
        project_id=project_id,
        dataset_id=dataset.id,
        base_model="google/gemma-2b-it",
        backend=backend,
        method="qlora" if backend == "cuda" else "mlx_lora",
        adapter_path=f"/tmp/mib-adapters/{backend}",
        adapter_sha256=("a" if backend == "cuda" else "b") * 64,
        artifact_manifest_sha256=("c" if backend == "cuda" else "d") * 64,
        status="SUCCEEDED",
        seed=42,
        config_json=config_json,
        config_hash=sha256_text(config_json),
        resumable=1,
        created_at=now,
    )
    session.add(model_run)
    session.flush()
    return model_run


def benchmark_targets(*, model_runs: dict[str, ModelRun], credential_id: str, include_local_large: bool) -> list[dict[str, Any]]:
    prompt_sha = sha256_text(Path("prompts/router.prompt_only.v1.txt").read_text(encoding="utf-8"))
    rules_path = "rules/router.routing_rules.v1.yaml"
    rules_sha = sha256_text(Path(rules_path).read_text(encoding="utf-8"))
    targets = [
        {
            "target_key": "prompt_gemma",
            "target_type": "prompt_only",
            "backend": "prompt_only",
            "base_model": "google/gemma-2b-it",
            "prompt_template_sha256": prompt_sha,
        },
        *[
            {
                "target_key": f"ft_{backend}",
                "target_type": "fine_tuned",
                "backend": backend,
                "model_run_id": model_run.id,
            }
            for backend, model_run in model_runs.items()
        ],
        {
            "target_key": "teacher_gpt",
            "target_type": "teacher",
            "backend": "teacher",
            "credential_id": credential_id,
            "teacher_base_url_origin": "https://teacher.example.test",
        },
        {
            "target_key": "rule_router",
            "target_type": "rule_based",
            "backend": "rule_based",
            "routing_rules_path": rules_path,
            "routing_rules_sha256": rules_sha,
        },
    ]
    if include_local_large:
        targets.append(
            {
                "target_key": "local_large_q4",
                "target_type": "local_large",
                "backend": "local_large",
                "required": False,
                "local_large_config": {"model": "local-large-q4"},
            }
        )
    return targets
