from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import Dataset
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


NOW = "2026-06-21T00:00:00.000Z"
HASH = "b" * 64


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "projects.db"
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


def project_payload(name: str = "Router Project") -> dict[str, object]:
    return {
        "name": name,
        "preset_id": "router.basic.v1",
        "routes": [
            {
                "route_id": "finance_income",
                "description": "Finance income route",
                "is_unsafe": False,
                "task_type": "generate_report",
                "requires_calculation": True,
                "requires_human_review": False,
                "is_default": False,
                "examples": ["calculate monthly finance income"],
            },
            {
                "route_id": "human_review",
                "description": "Needs human review",
                "is_unsafe": True,
                "task_type": "block",
                "requires_calculation": False,
                "requires_human_review": True,
                "is_default": True,
                "examples": ["manual escalation required"],
            },
        ],
    }


def client_for(database_url: str) -> httpx.AsyncClient:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token", database_url=database_url)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


@pytest.mark.asyncio
async def test_create_list_read_project(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    async with client_for(database_url) as client:
        created = await client.post("/projects", json=project_payload(), headers=auth_headers())
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == "Router Project"
        assert body["preset_id"] == "router.basic.v1"
        assert [route["route_id"] for route in body["routes"]] == ["finance_income", "human_review"]
        assert body["routes"][0]["task_type"] == "generate_report"
        assert body["routes"][0]["requires_calculation"] is True
        assert body["routes"][0]["examples"] == ["calculate monthly finance income"]
        assert body["routes"][1]["requires_human_review"] is True
        assert body["routes"][1]["is_default"] is True

        listed = await client.get("/projects", headers=auth_headers())
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [body["id"]]

        read = await client.get(f"/projects/{body['id']}", headers=auth_headers())
        assert read.status_code == 200
        assert read.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_create_project_requires_existing_preset(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    payload = project_payload()
    payload["preset_id"] = "missing"

    async with client_for(database_url) as client:
        response = await client.post("/projects", json=payload, headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["error_code"] == "PRESET_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_project_validates_route_count_and_duplicates(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    too_few = project_payload()
    too_few["routes"] = [{"route_id": "one", "description": "Only one"}]
    duplicate = project_payload()
    duplicate["routes"] = [
        {"route_id": "same", "description": "A"},
        {"route_id": "same", "description": "B"},
    ]

    async with client_for(database_url) as client:
        too_few_response = await client.post("/projects", json=too_few, headers=auth_headers())
        duplicate_response = await client.post("/projects", json=duplicate, headers=auth_headers())

    assert too_few_response.status_code == 422
    assert duplicate_response.status_code == 422


@pytest.mark.asyncio
async def test_patch_and_archive_project_guards_mutations(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    async with client_for(database_url) as client:
        created = await client.post("/projects", json=project_payload(), headers=auth_headers())
        project_id = created.json()["id"]

        patched = await client.patch(
            f"/projects/{project_id}",
            json={
                "name": "Renamed",
                "routes": [
                    {
                        "route_id": "risk_summary",
                        "description": "Risk route",
                        "task_type": "generate_report",
                        "requires_calculation": True,
                        "examples": ["summarize operating risk"],
                    },
                    {
                        "route_id": "blocked",
                        "description": "Blocked route",
                        "is_unsafe": True,
                        "task_type": "block",
                        "requires_human_review": True,
                        "is_default": True,
                        "examples": ["blocked route example"],
                    },
                ],
            },
            headers=auth_headers(),
        )
        assert patched.status_code == 200
        assert patched.json()["name"] == "Renamed"
        assert [route["route_id"] for route in patched.json()["routes"]] == ["risk_summary", "blocked"]
        assert patched.json()["routes"][0]["requires_calculation"] is True
        assert patched.json()["routes"][1]["examples"] == ["blocked route example"]

        archived = await client.delete(f"/projects/{project_id}", headers=auth_headers())
        assert archived.status_code == 204

        list_default = await client.get("/projects", headers=auth_headers())
        assert list_default.json()["items"] == []

        list_archived = await client.get("/projects?include_archived=true", headers=auth_headers())
        assert [item["id"] for item in list_archived.json()["items"]] == [project_id]
        assert list_archived.json()["items"][0]["archived_at"] is not None

        rejected = await client.patch(f"/projects/{project_id}", json={"name": "Nope"}, headers=auth_headers())
        assert rejected.status_code == 409
        assert rejected.json()["error_code"] == "PROJECT_ARCHIVED"


@pytest.mark.asyncio
async def test_route_taxonomy_locked_after_dataset_exists(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    async with client_for(database_url) as client:
        created = await client.post("/projects", json=project_payload(), headers=auth_headers())
        project_id = created.json()["id"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    with factory() as session:
        session.add(
            Dataset(
                id="dataset_1",
                project_id=project_id,
                version=1,
                path="dataset.jsonl",
                sha256=HASH,
                sample_count=0,
                status="DRAFT",
                schema_version="router.v1",
                route_snapshot_json="[]",
                route_snapshot_sha256=HASH,
                created_at=NOW,
            )
        )
        session.commit()
    engine.dispose()

    async with client_for(database_url) as client:
        response = await client.patch(
            f"/projects/{project_id}",
            json={
                "routes": [
                    {"route_id": "new_route", "description": "New"},
                    {"route_id": "blocked", "description": "Blocked", "is_unsafe": True},
                ]
            },
            headers=auth_headers(),
        )

    assert response.status_code == 409
    assert response.json()["error_code"] == "ROUTE_TAXONOMY_LOCKED"
    assert response.json()["details"]["locked_by_resource_type"] == "dataset"
