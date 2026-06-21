from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from services.api.app.services.verifier_service import VerifierService
from services.shared.db.models import AgentPackage
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.agent_package.test_contract_builder import create_valid_report, fine_tuned_model_run_id
from tests.eval.test_benchmark_report import completed_benchmark


CORE_VERIFIER_PATH = Path("packages/agent-runtime/core/verifier.py")


def load_core_verifier() -> Any:
    spec = importlib.util.spec_from_file_location("test_runtime_verifier", CORE_VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_output(route: str = "finance_income", confidence: float = 0.91) -> dict[str, Any]:
    return {
        "route": route,
        "task_type": "provide_advice",
        "requires_calculation": False,
        "requires_human_review": False,
        "confidence": confidence,
    }


def minimal_contract() -> dict[str, Any]:
    return {
        "route_catalog": {
            "routes": [
                {"route_id": "finance_income"},
                {"route_id": "human_review"},
            ]
        },
        "verifiers": [{"name": "confidence_threshold", "config": {"threshold": 0.7}}],
        "fallback": {
            "enabled": True,
            "provider": "openai_compatible",
            "model": "teacher-small",
            "condition": {"type": "confidence_lt", "threshold": 0.7},
        },
    }


async def create_package(tmp_path: Path) -> tuple[str, Path, dict[str, Any]]:
    from tests.eval.test_benchmark_report import auth_headers, call_api, client_for

    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    await create_valid_report(database_url, mib_home, fixture.benchmark_id)
    model_run_id = fine_tuned_model_run_id(fixture.targets)
    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/projects/{fixture.project_id}/agent-packages",
                json={
                    "model_run_id": model_run_id,
                    "benchmark_id": fixture.benchmark_id,
                    "fallback": {
                        "enabled": True,
                        "provider": "openai_compatible",
                        "model": "teacher-small",
                        "condition": {"type": "confidence_lt", "threshold": 0.7},
                    },
                },
                headers=auth_headers(),
            )
        )
        assert response.status_code == 201
        return database_url, mib_home, response.json()


def test_core_verifier_passes_valid_router_output_from_json_string(tmp_path: Path) -> None:
    core = load_core_verifier()
    contract = minimal_contract()
    result = core.verify_router_output(output='{"route":"finance_income","task_type":"provide_advice","requires_calculation":false,"requires_human_review":false,"confidence":0.91}', contract=contract)
    assert result.verifier_status == "PASS"
    assert result.verifier_errors == []
    assert result.fallback_required is False
    assert result.fallback_used is False


def test_core_verifier_reports_json_schema_route_and_confidence_failures(tmp_path: Path) -> None:
    core = load_core_verifier()
    contract = minimal_contract()
    output = {"route": "unknown_route", "task_type": "provide_advice", "requires_calculation": False, "requires_human_review": False, "confidence": 0.2}
    result = core.verify_router_output(output=output, contract=contract)
    assert result.verifier_status == "FAIL"
    assert result.fallback_required is True
    assert result.fallback_used is False
    assert any(error.startswith("route_allowed:") for error in result.verifier_errors)
    assert any(error.startswith("confidence_threshold:") for error in result.verifier_errors)

    approved = core.verify_router_output(output=output, contract=contract, approve_fallback=True)
    assert approved.verifier_status == "FAIL"
    assert approved.fallback_required is False
    assert approved.fallback_used is True


def test_core_verifier_reports_invalid_json_and_schema_errors(tmp_path: Path) -> None:
    core = load_core_verifier()
    contract = minimal_contract()
    invalid_json = core.verify_router_output(output="{bad json", contract=contract)
    assert invalid_json.verifier_status == "FAIL"
    assert invalid_json.verifier_errors[0].startswith("json_parse:")

    missing_field = core.verify_router_output(output={"route": "finance_income", "confidence": 0.8}, contract=contract)
    assert missing_field.verifier_status == "FAIL"
    assert any(error.startswith("output_schema:") for error in missing_field.verifier_errors)


@pytest.mark.asyncio
async def test_api_verifier_service_reuses_runtime_core_against_agent_package(tmp_path: Path) -> None:
    database_url, _, package = await create_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            stored = session.get(AgentPackage, package["id"])
            assert stored is not None
            service = VerifierService(session)
            passed = service.verify_package_output(agent_package_id=stored.id, output=valid_output())
            assert passed["verifier_status"] == "PASS"
            assert passed["contract_sha256"] == package["contract_sha256"]

            low_confidence = service.verify_package_output(agent_package_id=stored.id, output=valid_output(confidence=0.1))
            assert low_confidence["verifier_status"] == "FAIL"
            assert low_confidence["fallback_required"] is True
            assert any(error.startswith("confidence_threshold:") for error in low_confidence["verifier_errors"])
    finally:
        engine.dispose()
