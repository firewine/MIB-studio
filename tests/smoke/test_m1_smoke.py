from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import Dataset, Example, HardwareProfile, Job, Project
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "m1_smoke.db"
    command.upgrade(alembic_config(db_path), "head")
    database_url = f"sqlite:///{db_path}"
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return database_url


def client_for(database_url: str) -> httpx.AsyncClient:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token", database_url=database_url)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


def headers(idempotency_key: str | None = None) -> dict[str, str]:
    values = {"host": "127.0.0.1:8910", "authorization": "Bearer test-token"}
    if idempotency_key:
        values["Idempotency-Key"] = idempotency_key
    return values


@pytest.mark.asyncio
async def test_m1_smoke_core_api_persistence_and_hardware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_hardware_probe(monkeypatch)
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        health = await request(client.get("/healthz", headers=headers()))
        presets = await request(client.get("/presets", headers=headers()))
        project = await request(client.post("/projects", json=project_body(), headers=headers()))
        listed_projects = await request(client.get("/projects", headers=headers()))
        updated_project = await request(
            client.patch(
                f"/projects/{project.json()['id']}",
                json={"name": "m1-smoke-router-updated"},
                headers=headers(),
            )
        )
        dataset = await request(
            client.post(
                f"/projects/{project.json()['id']}/datasets",
                json={"status": "BUILT", "examples": examples()},
                headers=headers(),
            )
        )
        dataset_with_examples = await request(client.get(f"/datasets/{dataset.json()['id']}", headers=headers()))
        hardware_job = await request(
            client.post(
                "/hardware-doctor/scan",
                json={"dry_run": True, "target_backend": "auto"},
                headers=headers("m1-smoke-hardware"),
            )
        )
        hardware = await request(client.get("/hardware-doctor/result", headers=headers()))
        archived = await request(client.delete(f"/projects/{project.json()['id']}", headers=headers()))
        archived_projects = await request(client.get("/projects?include_archived=true", headers=headers()))
        archived_guard = await client.patch(
            f"/projects/{project.json()['id']}",
            json={"name": "blocked-after-archive"},
            headers=headers(),
        )

    assert health.json()["status"] == "ok"
    assert presets.json()["items"][0]["id"] == "router.basic.v1"
    assert listed_projects.json()["items"][0]["id"] == project.json()["id"]
    assert updated_project.json()["name"] == "m1-smoke-router-updated"
    assert dataset.json()["sample_count"] == 20
    assert len(dataset_with_examples.json()["examples"]) == 20
    assert hardware_job.json()["type"] == "hardware_scan"
    assert hardware_job.json()["created_resource_type"] == "hardware_scan"
    assert hardware.json()["capability_gate"] == "G2"
    assert archived.status_code == 204
    assert archived_projects.json()["items"][0]["archived_at"] is not None
    assert archived_guard.status_code == 409
    assert archived_guard.json()["error_code"] == "PROJECT_ARCHIVED"

    assert json.loads(Path("schemas/openapi.json").read_text(encoding="utf-8"))["openapi"].startswith("3.")
    assert "submitHardwareScan" in Path("apps/desktop/src/lib/generated.ts").read_text(encoding="utf-8")
    assert "Route contract" in Path("apps/desktop/src/main.mjs").read_text(encoding="utf-8")

    assert_persisted_counts(database_url)

    async with client_for(database_url) as restarted:
        restored_dataset = await request(restarted.get(f"/datasets/{dataset.json()['id']}", headers=headers()))
        restored_hardware = await request(restarted.get("/hardware-doctor/result", headers=headers()))

    assert restored_dataset.json()["sample_count"] == 20
    assert restored_hardware.json()["capability_gate"] == "G2"


async def request(awaitable: object) -> httpx.Response:
    response = await asyncio.wait_for(awaitable, timeout=10)
    assert response.status_code < 400, response.text
    return response


def set_hardware_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIB_HW_MACHINE_ID", "m1-smoke-machine")
    monkeypatch.setenv("MIB_HW_OS", "Linux smoke")
    monkeypatch.setenv("MIB_HW_CPU", "Smoke CPU")
    monkeypatch.setenv("MIB_HW_RAM_GB", "64")
    monkeypatch.setenv("MIB_HW_GPU_VENDOR", "nvidia")
    monkeypatch.setenv("MIB_HW_GPU_NAME", "RTX Smoke 24GB")
    monkeypatch.setenv("MIB_HW_VRAM_GB", "24")
    monkeypatch.setenv("MIB_HW_CUDA_STATUS", "ok")


def project_body() -> dict[str, object]:
    return {
        "name": "m1-smoke-router",
        "preset_id": "router.basic.v1",
        "routes": [
            {"route_id": "support", "description": "Support route", "is_unsafe": False},
            {"route_id": "billing", "description": "Billing route", "is_unsafe": False},
            {"route_id": "unsafe_request", "description": "Unsafe route", "is_unsafe": True},
        ],
    }


def examples() -> list[dict[str, object]]:
    route_ids = ["support", "billing", "unsafe_request"]
    return [
        {
            "source": "user",
            "input": {"text": f"m1 smoke example {index}", "allowed_routes": route_ids},
            "output": {
                "route": route_ids[index % len(route_ids)],
                "task_type": "block" if index % len(route_ids) == 2 else "generate_report",
                "requires_calculation": False,
                "requires_human_review": index % len(route_ids) == 2,
                "confidence": 0.84,
            },
        }
        for index in range(20)
    ]


def assert_persisted_counts(database_url: str) -> None:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert session.query(Project).count() == 1
            assert session.query(Dataset).count() == 1
            assert session.query(Example).count() == 20
            assert session.query(Job).filter_by(type="hardware_scan").count() == 1
            assert session.query(HardwareProfile).count() == 1
    finally:
        engine.dispose()
