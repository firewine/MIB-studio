from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.api.app.schemas.router_validation import validate_router_example
from services.shared.db.models import AuditEvent, Example, Job, JobEvent, TeacherPacketApproval
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.dataset.teacher_synthetic_helpers import (
    FakeTeacherClient,
    auth_headers,
    call_api,
    client_for,
    jsonl_rows,
    prepare_database,
    create_approved_teacher_synthetic_job,
    run_worker,
)


@pytest.mark.asyncio
async def test_teacher_synthetic_min200_schema_valid(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200)
        result = run_worker(database_url, mib_home, setup.job_id, FakeTeacherClient(count=200))
        generated = await call_api(client.get(f"/datasets/{result.dataset_id}?limit=200", headers=auth_headers()))

    assert result.generated_count == 200
    assert result.hard_negative_count == 40
    assert result.validated_count == 200
    assert result.rejected_count == 0
    assert result.packet_sha256 == setup.packet_sha256
    assert generated.status_code == 200, generated.text

    dataset = generated.json()
    assert dataset["project_id"] == setup.project_id
    assert dataset["version"] == 2
    assert dataset["status"] == "BUILT"
    assert dataset["sample_count"] == 200
    assert len(dataset["examples"]) == 200
    assert dataset["next_cursor"] is None
    assert len(jsonl_rows(dataset["path"])) == 200

    for example in dataset["examples"]:
        assert example["source"] in {"teacher", "hard_negative"}
        assert example["review_status"] == "PENDING"
        assert example["approved"] is False
        assert validate_router_example(example["input"], example["output"], example["input"]["allowed_routes"]) == []

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            job = session.get(Job, setup.job_id)
            approval = session.get(TeacherPacketApproval, setup.approval_id)
            assert job is not None
            assert approval is not None
            assert job.status == "SUCCEEDED"
            assert job.eval_set_id == setup.eval_set_id
            assert json.loads(job.params_json)["packet_sha256"] == setup.packet_sha256
            assert approval.used_job_id == setup.job_id
            assert session.query(Example).filter_by(dataset_id=result.dataset_id, source="teacher").count() == 160
            assert session.query(Example).filter_by(dataset_id=result.dataset_id, source="hard_negative").count() == 40
            audit = session.query(AuditEvent).filter_by(event_type="teacher_egress").one()
            details = json.loads(audit.details_json)
            assert details["approval_id"] == setup.approval_id
            assert details["approved_by_user"] is True
            assert "anonymized_examples" not in audit.details_json
            metric = session.query(JobEvent).filter_by(job_id=setup.job_id, event_type="metric").one()
            assert json.loads(metric.payload_json)["validated_count"] == 200
            assert json.loads(metric.payload_json)["hard_negative_count"] == 40
    finally:
        engine.dispose()
