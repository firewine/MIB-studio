from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import AuditEvent, TeacherPacketApproval
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


ROUTES = ["support", "billing", "human_review", "blocked_pii"]
RAW_EMAIL = "ada@example.com"
RAW_PHONE = "010-1234-5678"


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "teacher_packet.db"
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


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


def project_payload(name: str = "Teacher Packet Project") -> dict[str, Any]:
    return {
        "name": name,
        "preset_id": "router.basic.v1",
        "routes": [
            {"route_id": route_id, "description": f"{route_id} route", "is_unsafe": route_id.startswith("blocked")}
            for route_id in ROUTES
        ],
    }


def example_payloads() -> list[dict[str, Any]]:
    rows = []
    for index in range(20):
        route_id = ROUTES[index % len(ROUTES)]
        rows.append(
            {
                "source": "user",
                "input": {
                    "text": f"case {index} from {RAW_EMAIL} phone {RAW_PHONE}",
                    "allowed_routes": ROUTES,
                    "metadata": {"source_file": f"/private/raw/customer_{index}.csv"},
                },
                "output": {
                    "route": route_id,
                    "task_type": "block" if route_id.startswith("blocked") else "generate_report",
                    "requires_calculation": False,
                    "requires_human_review": route_id.startswith("blocked") or route_id == "human_review",
                    "confidence": 0.84,
                },
            }
        )
    return rows


async def create_project_dataset(client: httpx.AsyncClient, *, approve: bool) -> tuple[str, str, list[str]]:
    project = await call_api(client.post("/projects", json=project_payload(), headers=auth_headers()))
    assert project.status_code == 201
    project_id = project.json()["id"]
    created = await call_api(
        client.post(
            f"/projects/{project_id}/datasets",
            json={"status": "BUILT", "examples": example_payloads()},
            headers=auth_headers(),
        )
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]
    read = await call_api(client.get(f"/datasets/{dataset_id}", headers=auth_headers()))
    assert read.status_code == 200
    example_ids = [example["id"] for example in read.json()["examples"]]
    if approve:
        approved = await call_api(
            client.patch(
                f"/datasets/{dataset_id}",
                json={"status": "APPROVED", "approved_example_ids": example_ids},
                headers=auth_headers(),
            )
        )
        assert approved.status_code == 200
    return project_id, dataset_id, example_ids


@pytest.mark.asyncio
async def test_teacher_packet_preview_masks_pii_and_approval_records_row(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        project_id, dataset_id, example_ids = await create_project_dataset(client, approve=True)
        preview = await call_api(
            client.post(
                f"/projects/{project_id}/teacher-packets/preview",
                json={
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "instruction": "Generate schema-valid router examples without personal data.",
                },
                headers=auth_headers(),
            )
        )
        approval = await call_api(client.post(f"/teacher-packets/{preview.json()['id']}/approve", headers=auth_headers()))

    assert preview.status_code == 200
    body = preview.json()
    assert body["approved_at"] is None
    assert body["packet_preview"]["instruction"] == "Generate schema-valid router examples without personal data."
    assert set(body["packet_preview"]) == {"rules", "schema", "anonymized_examples", "instruction"}
    assert len(body["packet_preview"]["anonymized_examples"]) == 20
    assert body["pii_summary"]["masked_count"] >= 40
    assert body["pii_summary"]["entity_counts"]["email"] >= 20
    assert body["pii_summary"]["entity_counts"]["phone"] >= 20
    assert "raw CSV" in body["pii_summary"]["not_transmitted"]
    assert RAW_EMAIL not in preview.text
    assert RAW_PHONE not in preview.text
    assert "/private/raw" not in preview.text
    assert body["packet_sha256"] == sha256_text(canonical_json(body["packet_preview"]))

    assert approval.status_code == 200
    assert approval.json()["approval_id"] == body["id"]
    assert approval.json()["approved_at"] is not None

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            row = session.get(TeacherPacketApproval, body["id"])
            assert row is not None
            assert row.approved_at == approval.json()["approved_at"]
            assert row.packet_sha256 == body["packet_sha256"]
            assert RAW_EMAIL not in row.packet_json
            assert RAW_PHONE not in row.packet_json
            assert "/private/raw" not in row.packet_json
            raw_rows = json.dumps([dict(item) for item in session.execute(text("SELECT * FROM audit_event")).mappings()], default=str)
            assert RAW_EMAIL not in raw_rows
            assert RAW_PHONE not in raw_rows
            audit = session.query(AuditEvent).filter_by(event_type="pii_mask").one()
            assert audit.resource_type == "dataset"
            details = json.loads(audit.details_json)
            assert details["approval_id"] == body["id"]
            assert details["packet_sha256"] == body["packet_sha256"]
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_teacher_packet_preview_requires_approved_dataset(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        project_id, dataset_id, example_ids = await create_project_dataset(client, approve=False)
        response = await call_api(
            client.post(
                f"/projects/{project_id}/teacher-packets/preview",
                json={"dataset_id": dataset_id, "example_ids": example_ids, "instruction": "Generate examples."},
                headers=auth_headers(),
            )
        )

    assert response.status_code == 409
    assert response.json()["error_code"] == "DATASET_NOT_APPROVED"


@pytest.mark.asyncio
async def test_teacher_packet_approval_rejects_expired_packet(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)

    async with client_for(database_url) as client:
        project_id, dataset_id, example_ids = await create_project_dataset(client, approve=True)
        preview = await call_api(
            client.post(
                f"/projects/{project_id}/teacher-packets/preview",
                json={"dataset_id": dataset_id, "example_ids": example_ids, "instruction": "Generate examples."},
                headers=auth_headers(),
            )
        )
        packet_id = preview.json()["id"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            row = session.get(TeacherPacketApproval, packet_id)
            assert row is not None
            row.expires_at = "2000-01-01T00:00:00.000Z"
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url) as client:
        response = await call_api(client.post(f"/teacher-packets/{packet_id}/approve", headers=auth_headers()))

    assert response.status_code == 409
    assert response.json()["error_code"] == "TEACHER_PACKET_APPROVAL_EXPIRED"
