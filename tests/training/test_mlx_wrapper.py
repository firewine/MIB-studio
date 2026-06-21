from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config

from services.shared.db.models import Job, JobEvent, JobResource, ModelRun, Project, ProjectRoute
from services.shared.db.repositories.dataset_store import DatasetExampleInput, DatasetStore, canonical_json, sha256_text
from services.shared.db.repositories.training_store import TrainingRunInput, TrainingStore
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.train_mlx import TrainMlxError, run_train_mlx_job
from services.worker.runtime.mlx_lm import MlxTrainerEvent


ROUTES = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


class FakeMlxRunner:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.config_paths: list[Path] = []

    def run(self, config_path: Path, *, run_dir: Path) -> list[MlxTrainerEvent]:
        self.config_paths.append(config_path)
        if self.fail:
            raise RuntimeError("mlx metal failure with raw stack details")
        (run_dir / "adapter" / "adapters.npz").write_bytes(b"fake mlx adapter weights")
        (run_dir / "adapter" / "adapter_config.json").write_text('{"format":"mlx_lora_adapter"}\n', encoding="utf-8")
        return [
            MlxTrainerEvent(kind="log", message="mlx-lm lora train started"),
            MlxTrainerEvent(kind="metric", step=9, total_steps=18, loss=0.31, vram_gb=0.0, tokens_per_sec=82.4),
        ]


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "mlx_wrapper.db"
    command.upgrade(alembic_config(db_path), "head")
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return f"sqlite:///{db_path}"


def create_queued_mlx_run(database_url: str, mib_home: Path) -> tuple[str, str, str]:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            now = "2026-01-01T00:00:00.000Z"
            project = Project(id="project_1", name="MLX Project", preset_id="router.basic.v1", created_at=now, updated_at=now)
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
                "backend": "mlx",
                "method": "mlx_lora",
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
                    backend="mlx",
                    method="mlx_lora",
                    seed=123,
                    config=config,
                    job_params={
                        "preset_id": "router.basic.v1",
                        "dataset_id": dataset.id,
                        "base_model": "google/gemma-2b-it",
                        "backend": "mlx",
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


def test_mlx_wrapper_writes_config_chat_dataset_events_and_adapter_manifest(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_mlx_run(database_url, mib_home)
    runner = FakeMlxRunner()

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert run_train_mlx_job(session, mib_home, job_id, runner=runner) == model_run_id
            session.commit()

        run_dir = mib_home / "projects" / "project_1" / "runs" / model_run_id
        backend_config = json.loads((run_dir / "backend_config.json").read_text(encoding="utf-8"))
        assert normalized_config(backend_config) == json.loads(Path("examples/fixtures/mlx_config.golden.json").read_text(encoding="utf-8"))
        train_config = json.loads((run_dir / "train_config.json").read_text(encoding="utf-8"))
        assert train_config["backend"] == "mlx"
        assert train_config["method"] == "mlx_lora"
        train_rows = [json.loads(line) for line in (run_dir / "dataset" / "mlx" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
        valid_rows = [json.loads(line) for line in (run_dir / "dataset" / "mlx" / "valid.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(train_rows) == 18
        assert len(valid_rows) == 2
        assert train_rows[0]["messages"][0]["role"] == "user"
        assert "Classify the request" in train_rows[0]["messages"][0]["content"]
        assert train_rows[0]["messages"][1]["role"] == "assistant"

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
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["adapter_format"] == "mlx_lora_adapter"
            assert {item["path"] for item in manifest["files"]} == {"adapter/adapter_config.json", "adapter/adapters.npz"}
            assert model_run.artifact_manifest_sha256 == sha256_text((run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert job.status == "SUCCEEDED"
            assert resource.resource_type == "model_run"
            events = session.query(JobEvent).filter_by(job_id=job_id).order_by(JobEvent.seq.asc()).all()
            payloads = [json.loads(event.payload_json) for event in events]
            assert any(event.event_type == "log" and payload["message"] == "mlx-lm lora train started" for event, payload in zip(events, payloads, strict=True))
            metric = next(payload for event, payload in zip(events, payloads, strict=True) if event.event_type == "metric")
            assert metric["loss"] == 0.31
            assert metric["tokens_per_sec"] == 82.4
            assert any(event.event_type == "artifact" for event in events)
    finally:
        engine.dispose()


def test_mlx_wrapper_failure_marks_job_and_model_run_failed(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_mlx_run(database_url, mib_home)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(TrainMlxError):
                run_train_mlx_job(session, mib_home, job_id, runner=FakeMlxRunner(fail=True))
            session.commit()

        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            job = session.get(Job, job_id)
            assert model_run is not None
            assert job is not None
            assert model_run.status == "FAILED"
            assert job.status == "FAILED"
            assert job.error_class == "UNKNOWN"
            assert "mlx metal failure" in str(job.error_message)
            assert "\n" not in str(job.error_message)
    finally:
        engine.dispose()


def normalized_config(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    normalized["model"] = "<model_cache_path>"
    normalized["data"] = "<dataset_dir>"
    normalized["adapter_path"] = "<adapter_dir>"
    return normalized
