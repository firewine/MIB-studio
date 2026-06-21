from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from alembic import command
from alembic.config import Config

from services.shared.db.models import Job, JobEvent, JobResource, ModelRun, Project, ProjectRoute
from services.shared.db.repositories.dataset_store import DatasetExampleInput, DatasetStore, canonical_json, sha256_text
from services.shared.db.repositories.training_store import TrainingRunInput, TrainingStore
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.train_cuda import TrainCudaError, run_train_cuda_job
from services.worker.runtime.llamafactory import TrainerEvent


ROUTES = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


class FakeLlamaFactoryRunner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.config_paths: list[Path] = []

    def run(self, config_path: Path, *, run_dir: Path) -> list[TrainerEvent]:
        self.config_paths.append(config_path)
        if self.fail:
            raise RuntimeError("cuda kernel panic with raw stack details")
        adapter = run_dir / "adapter" / "adapter_model.safetensors"
        adapter.write_bytes(b"fake cuda adapter bytes")
        return [
            TrainerEvent(kind="log", message="llamafactory train started"),
            TrainerEvent(kind="metric", step=10, total_steps=30, loss=0.42, vram_gb=12.5, tokens_per_sec=115.2),
        ]


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "cuda_wrapper.db"
    command.upgrade(alembic_config(db_path), "head")
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return f"sqlite:///{db_path}"


def create_queued_cuda_run(database_url: str, mib_home: Path) -> tuple[str, str, str]:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            now = "2026-01-01T00:00:00.000Z"
            project = Project(id="project_1", name="CUDA Project", preset_id="router.basic.v1", created_at=now, updated_at=now)
            session.add(project)
            for index, route_id in enumerate(ROUTES):
                session.add(
                    ProjectRoute(
                        id=f"route_{index}",
                        project_id=project.id,
                        route_id=route_id,
                        description=f"{route_id} route",
                        is_unsafe=1 if route_id.startswith("blocked") else 0,
                        created_at=now,
                    )
                )
            session.flush()
            route_snapshot = [{"route_id": route_id, "description": f"{route_id} route", "is_unsafe": route_id.startswith("blocked")} for route_id in ROUTES]
            route_snapshot_json = canonical_json(route_snapshot)
            dataset = DatasetStore(session, mib_home).create_dataset(
                project_id=project.id,
                version=1,
                status="APPROVED",
                examples=dataset_examples(),
                route_snapshot_json=route_snapshot_json,
                route_snapshot_sha256=sha256_text(route_snapshot_json),
                created_at=now,
            )
            config = {
                "schema_version": "training_config.v1",
                "preset_id": "router.basic.v1",
                "dataset_id": dataset.id,
                "dataset_version": dataset.version,
                "route_snapshot_sha256": dataset.route_snapshot_sha256,
                "base_model": "google/gemma-2b-it",
                "backend": "cuda",
                "method": "qlora",
                "training_preset": "quick",
                "seed": 123,
                "model_cache_subdir": "google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad",
                "hardware_profile_id": "hardware_profile_1",
            }
            rows = TrainingStore(session).create_queued_training_run(
                TrainingRunInput(
                    project_id=project.id,
                    dataset_id=dataset.id,
                    base_model="google/gemma-2b-it",
                    backend="cuda",
                    method="qlora",
                    seed=123,
                    config=config,
                    job_params={
                        "preset_id": "router.basic.v1",
                        "dataset_id": dataset.id,
                        "base_model": "google/gemma-2b-it",
                        "backend": "cuda",
                        "training_preset": "quick",
                        "seed": 123,
                    },
                    idempotency_key=None,
                    idempotency_body_sha256=None,
                    idempotency_expires_at=None,
                    trace_id="trace_1",
                    created_at=now,
                )
            )
            session.commit()
            return rows.job.id, rows.model_run.id, dataset.id
    finally:
        engine.dispose()


