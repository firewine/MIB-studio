from __future__ import annotations

from pathlib import Path

import pytest

from tests.dataset.teacher_synthetic_helpers import (
    FakeTeacherClient,
    auth_headers,
    call_api,
    client_for,
    prepare_database,
    create_approved_teacher_synthetic_job,
    run_worker,
)


@pytest.mark.asyncio
async def test_generated_examples_require_review_decision_before_dataset_approval(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path, "teacher_synthetic_review.db")
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        setup = await create_approved_teacher_synthetic_job(client, target_count=200)
        result = run_worker(database_url, mib_home, setup.job_id, FakeTeacherClient(count=200))
        generated = await call_api(client.get(f"/datasets/{result.dataset_id}?limit=200", headers=auth_headers()))
        example_ids = [example["id"] for example in generated.json()["examples"]]
        response = await call_api(
            client.patch(
                f"/datasets/{result.dataset_id}",
                json={"status": "APPROVED", "approved_example_ids": example_ids[:20]},
                headers=auth_headers(),
            )
        )

    assert generated.status_code == 200, generated.text
    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "DATASET_REVIEW_INCOMPLETE"
    assert body["details"]["pending_count"] == 180
