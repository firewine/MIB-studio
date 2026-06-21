from __future__ import annotations

from pathlib import Path

import pytest

from services.shared.db.models import Job, JobResource
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.dataset_gen import DatasetGenWorkerError, run_dataset_gen_job
from tests.dataset.teacher_synthetic_helpers import (
    FakeTeacherClient,
    client_for,
    prepare_database,
    create_approved_teacher_synthetic_job,
)


@pytest.mark.asyncio
async def test_teacher_guard_synthetic_exact_overlap_zero(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "teacher_synthetic_overlap.db")
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(DatasetGenWorkerError) as excinfo:
                run_dataset_gen_job(
                    session,
                    mib_home,
                    setup.job_id,
                    teacher_client=FakeTeacherClient(count=200, overlap_input=setup.source_inputs[0]),
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

    assert excinfo.value.code == "TEACHER_GUARD_SYNTHETIC_OVERLAP"
