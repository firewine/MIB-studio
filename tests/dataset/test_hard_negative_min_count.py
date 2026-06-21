from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.shared.db.models import Example, Job, JobEvent, JobResource
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.dataset_gen import DatasetGenWorkerError, run_dataset_gen_job
from tests.dataset.teacher_synthetic_helpers import (
    FakeTeacherClient,
    client_for,
    prepare_database,
    create_approved_teacher_synthetic_job,
    run_worker,
)


@pytest.mark.asyncio
async def test_hard_negative_min_count_is_persisted_and_reported(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "hard_negative_min_count.db")
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200, hard_negative_min_count=40)
        result = run_worker(database_url, mib_home, setup.job_id, FakeTeacherClient(count=200, hard_negative_count=40))

    assert result.generated_count == 200
    assert result.validated_count == 200
    assert result.hard_negative_count == 40

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert session.query(Example).filter_by(dataset_id=result.dataset_id, source="hard_negative").count() == 40
            assert session.query(Example).filter_by(dataset_id=result.dataset_id, source="teacher").count() == 160
            hard_negative_rows = session.query(Example).filter_by(dataset_id=result.dataset_id, source="hard_negative").all()
            for row in hard_negative_rows:
                output = json.loads(row.output_json)
                assert output["route"].startswith("blocked") or output["route"].endswith("_block") or output["route"] == "human_review"
            metric = session.query(JobEvent).filter_by(job_id=setup.job_id, event_type="metric").one()
            payload = json.loads(metric.payload_json)
            assert payload["generated_count"] == 200
            assert payload["validated_count"] == 200
            assert payload["hard_negative_count"] == 40
            assert payload["rejected_count"] == 0
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_hard_negative_shortfall_fails_before_dataset_resource(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "hard_negative_shortfall.db")
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200, hard_negative_min_count=40)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(DatasetGenWorkerError) as excinfo:
                run_dataset_gen_job(
                    session,
                    mib_home,
                    setup.job_id,
                    teacher_client=FakeTeacherClient(count=200, hard_negative_count=39),
                )
            session.commit()

        with factory() as session:
            job = session.get(Job, setup.job_id)
            assert job is not None
            assert job.status == "FAILED"
            assert job.error_class == "SCHEMA_VALIDATION_FAIL"
            assert session.get(JobResource, setup.job_id) is None
    finally:
        engine.dispose()

    assert excinfo.value.code == "DATASET_HARD_NEGATIVE_MIN_NOT_MET"
