from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "restart.db"
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
async def test_m1_restart_persists_project_dataset_examples_job_and_hardware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIB_HW_MACHINE_ID", "restart-machine")
    monkeypatch.setenv("MIB_HW_OS", "Linux restart")
    monkeypatch.setenv("MIB_HW_CPU", "Restart CPU")
    monkeypatch.setenv("MIB_HW_RAM_GB", "64")
    monkeypatch.setenv("MIB_HW_GPU_VENDOR", "nvidia")
    monkeypatch.setenv("MIB_HW_GPU_NAME", "RTX Restart 24GB")
    monkeypatch.setenv("MIB_HW_VRAM_GB", "24")
    monkeypatch.setenv("MIB_HW_CUDA_STATUS", "ok")
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        project = await request(
            client.post(
                "/projects",
                json={
                    "name": "restart-router",
                    "preset_id": "router.basic.v1",
                    "routes": [
                        {"route_id": "support", "description": "Support route", "is_unsafe": False},
                        {"route_id": "unsafe_request", "description": "Unsafe route", "is_unsafe": True},
                    ],
                },
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
        hardware = await request(
            client.post(
                "/hardware-doctor/scan",
                json={"dry_run": True, "target_backend": "auto"},
                headers=headers("restart-hardware"),
            )
        )

    async with client_for(database_url) as restarted:
        restored_project = await request(restarted.get(f"/projects/{project.json()['id']}", headers=headers()))
        restored_dataset = await request(restarted.get(f"/datasets/{dataset.json()['id']}", headers=headers()))
        restored_hardware = await request(restarted.get("/hardware-doctor/result", headers=headers()))

    assert project.status_code == 201
    assert dataset.status_code == 201
    assert hardware.status_code == 202
    assert restored_project.json()["name"] == "restart-router"
    assert restored_dataset.json()["sample_count"] == 20
    assert len(restored_dataset.json()["examples"]) == 20
    assert restored_hardware.json()["capability_gate"] == "G2"


async def request(awaitable: object) -> httpx.Response:
    response = await asyncio.wait_for(awaitable, timeout=10)
    assert response.status_code < 400, response.text
    return response


def examples() -> list[dict[str, object]]:
    return [
        {
            "source": "user",
            "input": {"text": f"restart example {index}", "allowed_routes": ["support", "unsafe_request"]},
            "output": {
                "route": "support" if index % 2 == 0 else "unsafe_request",
                "task_type": "generate_report" if index % 2 == 0 else "block",
                "requires_calculation": False,
                "requires_human_review": index % 2 == 1,
                "confidence": 0.8,
            },
        }
        for index in range(20)
    ]
