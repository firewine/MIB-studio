from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from services.shared.db.models import Benchmark, Credential, Job, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.eval.test_eval_set_freeze import (
    auth_headers,
    call_api,
    client_for,
    create_benchmark_dataset_and_approve,
    prepare_database,
)


def test_project_benchmark_job_creates_queued_benchmark_resource(tmp_path: Path) -> None:
    asyncio.run(run_project_benchmark_job_creates_queued_benchmark_resource(tmp_path))


async def run_project_benchmark_job_creates_queued_benchmark_resource(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, example_ids = await create_benchmark_dataset_and_approve(client)
        eval_set = await call_api(
            client.post(
                f"/projects/{project_id}/eval-sets",
                json={
                    "purpose": "benchmark_gold",
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "labeler_ids": ["domain_labeler", "security_labeler", "tie_breaker"],
                    "kappa": 0.81,
                },
                headers=auth_headers(),
            )
        )
        assert eval_set.status_code == 201
        model_run_id, credential_id = create_ready_benchmark_inputs(database_url, project_id, dataset_id)
        accepted = await call_api(
            client.post(
                f"/projects/{project_id}/jobs",
                json={
                    "type": "benchmark",
                    "params": benchmark_params(eval_set.json()["id"], model_run_id, credential_id),
                },
                headers={**auth_headers(), "idempotency-key": "benchmark-submit-1"},
            )
        )
        replay = await call_api(
            client.post(
                f"/projects/{project_id}/jobs",
                json={
                    "type": "benchmark",
                    "params": benchmark_params(eval_set.json()["id"], model_run_id, credential_id),
                },
                headers={**auth_headers(), "idempotency-key": "benchmark-submit-1"},
            )
        )
        listed = await call_api(client.get(f"/projects/{project_id}/benchmarks", headers=auth_headers()))

    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "QUEUED"
    assert body["type"] == "benchmark"
    assert body["created_resource_type"] == "benchmark"
    assert body["created_resource_id"]
    assert replay.status_code == 202
    assert replay.json()["job_id"] == body["job_id"]
    assert replay.json()["idempotency_replayed"] is True
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == body["created_resource_id"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            job = session.get(Job, body["job_id"])
            benchmark = session.get(Benchmark, body["created_resource_id"])
            assert job is not None
            assert benchmark is not None
            assert job.type == "benchmark"
            assert job.resource_class == "gpu_exclusive"
            assert job.eval_set_id == eval_set.json()["id"]
            assert benchmark.job_id == job.id
            assert benchmark.status == "QUEUED"
            assert benchmark.parity_status == "NA"
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_project_benchmark_job_rejects_incomplete_target_set(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"

    async with client_for(database_url, mib_home) as client:
        project_id, dataset_id, example_ids = await create_benchmark_dataset_and_approve(client)
        eval_set = await call_api(
            client.post(
                f"/projects/{project_id}/eval-sets",
                json={
                    "purpose": "benchmark_gold",
                    "dataset_id": dataset_id,
                    "example_ids": example_ids,
                    "labeler_ids": ["domain_labeler", "security_labeler", "tie_breaker"],
                    "kappa": 0.81,
                },
                headers=auth_headers(),
            )
        )
        model_run_id, credential_id = create_ready_benchmark_inputs(database_url, project_id, dataset_id)
        params = benchmark_params(eval_set.json()["id"], model_run_id, credential_id)
        params["targets"] = [target for target in params["targets"] if target["target_type"] != "teacher"]
        response = await call_api(
            client.post(
                f"/projects/{project_id}/jobs",
                json={"type": "benchmark", "params": params},
                headers=auth_headers(),
            )
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "BENCHMARK_TARGETS_REQUIRED"


def create_ready_benchmark_inputs(database_url: str, project_id: str, dataset_id: str) -> tuple[str, str]:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    config_json = canonical_json({"schema_version": "training_config.v1", "mock": False})
    try:
        with factory() as session:
            credential = Credential(
                id="cred_benchmark_teacher",
                provider="openai_compatible",
                base_url="https://teacher.example.test",
                keychain_ref="keyring://MIB%20Studio/credential:openai_compatible:test",
                is_revoked=0,
                created_at="2026-06-23T00:00:00.000Z",
            )
            model_run = ModelRun(
                id="model_run_benchmark_ready",
                project_id=project_id,
                dataset_id=dataset_id,
                base_model="google/gemma-2b-it",
                backend="cuda",
                method="qlora",
                adapter_path="adapters/model_run_benchmark_ready",
                adapter_sha256="a" * 64,
                artifact_manifest_sha256="b" * 64,
                status="SUCCEEDED",
                seed=123,
                config_json=config_json,
                config_hash=sha256_text(config_json),
                resumable=1,
                started_at="2026-06-23T00:00:00.000Z",
                ended_at="2026-06-23T00:05:00.000Z",
                created_at="2026-06-23T00:00:00.000Z",
            )
            session.add_all([credential, model_run])
            session.commit()
            return model_run.id, credential.id
    finally:
        engine.dispose()


def benchmark_params(eval_set_id: str, model_run_id: str, credential_id: str) -> dict[str, Any]:
    return {
        "eval_set_id": eval_set_id,
        "seeds": [42, 123, 456],
        "targets": [
            {
                "target_key": "prompt_gemma",
                "target_type": "prompt_only",
                "backend": "prompt_only",
                "base_model": "google/gemma-2b-it",
                "prompt_template_sha256": "410ca967a64b6a71d53d82cd9102f0767c5d94d4af27640826fb60feced9e9dd",
            },
            {
                "target_key": "ft_cuda",
                "target_type": "fine_tuned",
                "backend": "cuda",
                "model_run_id": model_run_id,
            },
            {
                "target_key": "teacher_gpt",
                "target_type": "teacher",
                "backend": "teacher",
                "credential_id": credential_id,
                "teacher_base_url_origin": "https://teacher.example.test",
            },
            {
                "target_key": "rule_router",
                "target_type": "rule_based",
                "backend": "rule_based",
                "routing_rules_path": "rules/router.routing_rules.v1.yaml",
                "routing_rules_sha256": "1b9501f1ba0bbd527beacab98e34d5355d676c0ba60b151a22be87e369232934",
            },
        ],
    }
