from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.shared.db.models import AuditEvent, JobEvent
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.dataset.teacher_synthetic_helpers import (
    FakeTeacherClient,
    client_for,
    prepare_database,
    create_approved_teacher_synthetic_job,
    run_worker,
)


@pytest.mark.asyncio
async def test_dataset_gen_event_payload_redacts_raw_generated_examples(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "hard_negative_redaction.db")
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200, hard_negative_min_count=40)
        run_worker(database_url, mib_home, setup.job_id, FakeTeacherClient(count=200, hard_negative_count=40))

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            event_payloads = [event.payload_json for event in session.query(JobEvent).filter_by(job_id=setup.job_id)]
            audit = session.query(AuditEvent).filter_by(event_type="teacher_egress", resource_id=setup.job_id).one()
    finally:
        engine.dispose()

    combined = "\n".join(event_payloads + [audit.details_json])
    assert "synthetic teacher case" not in combined
    assert "synthetic hard negative case" not in combined
    assert "pre teacher source case" not in combined
    assert "anonymized_examples" not in combined

    for payload_text in event_payloads:
        payload = json.loads(payload_text)
        forbidden_keys = {"input", "output", "examples", "raw_examples", "prompt", "packet"}
        assert forbidden_keys.isdisjoint(payload)

    audit_details = json.loads(audit.details_json)
    assert audit_details == {
        "approval_id": setup.approval_id,
        "approved_by_user": True,
        "dataset_id": setup.source_dataset_id,
        "packet_sha256": setup.packet_sha256,
        "project_id": setup.project_id,
        "target_count": 200,
    }
