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
from services.shared.db.models import EvalSet
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


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "eval_sets.db"
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


def project_payload(name: str = "Eval Project") -> dict[str, Any]:
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


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


async def create_project_dataset_and_approve(client: httpx.AsyncClient) -> tuple[str, str, list[str]]:
    project = await call_api(client.post("/projects", json=project_payload(), headers=auth_headers()))
    assert project.status_code == 201
    project_id = project.json()["id"]

    created = await call_api(
        client.post(
            f"/projects/{project_id}/datasets",
            json={"examples": load_router_examples(), "status": "BUILT"},
            headers=auth_headers(),
        )
    )
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    read = await call_api(client.get(f"/datasets/{dataset_id}", headers=auth_headers()))
    assert read.status_code == 200
    example_ids = [example["id"] for example in read.json()["examples"]]

    approved = await call_api(
        client.patch(
            f"/datasets/{dataset_id}",
            json={"status": "APPROVED", "approved_example_ids": example_ids},
            headers=auth_headers(),
        )
    )
    assert approved.status_code == 200
    return project_id, dataset_id, example_ids


def test_teacher_guard_eval_set_freezes_approved_pre_teacher_examples(tmp_path: Path) -> None:
    asyncio.run(run_teacher_guard_eval_set_freezes_approved_pre_teacher_examples(tmp_path))


async def run_teacher_guard_eval_set_freezes_approved_pre_teacher_examples(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, example_ids = await create_project_dataset_and_approve(client)
        created = await call_api(
            client.post(
                f"/projects/{project_id}/eval-sets",
                json={
                    "purpose": "teacher_guard",
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "labeler_ids": ["domain_reviewer"],
                },
                headers=auth_headers(),
            )
        )
        listed = await call_api(client.get(f"/projects/{project_id}/eval-sets?purpose=teacher_guard", headers=auth_headers()))

    assert created.status_code == 201
    eval_set = created.json()
    assert eval_set["purpose"] == "teacher_guard"
    assert eval_set["dataset_id"] == dataset_id
    assert eval_set["version"] == 1
    assert eval_set["sample_count"] == 20
    assert eval_set["kappa"] is None
    assert eval_set["labeler_ids_json"] == ["domain_reviewer"]
    assert eval_set["frozen_at"] is not None

    eval_path = Path(eval_set["path"])
    assert eval_path == mib_home / "projects" / project_id / "eval_sets" / "1" / "eval_set.jsonl"
    assert eval_path.exists()
    text = eval_path.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == eval_set["sha256"]
    rows = [json.loads(line) for line in text.splitlines()]
    assert len(rows) == 20
    assert set(rows[0]) == {"example_id", "input_sha256", "source", "input", "output"}
    assert rows[0]["source"] == "user"

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [eval_set["id"]]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            persisted = session.get(EvalSet, eval_set["id"])
            assert persisted is not None
            assert persisted.is_holdout == 1
            assert persisted.sha256 == eval_set["sha256"]
            assert persisted.route_snapshot_sha256 == eval_set["route_snapshot_sha256"]
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_eval_set_requires_approved_examples(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project = await call_api(client.post("/projects", json=project_payload("Unapproved Eval"), headers=auth_headers()))
        assert project.status_code == 201
        project_id = project.json()["id"]
        created = await call_api(
            client.post(
                f"/projects/{project_id}/datasets",
                json={"examples": load_router_examples(), "status": "BUILT"},
                headers=auth_headers(),
            )
        )
        assert created.status_code == 201
        dataset_id = created.json()["id"]
        read = await call_api(client.get(f"/datasets/{dataset_id}", headers=auth_headers()))
        example_ids = [example["id"] for example in read.json()["examples"]]
        response = await call_api(
            client.post(
                f"/projects/{project_id}/eval-sets",
                json={
                    "purpose": "teacher_guard",
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "labeler_ids": ["domain_reviewer"],
                },
                headers=auth_headers(),
            )
        )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EVAL_SET_EXAMPLES_NOT_APPROVED"


@pytest.mark.asyncio
async def test_benchmark_eval_set_requires_benchmark_quality_gate(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, example_ids = await create_project_dataset_and_approve(client)
        response = await call_api(
            client.post(
                f"/projects/{project_id}/eval-sets",
                json={
                    "purpose": "benchmark_gold",
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "labeler_ids": ["a", "b", "c"],
                    "kappa": 0.8,
                },
                headers=auth_headers(),
            )
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
