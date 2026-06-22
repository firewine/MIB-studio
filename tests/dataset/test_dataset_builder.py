from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import Dataset
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
    db_path = tmp_path / "datasets.db"
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


def load_router_examples() -> list[dict[str, Any]]:
    rows = []
    for line in Path("examples/fixtures/router_20.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        rows.append({"input": row["input"], "output": row["output"], "source": "user"})
    return rows


def project_payload() -> dict[str, Any]:
    return {
        "name": "Dataset Project",
        "preset_id": "router.basic.v1",
        "routes": [
            {
                "route_id": route_id,
                "description": f"{route_id} route",
                "is_unsafe": route_id.startswith("blocked") or route_id == "investment_advice_block",
                "task_type": "block" if route_id.startswith("blocked") or route_id == "investment_advice_block" else "generate_report",
                "requires_calculation": route_id == "finance_income",
                "requires_human_review": route_id.startswith("blocked") or route_id in {"human_review", "investment_advice_block"},
                "is_default": route_id == "human_review",
                "examples": [f"{route_id} example"],
            }
            for route_id in ROUTES
        ],
    }


async def create_project(client: httpx.AsyncClient) -> str:
    response = await client.post("/projects", json=project_payload(), headers=auth_headers())
    assert response.status_code == 201
    return str(response.json()["id"])


def test_build_dataset_writes_jsonl_and_example_rows(tmp_path: Path) -> None:
    asyncio.run(run_build_dataset_writes_jsonl_and_example_rows(tmp_path))


async def run_build_dataset_writes_jsonl_and_example_rows(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id = await create_project(client)
        response = await asyncio.wait_for(
            client.post(
                f"/projects/{project_id}/datasets",
                json={"examples": load_router_examples(), "status": "BUILT"},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        assert response.status_code == 201
        dataset = response.json()

        listed = await asyncio.wait_for(client.get(f"/projects/{project_id}/datasets", headers=auth_headers()), timeout=10)
        read = await asyncio.wait_for(client.get(f"/datasets/{dataset['id']}?limit=5", headers=auth_headers()), timeout=10)

    dataset_path = Path(dataset["path"])
    assert dataset["project_id"] == project_id
    assert dataset["version"] == 1
    assert dataset["status"] == "BUILT"
    assert dataset["sample_count"] == 20
    assert dataset["schema_version"] == "router.v1"
    assert dataset_path == mib_home / "projects" / project_id / "datasets" / "1" / "dataset.jsonl"
    assert dataset_path.exists()

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    with factory() as session:
        route_snapshot = json.loads(session.get(Dataset, dataset["id"]).route_snapshot_json)
    engine.dispose()
    assert route_snapshot[0]["task_type"] == "generate_report"
    assert route_snapshot[0]["requires_calculation"] is True
    assert route_snapshot[0]["examples"] == ["finance_income example"]
    assert route_snapshot[3]["is_default"] is True

    text = dataset_path.read_text(encoding="utf-8")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == dataset["sha256"]
    rows = [json.loads(line) for line in text.splitlines()]
    assert len(rows) == 20
    assert set(rows[0]) == {"instruction", "input", "output"}
    assert rows[0]["instruction"] == "Classify the request into one of the allowed routes."
    assert rows[0]["input"]["allowed_routes"] == ROUTES
    assert set(rows[0]["output"]) == {
        "route",
        "task_type",
        "requires_calculation",
        "requires_human_review",
        "confidence",
    }
    assert rows[0]["output"]["route"] in ROUTES

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [dataset["id"]]

    assert read.status_code == 200
    body = read.json()
    assert body["id"] == dataset["id"]
    assert len(body["examples"]) == 5
    assert body["next_cursor"] == "4"
    assert body["examples"][0]["approved"] is False
    assert body["examples"][0]["validation_errors"] == []


def test_build_dataset_rejects_schema_invalid_or_route_mismatch(tmp_path: Path) -> None:
    asyncio.run(run_build_dataset_rejects_schema_invalid_or_route_mismatch(tmp_path))


async def run_build_dataset_rejects_schema_invalid_or_route_mismatch(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    examples = load_router_examples()
    examples[0]["output"] = {**examples[0]["output"], "route": "not_in_project"}

    async with client_for(database_url, mib_home) as client:
        project_id = await create_project(client)
        response = await asyncio.wait_for(
            client.post(
                f"/projects/{project_id}/datasets",
                json={"examples": examples},
                headers=auth_headers(),
            ),
            timeout=10,
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "DATASET_ROW_INVALID"
    assert body["details"]["row_errors"][0]["row_index"] == 0
    assert {error["code"] for error in body["details"]["row_errors"][0]["errors"]} == {"ROUTE_NOT_ALLOWED"}


def test_approve_dataset_requires_and_freezes_twenty_examples(tmp_path: Path) -> None:
    asyncio.run(run_approve_dataset_requires_and_freezes_twenty_examples(tmp_path))


async def run_approve_dataset_requires_and_freezes_twenty_examples(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id = await create_project(client)
        created = await asyncio.wait_for(
            client.post(
                f"/projects/{project_id}/datasets",
                json={"examples": load_router_examples()},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        dataset_id = created.json()["id"]
        read = await asyncio.wait_for(client.get(f"/datasets/{dataset_id}", headers=auth_headers()), timeout=10)
        example_ids = [example["id"] for example in read.json()["examples"]]

        too_few = await asyncio.wait_for(
            client.patch(
                f"/datasets/{dataset_id}",
                json={"status": "APPROVED", "approved_example_ids": example_ids[:19]},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        approved = await asyncio.wait_for(
            client.patch(
                f"/datasets/{dataset_id}",
                json={"status": "APPROVED", "approved_example_ids": example_ids},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        frozen_edit = await asyncio.wait_for(
            client.patch(
                f"/examples/{example_ids[0]}",
                json={"review_status": "REJECTED"},
                headers=auth_headers(),
            ),
            timeout=10,
        )

    assert too_few.status_code == 409
    assert too_few.json()["error_code"] == "DATASET_APPROVAL_MIN_EXAMPLES"
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["frozen_at"] is not None
    assert frozen_edit.status_code == 409
    assert frozen_edit.json()["error_code"] == "DATASET_FROZEN"


def test_patch_example_validates_edit_and_review_status(tmp_path: Path) -> None:
    asyncio.run(run_patch_example_validates_edit_and_review_status(tmp_path))


async def run_patch_example_validates_edit_and_review_status(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id = await create_project(client)
        created = await asyncio.wait_for(
            client.post(
                f"/projects/{project_id}/datasets",
                json={"examples": load_router_examples()},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        dataset_id = created.json()["id"]
        read = await asyncio.wait_for(client.get(f"/datasets/{dataset_id}", headers=auth_headers()), timeout=10)
        example = read.json()["examples"][0]

        edited = await asyncio.wait_for(
            client.patch(
                f"/examples/{example['id']}",
                json={"output": {**example["output"], "route": "human_review"}},
                headers=auth_headers(),
            ),
            timeout=10,
        )
        rejected = await asyncio.wait_for(
            client.patch(
                f"/examples/{example['id']}",
                json={"review_status": "REJECTED"},
                headers=auth_headers(),
            ),
            timeout=10,
        )

    assert edited.status_code == 200
    assert edited.json()["output"]["route"] == "human_review"
    assert edited.json()["review_status"] == "EDITED"
    assert edited.json()["approved"] is False
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "REJECTED"
    assert rejected.json()["approved"] is False