def dataset_examples() -> list[DatasetExampleInput]:
    examples = []
    for index in range(20):
        route_id = ROUTES[index % len(ROUTES)]
        examples.append(
            DatasetExampleInput(
                input={"text": f"training row {index}", "allowed_routes": ROUTES, "metadata": {"row": index}},
                output={
                    "route": route_id,
                    "task_type": "block" if route_id.startswith("blocked") else "generate_report",
                    "requires_calculation": route_id == "finance_income",
                    "requires_human_review": route_id.startswith("blocked") or route_id == "human_review",
                    "confidence": 0.9,
                },
                source="user",
            )
        )
    return examples


def test_cuda_wrapper_writes_llamafactory_config_events_and_adapter_manifest(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, dataset_id = create_queued_cuda_run(database_url, mib_home)
    runner = FakeLlamaFactoryRunner()

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert run_train_cuda_job(session, mib_home, job_id, runner=runner) == model_run_id
            session.commit()

        run_dir = mib_home / "projects" / "project_1" / "runs" / model_run_id
        backend_config = yaml.safe_load((run_dir / "backend_config.yaml").read_text(encoding="utf-8"))
        assert normalized_config(backend_config) == yaml.safe_load(
            Path("examples/fixtures/llamafactory_config.golden.yaml").read_text(encoding="utf-8")
        )
        train_config = json.loads((run_dir / "train_config.json").read_text(encoding="utf-8"))
        assert train_config["job_id"] == job_id
        assert train_config["dataset_sha256"]
        train_rows = [json.loads(line) for line in (run_dir / "dataset" / "llamafactory" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
        valid_rows = [json.loads(line) for line in (run_dir / "dataset" / "llamafactory" / "valid.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(train_rows) == 18
        assert len(valid_rows) == 2
        dataset_info = json.loads((run_dir / "dataset" / "llamafactory" / "dataset_info.json").read_text(encoding="utf-8"))
        assert "mib_router_" + dataset_id in dataset_info

        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            job = session.get(Job, job_id)
            resource = session.get(JobResource, job_id)
            assert model_run is not None
            assert job is not None
            assert resource is not None
            assert model_run.status == "SUCCEEDED"
            assert model_run.adapter_path == str(run_dir / "adapter")
            assert model_run.adapter_sha256 is not None
            assert model_run.artifact_manifest_sha256 == sha256_text((run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert job.status == "SUCCEEDED"
            assert resource.resource_type == "model_run"
            events = session.query(JobEvent).filter_by(job_id=job_id).order_by(JobEvent.seq.asc()).all()
            payloads = [json.loads(event.payload_json) for event in events]
            assert any(event.event_type == "log" and payload["message"] == "llamafactory train started" for event, payload in zip(events, payloads, strict=True))
            metric = next(payload for event, payload in zip(events, payloads, strict=True) if event.event_type == "metric")
            assert metric["loss"] == 0.42
            assert metric["tokens_per_sec"] == 115.2
            assert any(event.event_type == "artifact" for event in events)
    finally:
        engine.dispose()


def test_cuda_wrapper_failure_marks_job_and_model_run_failed(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_cuda_run(database_url, mib_home)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(TrainCudaError):
                run_train_cuda_job(session, mib_home, job_id, runner=FakeLlamaFactoryRunner(fail=True))
            session.commit()

        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            job = session.get(Job, job_id)
            assert model_run is not None
            assert job is not None
            assert model_run.status == "FAILED"
            assert job.status == "FAILED"
            assert job.error_class == "UNKNOWN"
            assert "cuda kernel panic" in str(job.error_message)
            assert "\n" not in str(job.error_message)
    finally:
        engine.dispose()


def normalized_config(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    normalized["model_name_or_path"] = "<model_cache_path>"
    normalized["dataset"] = "<dataset_name>"
    normalized["dataset_dir"] = "<dataset_dir>"
    normalized["output_dir"] = "<adapter_dir>"
    return normalized
