from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
import pytest
from jsonschema import Draft7Validator

from services.api.app.services.agent_contract import contract_sha256
from services.shared.db.models import AgentPackage, Benchmark, Project
from services.shared.db.repositories.dataset_store import canonical_json
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for, completed_benchmark


def fine_tuned_model_run_id(targets: list[dict[str, Any]], backend: str = "cuda") -> str:
    for target in targets:
        if target["target_type"] == "fine_tuned" and target["backend"] == backend:
            return str(target["model_run_id"])
    raise AssertionError(f"missing fine_tuned {backend} target")


async def create_valid_report(database_url: str, mib_home: Path, benchmark_id: str) -> dict[str, Any]:
    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.get(f"/benchmarks/{benchmark_id}/report", headers=auth_headers()))
        assert response.status_code == 200
        payload = response.json()
        assert payload["hash_status"] == "VALID"
        return payload


def load_contract_schema() -> dict[str, Any]:
    return json.loads(Path("schemas/agent_contract.schema.json").read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_agent_package_builder_creates_schema_valid_immutable_contract(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    report_payload = await create_valid_report(database_url, mib_home, fixture.benchmark_id)
    model_run_id = fine_tuned_model_run_id(fixture.targets)

    request = {
        "agent_slug": "support_router",
        "model_run_id": model_run_id,
        "benchmark_id": fixture.benchmark_id,
        "fallback": {
            "enabled": True,
            "provider": "openai_compatible",
            "model": "teacher-small",
            "condition": {"type": "confidence_lt", "threshold": 0.62},
        },
    }
    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.post(f"/projects/{fixture.project_id}/agent-packages", json=request, headers=auth_headers()))
        assert response.status_code == 201
        package = response.json()

        listed = await call_api(client.get(f"/projects/{fixture.project_id}/agent-packages", headers=auth_headers()))
        assert listed.status_code == 200
        assert listed.json()["items"][0]["id"] == package["id"]

        read = await call_api(client.get(f"/agent-packages/{package['id']}", headers=auth_headers()))
        assert read.status_code == 200
        assert read.json() == package

    contract = yaml.safe_load(package["contract_yaml"])
    Draft7Validator(load_contract_schema()).validate(contract)
    assert package["agent_id"] == "support_router.v1"
    assert package["contract_version"] == 1
    assert package["contract_sha256"] == contract_sha256(package["contract_yaml"])
    assert contract["agent_id"] == package["agent_id"]
    assert contract["adapter"]["path"] == f"adapter/{model_run_id}"
    assert contract["adapter"]["sha256"] == "a" * 64
    assert contract["fallback"] == request["fallback"]
    assert contract["benchmark_report"] == {
        "path": f"benchmark/{fixture.benchmark_id}/benchmark_report.json",
        "sha256": report_payload["report_sha256"],
    }
    assert contract["route_catalog"]["sha256"] == package["route_catalog_sha256"]
    assert [route["order"] for route in contract["route_catalog"]["routes"]] == list(range(6))
    assert contract["export_compatibility"]["supported_formats"] == ["zip", "docker"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            row = session.get(AgentPackage, package["id"])
            assert row is not None
            assert row.contract_sha256 == package["contract_sha256"]
            assert row.contract_yaml == package["contract_yaml"]
            assert row.route_catalog_sha256 == contract["route_catalog"]["sha256"]
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_agent_package_builder_rejects_benchmark_hash_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    await create_valid_report(database_url, mib_home, fixture.benchmark_id)
    model_run_id = fine_tuned_model_run_id(fixture.targets)

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
        response = await call_api(
            client.post(
                f"/projects/{fixture.project_id}/agent-packages",
                json={"model_run_id": model_run_id, "benchmark_id": fixture.benchmark_id, "fallback": {"enabled": False}},
                headers=auth_headers(),
            )
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error_code"] == "BENCHMARK_REPORT_HASH_INVALID"
        assert body["details"]["hash_status"] == "MISMATCH"


@pytest.mark.asyncio
async def test_agent_package_builder_allocates_versions_and_rejects_project_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    await create_valid_report(database_url, mib_home, fixture.benchmark_id)
    model_run_id = fine_tuned_model_run_id(fixture.targets)

    async with client_for(database_url, mib_home) as client:
        first = await call_api(
            client.post(
                f"/projects/{fixture.project_id}/agent-packages",
                json={"model_run_id": model_run_id, "benchmark_id": fixture.benchmark_id, "fallback": {"enabled": False}},
                headers=auth_headers(),
            )
        )
        assert first.status_code == 201
        second = await call_api(
            client.post(
                f"/projects/{fixture.project_id}/agent-packages",
                json={"agent_slug": "second_router", "model_run_id": model_run_id, "benchmark_id": fixture.benchmark_id, "fallback": {"enabled": False}},
                headers=auth_headers(),
            )
        )
        assert second.status_code == 201
        assert first.json()["agent_id"].endswith(".v1")
        assert second.json()["agent_id"] == "second_router.v2"

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            other = Project(id="other_project", name="Other", preset_id="router.basic.v1", created_at="2026-01-01T00:00:00.000Z", updated_at="2026-01-01T00:00:00.000Z")
            session.add(other)
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        mismatch = await call_api(
            client.post(
                "/projects/other_project/agent-packages",
                json={"model_run_id": model_run_id, "benchmark_id": fixture.benchmark_id, "fallback": {"enabled": False}},
                headers=auth_headers(),
            )
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["error_code"] == "AGENT_PACKAGE_PROJECT_MISMATCH"
