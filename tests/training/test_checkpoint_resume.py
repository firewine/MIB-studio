from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from services.api.app.core.config import Settings
from services.api.app.core.errors import APIError
from services.api.app.main import create_app
from services.api.app.schemas.job import ResumeJobRequest
from services.api.app.services.job_control_service import JobControlService
from services.shared.db.models import AuditEvent, Checkpoint, Dataset, Job, JobEvent, JobResource, ModelRun, Project, ProjectRoute
from services.shared.db.repositories.dataset_store import DatasetExampleInput, DatasetStore, canonical_json, sha256_text
from services.shared.db.repositories.training_store import TrainingRunInput, TrainingStore
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.checkpoint_writer import CheckpointWriteInput, write_checkpoint


ROUTES = ["finance_income", "risk_summary", "investment_advice_block", "human_review", "blocked_pii", "blocked_unsupported"]
NOW = "2026-01-01T00:00:00.000Z"


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "checkpoint_resume.db"
    command.upgrade(alembic_config(db_path), "head")
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return f"sqlite:///{db_path}"


def client_for(database_url: str, mib_home: Path) -> httpx.AsyncClient:
    settings = Settings(
        app_env="production",
        dev_auth="bootstrap",
        bootstrap_token="test-token",
        database_url=database_url,
        mib_home=mib_home,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://127.0.0.1:8910")


def auth_headers() -> dict[str, str]:
    return {"host": "127.0.0.1:8910", "authorization": "Bearer test-token"}


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


def create_train_fixture(database_url: str, mib_home: Path, *, status: str = "FAILED") -> tuple[str, str, str]:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            project = Project(id="project_1", name="Checkpoint Project", preset_id="router.basic.v1", created_at=NOW, updated_at=NOW)
            session.add(project)
            for index, route_id in enumerate(ROUTES):
                session.add(
                    ProjectRoute(
                        id=f"route_{index}",
                        project_id=project.id,
                        route_id=route_id,
                        description=f"{route_id} route",
                        is_unsafe=1 if route_id.startswith("blocked") else 0,
                        created_at=NOW,
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
                created_at=NOW,
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
                    job_params={"dataset_id": dataset.id, "base_model": "google/gemma-2b-it", "backend": "cuda", "training_preset": "quick", "seed": 123},
                    idempotency_key=None,
                    idempotency_body_sha256=None,
                    idempotency_expires_at=None,
                    trace_id="trace_1",
                    created_at=NOW,
                )
            )
            rows.job.status = status
            rows.model_run.status = status
            rows.job.attempt_count = 1 if status in {"FAILED", "INTERRUPTED", "RUNNING"} else 0
            if status == "RUNNING":
                rows.job.started_at = NOW
                rows.model_run.started_at = NOW
            session.commit()
            return rows.job.id, rows.model_run.id, dataset.id
    finally:
        engine.dispose()


def dataset_examples() -> list[DatasetExampleInput]:
    rows = []
    for index in range(20):
        route_id = ROUTES[index % len(ROUTES)]
        rows.append(
            DatasetExampleInput(
                input={"text": f"checkpoint row {index}", "allowed_routes": ROUTES},
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
    return rows


def write_test_checkpoint(database_url: str, mib_home: Path, job_id: str, model_run_id: str, *, optimizer_rng: bool = True) -> str:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            dataset = session.get(Dataset, str(model_run.dataset_id)) if model_run is not None else None
            assert model_run is not None
            assert dataset is not None
            checkpoint = write_checkpoint(
                session,
                mib_home / "projects" / model_run.project_id / "runs" / model_run.id,
                CheckpointWriteInput(
                    job_id=job_id,
                    model_run_id=model_run.id,
                    dataset_id=dataset.id,
                    dataset_version=dataset.version,
                    training_config_hash=model_run.config_hash,
                    step=100,
                    adapter_filename="adapter.safetensors",
                    adapter_bytes=b"checkpoint adapter bytes",
                    trainer_backend="llamafactory",
                    loss=0.25,
                    optimizer_state_bytes=b"optimizer" if optimizer_rng else None,
                    rng_state_json={"seed": 123} if optimizer_rng else None,
                    trainer_state={"global_step": 100},
                    created_at=NOW,
                ),
            )
            session.commit()
            return checkpoint.id
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_cancel_queued_train_marks_job_and_model_run_cancelled(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_train_fixture(database_url, mib_home, status="QUEUED")

    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.delete(f"/jobs/{job_id}", headers=auth_headers()))

    assert response.status_code == 202, response.text
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancel_requested"] is False

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert session.get(Job, job_id).status == "CANCELLED"
            assert session.get(ModelRun, model_run_id).status == "CANCELLED"
            event = session.scalars(select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.event_type == "status_change")).one()
            assert json.loads(event.payload_json)["status"] == "CANCELLED"
    finally:
        engine.dispose()


def test_cancel_running_sets_cancel_requested_without_terminal_state(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_train_fixture(database_url, mib_home, status="RUNNING")

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            response = JobControlService(session, mib_home).cancel_job(job_id)
            session.commit()
            assert response.status == "RUNNING"
            assert response.cancel_requested is True

        with factory() as session:
            job = session.get(Job, job_id)
            model_run = session.get(ModelRun, model_run_id)
            assert job.status == "RUNNING"
            assert job.cancel_requested_at is not None
            assert model_run.status == "RUNNING"
            assert TrainingStore(session).cancel_requested(job_id) is True
    finally:
        engine.dispose()


def test_checkpoint_writer_records_artifact_metrics_and_best_checkpoint(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, dataset_id = create_train_fixture(database_url, mib_home, status="RUNNING")
    checkpoint_id = write_test_checkpoint(database_url, mib_home, job_id, model_run_id)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            checkpoint = session.get(ModelRun, model_run_id).best_checkpoint_id
            assert checkpoint == checkpoint_id
            checkpoint_model = session.get(ModelRun, model_run_id)
            assert checkpoint_model.resumable == 1
            db_checkpoint = session.get(Checkpoint, checkpoint_id)
            assert db_checkpoint.dataset_id == dataset_id
            metrics = json.loads(db_checkpoint.metrics_json)
            assert metrics["step"] == 100
            assert metrics["loss"] == 0.25
            assert metrics["optimizer_state_present"] is True
            assert metrics["rng_state_present"] is True
            assert Path(db_checkpoint.path, "adapter.safetensors").is_file()
            assert Path(db_checkpoint.path, "manifest.json").is_file()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("dataset", "CHECKPOINT_DATASET_MISMATCH"),
        ("config", "CHECKPOINT_CONFIG_MISMATCH"),
        ("missing", "CHECKPOINT_ARTIFACT_MISSING"),
    ],
)
def test_resume_rejects_invalid_checkpoint_without_child_job(tmp_path: Path, mutation: str, error_code: str) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_train_fixture(database_url, mib_home)
    checkpoint_id = write_test_checkpoint(database_url, mib_home, job_id, model_run_id)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            checkpoint = session.get(Checkpoint, checkpoint_id)
            if mutation == "dataset":
                checkpoint.dataset_version = 2
            elif mutation == "config":
                checkpoint.training_config_hash = "b" * 64
            else:
                shutil.rmtree(checkpoint.path)
            session.commit()

        with factory() as session:
            with pytest.raises(APIError) as exc_info:
                JobControlService(session, mib_home).resume_job(job_id, ResumeJobRequest(checkpoint_id=checkpoint_id), trace_id="trace_resume")
            assert exc_info.value.error_code == error_code
            assert session.scalar(select(func.count()).select_from(Job).where(Job.parent_job_id == job_id)) == 0
            assert session.get(Job, job_id).status == "FAILED"
    finally:
        engine.dispose()


def test_resume_from_checkpoint_creates_child_job_rebinds_model_run_and_audits_warning(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_train_fixture(database_url, mib_home)
    checkpoint_id = write_test_checkpoint(database_url, mib_home, job_id, model_run_id, optimizer_rng=False)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            response = JobControlService(session, mib_home).resume_job(job_id, ResumeJobRequest(checkpoint_id=checkpoint_id), trace_id="trace_resume")
            session.commit()
            child_job_id = response.child_job_id

        with factory() as session:
            parent = session.get(Job, job_id)
            child = session.get(Job, child_job_id)
            model_run = session.get(ModelRun, model_run_id)
            current = session.scalars(select(JobResource).where(JobResource.resource_type == "model_run", JobResource.resource_id == model_run_id, JobResource.is_current == 1)).one()
            audit = session.query(AuditEvent).filter_by(event_type="job_control", action="resume", resource_id=child_job_id).one()
            child_event = session.query(JobEvent).filter_by(job_id=child_job_id, event_type="status_change").one()
            params = json.loads(child.params_json)
            assert parent.status == "FAILED"
            assert child.status == "QUEUED"
            assert child.parent_job_id == job_id
            assert child.attempt_count == parent.attempt_count + 1
            assert params["model_run_id"] == model_run_id
            assert params["checkpoint_id"] == checkpoint_id
            assert current.job_id == child_job_id
            assert model_run.status == "QUEUED"
            assert json.loads(audit.details_json)["optimizer_rng_missing"] is True
            assert json.loads(child_event.payload_json)["phase"] == "resume_started"
    finally:
        engine.dispose()
