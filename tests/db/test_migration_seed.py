from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.shared.db.models import Credential, Job, JobEvent, JobResource, Preset, Project, ProjectRoute
from services.shared.db.seed import load_model_catalog, seed_router_preset
from services.shared.db.session import create_sqlite_engine, session_factory


NOW = "2026-06-21T00:00:00.000Z"
HASH = "a" * 64
DOMAIN_TABLES = {
    "preset",
    "project",
    "project_route",
    "dataset",
    "example",
    "eval_set",
    "hardware_profile",
    "credential",
    "job",
    "job_event",
    "job_resource",
    "teacher_packet_approval",
    "model_run",
    "checkpoint",
    "benchmark",
    "eval_run",
    "agent_package",
    "export_artifact",
    "audit_event",
    "schema_migration",
}


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def upgrade_db(db_path: Path) -> None:
    command.upgrade(alembic_config(db_path), "head")


def downgrade_db(db_path: Path) -> None:
    command.downgrade(alembic_config(db_path), "base")


def sqlite_tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


@pytest.fixture()
def session(tmp_path: Path) -> Session:
    db_path = tmp_path / "mib.db"
    upgrade_db(db_path)
    engine = create_sqlite_engine(f"sqlite:///{db_path}")
    factory = session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def seed_project(db: Session, project_id: str = "project_1") -> Project:
    seed_router_preset(db)
    project = Project(
        id=project_id,
        name="Router Project",
        preset_id="router.basic.v1",
        created_at=NOW,
        updated_at=NOW,
    )
    db.add(project)
    db.flush()
    return project


def add_job(
    db: Session,
    job_id: str,
    *,
    project_id: str | None = "project_1",
    resource_class: str = "cpu_shared",
    status: str = "QUEUED",
    idempotency_key: str | None = None,
    job_type: str = "dataset_gen",
) -> Job:
    job = Job(
        id=job_id,
        project_id=project_id,
        type=job_type,
        resource_class=resource_class,
        status=status,
        priority=0,
        params_json="{}",
        idempotency_key=idempotency_key,
        attempt_count=0,
        trace_id=f"trace-{job_id}",
        created_at=NOW,
    )
    db.add(job)
    db.flush()
    return job


def test_migration_upgrade_downgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "mib.db"

    upgrade_db(db_path)
    assert DOMAIN_TABLES <= sqlite_tables(db_path)

    with sqlite3.connect(db_path) as connection:
        job_indexes = {row[1] for row in connection.execute("PRAGMA index_list('job')")}
        resource_indexes = {row[1] for row in connection.execute("PRAGMA index_list('job_resource')")}

    assert "ux_job_idempotency_project" in job_indexes
    assert "ux_job_idempotency_system" in job_indexes
    assert "ux_one_running_gpu_job" in job_indexes
    assert "ux_job_resource_current" in resource_indexes

    downgrade_db(db_path)
    assert not (DOMAIN_TABLES & sqlite_tables(db_path))


def test_foreign_key_check_clean(tmp_path: Path) -> None:
    db_path = tmp_path / "mib.db"
    upgrade_db(db_path)

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_seed_router_preset_and_project_smoke(session: Session) -> None:
    preset = seed_router_preset(session)
    session.commit()

    row = session.get(Preset, "router.basic.v1")
    assert row is not None
    assert row.id == preset.id
    assert row.preset_type == "router"
    assert json.loads(row.base_model_options_json) == [
        "google/gemma-2b-it",
        "microsoft/Phi-3.5-mini-instruct",
    ]

    project = Project(
        id="project_1",
        name="Router Project",
        preset_id=row.id,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(project)
    session.commit()

    assert session.get(Project, "project_1") is not None


def test_model_catalog_loads() -> None:
    catalog = load_model_catalog()

    assert isinstance(catalog["models"], list)
    assert {model["id"] for model in catalog["models"]} >= {
        "google/gemma-2b-it",
        "microsoft/Phi-3.5-mini-instruct",
    }


def test_project_route_unique_per_project(session: Session) -> None:
    seed_project(session)
    session.add_all(
        [
            ProjectRoute(id="route_1", project_id="project_1", route_id="safe", description="Safe", created_at=NOW),
            ProjectRoute(id="route_2", project_id="project_1", route_id="safe", description="Duplicate", created_at=NOW),
        ]
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_job_idempotency_partial_unique(session: Session) -> None:
    seed_project(session)
    add_job(session, "job_1", idempotency_key="same-key")

    with pytest.raises(IntegrityError):
        add_job(session, "job_2", idempotency_key="same-key")


def test_job_idempotency_system_scope_for_null_project(session: Session) -> None:
    add_job(session, "job_1", project_id=None, job_type="hardware_scan", idempotency_key="same-key")

    with pytest.raises(IntegrityError):
        add_job(session, "job_2", project_id=None, job_type="hardware_scan", idempotency_key="same-key")


def test_job_resource_current_unique(session: Session) -> None:
    seed_project(session)
    add_job(session, "job_1")
    add_job(session, "job_2")
    session.add(JobResource(job_id="job_1", resource_type="model_run", resource_id="model_1", is_current=1, created_at=NOW))
    session.flush()
    session.add(JobResource(job_id="job_2", resource_type="model_run", resource_id="model_1", is_current=1, created_at=NOW))

    with pytest.raises(IntegrityError):
        session.flush()


def test_only_one_running_gpu_job(session: Session) -> None:
    seed_project(session)
    add_job(session, "job_1", resource_class="gpu_exclusive", status="RUNNING")

    with pytest.raises(IntegrityError):
        add_job(session, "job_2", resource_class="gpu_exclusive", status="RUNNING")


def test_job_event_seq_unique_per_job(session: Session) -> None:
    seed_project(session)
    add_job(session, "job_1")
    session.add_all(
        [
            JobEvent(id="event_1", job_id="job_1", seq=1, ts=NOW, level="info", event_type="step", payload_json="{}", trace_id="trace-1"),
            JobEvent(id="event_2", job_id="job_1", seq=1, ts=NOW, level="info", event_type="step", payload_json="{}", trace_id="trace-1"),
        ]
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_no_plaintext_credential_in_db(session: Session) -> None:
    credential = Credential(
        id="credential_1",
        provider="openai",
        base_url="https://api.openai.com/v1",
        keychain_ref="keychain://mib/openai",
        created_at=NOW,
    )
    session.add(credential)
    session.commit()

    row = session.execute(text("SELECT provider, base_url, keychain_ref FROM credential")).one()
    assert row.keychain_ref == "keychain://mib/openai"
    columns = {column["name"] for column in session.execute(text("PRAGMA table_info('credential')")).mappings()}
    assert "api_key" not in columns
    assert "secret" not in columns
