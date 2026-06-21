from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.api.app.services.benchmark_report import canonical_report_sha256
from services.shared.db.models import Benchmark, EvalRun, Job
from services.shared.db.repositories.dataset_store import canonical_json
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.eval import run_benchmark_eval_job
from tests.eval.test_eval_runner import FakeEvaluator, create_benchmark_fixture, prepare_database


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


def completed_benchmark(
    tmp_path: Path,
    *,
    fine_tuned_backends: tuple[str, ...] = ("cuda", "mlx"),
    include_local_large: bool = False,
    local_large_available: bool = False,
) -> tuple[str, Path, Any]:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            fixture = create_benchmark_fixture(
                session,
                mib_home,
                fine_tuned_backends=fine_tuned_backends,
                include_local_large=include_local_large,
            )
            run_benchmark_eval_job(session, fixture.job_id, evaluator=FakeEvaluator(), local_large_available=local_large_available)
            session.commit()
    finally:
        engine.dispose()
    return database_url, mib_home, fixture


@pytest.mark.asyncio
async def test_benchmark_report_generates_schema_valid_report_and_valid_hash(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)

    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.get(f"/benchmarks/{fixture.benchmark_id}/report", headers=auth_headers()))
        assert response.status_code == 200
        payload = response.json()

        listed = await call_api(client.get(f"/projects/{fixture.project_id}/benchmarks", headers=auth_headers()))
        assert listed.status_code == 200
        assert listed.json()["items"][0]["hash_status"] == "VALID"

        read = await call_api(client.get(f"/benchmarks/{fixture.benchmark_id}", headers=auth_headers()))
        assert read.status_code == 200
        assert read.json()["hash_status"] == "VALID"
        assert read.json()["parity_status"] == "PASS"

    report = payload["report"]
    assert payload["hash_status"] == "VALID"
    assert payload["report_sha256"] == report["artifact_hashes"]["report_sha256"]
    assert canonical_report_sha256(report) == payload["report_sha256"]
    assert report["schema_version"] == "benchmark_report.v1"
    assert report["eval_set"]["purpose"] == "benchmark_gold"
    assert report["eval_set"]["sample_count"] == 200
    assert report["overlap_check"] == {
        "exact_duplicate_count": 0,
        "semantic_flag_count": 0,
        "encoder_version": "sentence-transformers/all-MiniLM-L6-v2@frozen",
        "threshold": 0.85,
        "passed": True,
    }

    targets = {target["target_key"]: target for target in report["targets"]}
    assert targets["local_large_optional"]["target_status"] == "SKIPPED_OPTIONAL"
    assert targets["local_large_optional"]["seeds"] == [0]
    assert "mean_metrics" not in targets["local_large_optional"]
    assert targets["ft_cuda"]["seeds"] == [42, 123, 456]
    assert set(targets["ft_cuda"]["mean_metrics"]) >= {"route_accuracy", "latency_p50_ms", "effective_cost_per_task_usd"}
    assert set(targets["ft_cuda"]["std_metrics"]) == set(targets["ft_cuda"]["ci95"])

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            benchmark = session.get(Benchmark, fixture.benchmark_id)
            job = session.get(Job, fixture.job_id)
            assert benchmark is not None
            assert job is not None
            assert benchmark.status == "COMPLETED"
            assert benchmark.report_sha256 == payload["report_sha256"]
            assert benchmark.parity_status == "PASS"
            assert Path(str(benchmark.report_path)).name == "benchmark_report.json"
            assert job.status == "SUCCEEDED"
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_benchmark_report_detects_manual_report_file_tampering(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    async with client_for(database_url, mib_home) as client:
        generated = await call_api(client.get(f"/benchmarks/{fixture.benchmark_id}/report", headers=auth_headers()))
        assert generated.status_code == 200

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            benchmark = session.get(Benchmark, fixture.benchmark_id)
            assert benchmark is not None
            report_path = Path(str(benchmark.report_path))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["cost_assumptions"]["fallback_provider"] = "tampered-provider"
        report_path.write_text(canonical_json(report) + "\n", encoding="utf-8")
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.get(f"/benchmarks/{fixture.benchmark_id}/report", headers=auth_headers()))
        assert response.status_code == 200
        payload = response.json()
        assert payload["hash_status"] == "MISMATCH"
        assert payload["report"]["cost_assumptions"]["fallback_provider"] == "tampered-provider"


@pytest.mark.asyncio
async def test_benchmark_report_records_cuda_mlx_parity_fail(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            rows = session.query(EvalRun).filter_by(benchmark_id=fixture.benchmark_id, target_key="ft_mlx").all()
            assert rows
            for row in rows:
                metrics = json.loads(row.metrics_json)
                metrics["route_accuracy"] = 0.50
                row.metrics_json = canonical_json(metrics)
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.get(f"/benchmarks/{fixture.benchmark_id}/report", headers=auth_headers()))
        assert response.status_code == 200
        report = response.json()["report"]
        assert report["parity"]["status"] == "FAIL"
        route_accuracy = [item for item in report["parity"]["metrics"] if item["name"] == "route_accuracy"][0]
        assert route_accuracy["delta_pp"] > 2.0

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            benchmark = session.get(Benchmark, fixture.benchmark_id)
            assert benchmark is not None
            assert benchmark.parity_status == "FAIL"
    finally:
        engine.dispose()
