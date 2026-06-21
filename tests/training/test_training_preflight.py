from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import Example, HardwareProfile, Job, JobResource, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


ROUTES = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path, name: str = "training_preflight.db") -> str:
    db_path = tmp_path / name
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
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


def auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"host": "127.0.0.1:8910", "authorization": "Bearer test-token"}
    if extra:
        headers.update(extra)
    return headers


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


def project_payload(name: str = "Training Project") -> dict[str, Any]:
    return {
        "name": name,
        "preset_id": "router.basic.v1",
        "routes": [
            {"route_id": route_id, "description": f"{route_id} route", "is_unsafe": route_id.startswith("blocked")}
            for route_id in ROUTES
        ],
    }


def load_router_examples() -> list[dict[str, Any]]:
    rows = []
    for line in Path("examples/fixtures/router_20.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        rows.append({"input": row["input"], "output": row["output"], "source": "user"})
    return rows


async def create_project_dataset(client: httpx.AsyncClient, *, approve: bool) -> tuple[str, str, list[str]]:
    project = await call_api(client.post("/projects", json=project_payload(), headers=auth_headers()))
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    created = await call_api(
        client.post(
            f"/projects/{project_id}/datasets",
            json={"status": "BUILT", "examples": load_router_examples()},
            headers=auth_headers(),
        )
    )
    assert created.status_code == 201, created.text
    dataset_id = created.json()["id"]
    read = await call_api(client.get(f"/datasets/{dataset_id}", headers=auth_headers()))
    assert read.status_code == 200, read.text
    example_ids = [example["id"] for example in read.json()["examples"]]
    if approve:
        approved = await call_api(
            client.patch(
                f"/datasets/{dataset_id}",
                json={"status": "APPROVED", "approved_example_ids": example_ids},
                headers=auth_headers(),
            )
        )
        assert approved.status_code == 200, approved.text
    return project_id, dataset_id, example_ids


def add_hardware_profile(database_url: str, *, allowed_backend: str = "cuda", enabled: bool = True) -> None:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            dry_run = {
                "training_enabled": enabled,
                "training_disabled_reason_code": "NONE" if enabled else "NO_GPU",
                "allowed_backends": [allowed_backend] if enabled else [],
                "backend_recommendation": allowed_backend if enabled else "cpu",
            }
            session.add(
                HardwareProfile(
                    id="hardware_profile_1",
                    machine_id="machine_1",
                    os="Linux test",
                    cpu="test cpu",
                    ram_gb=64.0,
                    gpu_vendor="nvidia" if allowed_backend == "cuda" else "apple",
                    gpu_name="test gpu",
                    vram_gb=24.0 if allowed_backend == "cuda" else None,
                    unified_ram_gb=64.0 if allowed_backend == "mlx" else None,
                    cuda_status="ok" if allowed_backend == "cuda" else "na",
                    mlx_status="ok" if allowed_backend == "mlx" else "na",
                    capability_gate="G2" if enabled else "G0",
                    dry_run_result_json=canonical_json(dry_run),
                    created_at="2026-01-01T00:00:00.000Z",
                )
            )
            session.commit()
    finally:
        engine.dispose()


async def submit_train(
    client: httpx.AsyncClient,
    project_id: str,
    dataset_id: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return await call_api(
        client.post(
            f"/projects/{project_id}/jobs",
            json={
                "type": "train",
                "params": {
                    "preset_id": "router.basic.v1",
                    "dataset_id": dataset_id,
                    "base_model": "google/gemma-2b-it",
                    "backend": "cuda",
                    "training_preset": "quick",
                    "seed": 123,
                },
            },
            headers=headers or auth_headers(),
        )
    )


@pytest.mark.asyncio
async def test_train_submit_creates_model_run_job_resource_and_reads_model_run(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    add_hardware_profile(database_url, allowed_backend="cuda", enabled=True)

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, _ = await create_project_dataset(client, approve=True)
        response = await submit_train(
            client,
            project_id,
            dataset_id,
            headers=auth_headers({"Idempotency-Key": "train-once"}),
        )
        replay = await submit_train(
            client,
            project_id,
            dataset_id,
            headers=auth_headers({"Idempotency-Key": "train-once"}),
        )
        model_run_id = response.json()["created_resource_id"]
        listed = await call_api(client.get(f"/projects/{project_id}/model-runs", headers=auth_headers()))
        read = await call_api(client.get(f"/model-runs/{model_run_id}", headers=auth_headers()))

    assert response.status_code == 202, response.text
    assert response.json()["status"] == "QUEUED"
    assert response.json()["type"] == "train"
    assert response.json()["created_resource_type"] == "model_run"
    assert replay.status_code == 202, replay.text
    assert replay.json()["job_id"] == response.json()["job_id"]
    assert replay.json()["idempotency_replayed"] is True
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["items"]] == [model_run_id]
    assert read.status_code == 200, read.text
    assert read.json()["job_id"] == response.json()["job_id"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            job = session.get(Job, response.json()["job_id"])
            resource = session.get(JobResource, response.json()["job_id"])
            assert model_run is not None
            assert job is not None
            assert resource is not None
            assert model_run.status == "QUEUED"
            assert model_run.method == "qlora"
            assert model_run.backend == "cuda"
            assert model_run.seed == 123
            config = json.loads(model_run.config_json)
            assert config["dataset_id"] == dataset_id
            assert config["training_preset"] == "quick"
            assert config["model_cache_subdir"] == "google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad"
            assert model_run.config_hash == sha256_text(model_run.config_json)
            params = json.loads(job.params_json)
            assert params["model_run_id"] == model_run_id
            assert job.type == "train"
            assert job.resource_class == "gpu_exclusive"
            assert resource.resource_type == "model_run"
            assert resource.resource_id == model_run_id
            assert resource.is_current == 1
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_train_submit_requires_approved_dataset(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "training_preflight_unapproved.db")
    mib_home = tmp_path / ".mib-home"
    add_hardware_profile(database_url)

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, _ = await create_project_dataset(client, approve=False)
        response = await submit_train(client, project_id, dataset_id)

    assert response.status_code == 409
    assert response.json()["error_code"] == "DATASET_NOT_APPROVED"


@pytest.mark.asyncio
async def test_train_submit_requires_enabled_hardware_backend(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "training_preflight_hardware.db")
    mib_home = tmp_path / ".mib-home"
    add_hardware_profile(database_url, allowed_backend="mlx", enabled=True)

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, _ = await create_project_dataset(client, approve=True)
        response = await submit_train(client, project_id, dataset_id)

    assert response.status_code == 409
    assert response.json()["error_code"] == "HARDWARE_BACKEND_UNAVAILABLE"


@pytest.mark.asyncio
async def test_train_submit_rejects_route_snapshot_mismatch(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "training_preflight_snapshot.db")
    mib_home = tmp_path / ".mib-home"
    add_hardware_profile(database_url)

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, example_ids = await create_project_dataset(client, approve=True)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            example = session.get(Example, example_ids[0])
            assert example is not None
            payload = json.loads(example.input_json)
            payload["allowed_routes"] = list(reversed(payload["allowed_routes"]))
            example.input_json = canonical_json(payload)
            example.input_sha256 = hashlib.sha256(example.input_json.encode("utf-8")).hexdigest()
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        response = await submit_train(client, project_id, dataset_id)

    assert response.status_code == 409
    assert response.json()["error_code"] == "DATASET_ROUTE_SNAPSHOT_MISMATCH"
