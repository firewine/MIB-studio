from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from alembic import command
from alembic.config import Config

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.seed import seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.dataset_gen import DatasetGenResult, run_dataset_gen_job


ROUTES = [
    "finance_income",
    "risk_summary",
    "investment_advice_block",
    "human_review",
    "blocked_pii",
    "blocked_unsupported",
]


@dataclass(frozen=True)
class TeacherSyntheticSetup:
    project_id: str
    source_dataset_id: str
    source_example_ids: list[str]
    source_inputs: list[dict[str, Any]]
    eval_set_id: str
    approval_id: str
    packet_sha256: str
    job_id: str


class FakeTeacherClient:
    def __init__(self, *, count: int = 200, overlap_input: dict[str, Any] | None = None) -> None:
        self.count = count
        self.overlap_input = overlap_input

    def generate_examples(self, packet: dict[str, Any], *, target_count: int) -> list[dict[str, Any]]:
        route_ids = [route["route_id"] for route in packet["rules"]]
        count = max(self.count, target_count)
        examples = []
        for index in range(count):
            route_id = route_ids[index % len(route_ids)]
            input_payload = {
                "text": f"synthetic teacher case {index} for {route_id}",
                "allowed_routes": route_ids,
                "metadata": {"synthetic_index": index, "teacher_packet_sha": packet.get("packet_sha256")},
            }
            if index == 0 and self.overlap_input is not None:
                input_payload = self.overlap_input
            examples.append(
                {
                    "input": input_payload,
                    "output": {
                        "route": route_id,
                        "task_type": "block" if route_id.startswith("blocked") else "generate_report",
                        "requires_calculation": route_id == "finance_income",
                        "requires_human_review": route_id.startswith("blocked") or route_id == "human_review",
                        "confidence": 0.91,
                    },
                }
            )
        return examples


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path, name: str = "teacher_synthetic.db") -> str:
    db_path = tmp_path / name
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


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


def project_payload(name: str = "Teacher Synthetic Project") -> dict[str, Any]:
    return {
        "name": name,
        "preset_id": "router.basic.v1",
        "routes": [
            {"route_id": route_id, "description": f"{route_id} route", "is_unsafe": route_id.startswith("blocked")}
            for route_id in ROUTES
        ],
    }


def source_examples() -> list[dict[str, Any]]:
    rows = []
    for index in range(20):
        route_id = ROUTES[index % len(ROUTES)]
        rows.append(
            {
                "source": "user",
                "input": {
                    "text": f"pre teacher source case {index} for {route_id}",
                    "allowed_routes": ROUTES,
                    "metadata": {"fixture_index": index},
                },
                "output": {
                    "route": route_id,
                    "task_type": "block" if route_id.startswith("blocked") else "generate_report",
                    "requires_calculation": route_id == "finance_income",
                    "requires_human_review": route_id.startswith("blocked") or route_id == "human_review",
                    "confidence": 0.86,
                },
            }
        )
    return rows


async def create_approved_teacher_synthetic_job(
    client: httpx.AsyncClient,
    *,
    target_count: int = 200,
) -> TeacherSyntheticSetup:
    project = await call_api(client.post("/projects", json=project_payload(), headers=auth_headers()))
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    created = await call_api(
        client.post(
            f"/projects/{project_id}/datasets",
            json={"status": "BUILT", "examples": source_examples()},
            headers=auth_headers(),
        )
    )
    assert created.status_code == 201, created.text
    source_dataset_id = created.json()["id"]

    read_source = await call_api(client.get(f"/datasets/{source_dataset_id}", headers=auth_headers()))
    assert read_source.status_code == 200, read_source.text
    source_body = read_source.json()
    source_example_ids = [example["id"] for example in source_body["examples"]]
    source_inputs = [example["input"] for example in source_body["examples"]]

    approved = await call_api(
        client.patch(
            f"/datasets/{source_dataset_id}",
            json={"status": "APPROVED", "approved_example_ids": source_example_ids},
            headers=auth_headers(),
        )
    )
    assert approved.status_code == 200, approved.text

    eval_set = await call_api(
        client.post(
            f"/projects/{project_id}/eval-sets",
            json={
                "purpose": "teacher_guard",
                "dataset_id": source_dataset_id,
                "example_ids": source_example_ids,
                "labeler_ids": ["domain_reviewer"],
            },
            headers=auth_headers(),
        )
    )
    assert eval_set.status_code == 201, eval_set.text

    preview = await call_api(
        client.post(
            f"/projects/{project_id}/teacher-packets/preview",
            json={
                "dataset_id": source_dataset_id,
                "example_ids": source_example_ids,
                "instruction": "Generate schema-valid router examples without personal data.",
            },
            headers=auth_headers(),
        )
    )
    assert preview.status_code == 200, preview.text
    approval = await call_api(client.post(f"/teacher-packets/{preview.json()['id']}/approve", headers=auth_headers()))
    assert approval.status_code == 200, approval.text

    job = await call_api(
        client.post(
            f"/projects/{project_id}/jobs",
            json={
                "type": "dataset_gen",
                "params": {
                    "generation_mode": "teacher_synthetic",
                    "teacher_packet_approval_id": approval.json()["approval_id"],
                    "target_count": target_count,
                },
            },
            headers=auth_headers(),
        )
    )
    assert job.status_code == 202, job.text

    return TeacherSyntheticSetup(
        project_id=project_id,
        source_dataset_id=source_dataset_id,
        source_example_ids=source_example_ids,
        source_inputs=source_inputs,
        eval_set_id=eval_set.json()["id"],
        approval_id=approval.json()["approval_id"],
        packet_sha256=approval.json()["packet_sha256"],
        job_id=job.json()["job_id"],
    )


def run_worker(database_url: str, mib_home: Path, job_id: str, teacher_client: FakeTeacherClient) -> DatasetGenResult:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            result = run_dataset_gen_job(session, mib_home, job_id, teacher_client=teacher_client)
            session.commit()
            return result
    finally:
        engine.dispose()


def jsonl_rows(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
