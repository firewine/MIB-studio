from __future__ import annotations

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
    db_path = tmp_path / "presets.db"
    command.upgrade(alembic_config(db_path), "head")
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    with factory() as session:
        seed_router_preset(session)
        session.commit()
    engine.dispose()
    return f"sqlite:///{db_path}"


def auth_headers(token: str = "test-token") -> dict[str, str]:
    return {"host": "127.0.0.1:8910", "authorization": f"Bearer {token}"}


def client_for(database_url: str) -> httpx.AsyncClient:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token", database_url=database_url)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


@pytest.mark.asyncio
async def test_list_presets_returns_seeded_router_preset(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        response = await client.get("/presets", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1

    preset = body["items"][0]
    assert preset["id"] == "router.basic.v1"
    assert preset["name"] == "Basic Router"
    assert preset["preset_type"] == "router"
    assert preset["version"] == 1
    assert preset["schema_refs"] == {
        "input": "schemas/router_input.schema.json",
        "output": "schemas/router_output.schema.json",
    }
    assert preset["config_json"]["base_model_options"] == [
        "google/gemma-2b-it",
        "microsoft/Phi-3.5-mini-instruct",
    ]
    assert preset["config_json"]["data_template"]["dataset"]["format"] == "jsonl"
    assert preset["config_json"]["training_defaults"]["quick"]["epochs"] == 1
    assert preset["config_json"]["eval_options"]["metrics"] == [
        "route_accuracy",
        "task_type_accuracy",
        "unsafe_recall",
        "json_valid_rate",
        "latency_p50",
        "cost_per_task",
    ]
    assert preset["config_json"]["export_options"] == ["zip", "docker"]
    assert preset["created_at"]


@pytest.mark.asyncio
async def test_get_preset_matches_list_item(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        listed = await client.get("/presets", headers=auth_headers())
        read = await client.get("/presets/router.basic.v1", headers=auth_headers())

    assert read.status_code == 200
    assert read.json() == listed.json()["items"][0]


@pytest.mark.asyncio
async def test_get_preset_404_for_missing_id(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        response = await client.get("/presets/missing", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["error_code"] == "PRESET_NOT_FOUND"
    assert response.json()["details"] == {"preset_id": "missing"}
