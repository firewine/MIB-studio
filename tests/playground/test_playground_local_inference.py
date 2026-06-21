from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.shared.db.models import AuditEvent
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.agent_package.test_verifier import create_package
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for
from tests.eval.test_eval_runner import ROUTES


async def create_playground_package(tmp_path: Path) -> tuple[str, Path, dict[str, str]]:
    return await create_package(tmp_path)


@pytest.mark.asyncio
async def test_playground_run_returns_verified_json_output_and_audit_event(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_playground_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/agent-packages/{package['id']}/playground-runs",
                json={
                    "input": {
                        "text": "Route this finance_income request and calculate 1200 salary tax impact.",
                        "allowed_routes": ROUTES,
                    }
                },
                headers=auth_headers(),
            )
        )
        assert response.status_code == 200
        body = response.json()
        assert body["output"] == {
            "route": "finance_income",
            "task_type": "provide_advice",
            "requires_calculation": True,
            "requires_human_review": False,
            "confidence": 0.94,
        }
        assert body["verifier_status"] == "PASS"
        assert body["verifier_errors"] == []
        assert body["fallback_required"] is False
        assert body["fallback_used"] is False
        assert body["audit_event_id"]

        locked = await call_api(
            client.post(f"/agents/{package['agent_id']}/run", json={"input": "not implemented"}, headers=auth_headers())
        )
        assert locked.status_code == 409
        assert locked.json()["error_code"] == "MILESTONE_LOCKED"

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            event = session.get(AuditEvent, body["audit_event_id"])
            assert event is not None
            assert event.event_type == "agent_run"
            assert event.resource_type == "agent_package"
            assert event.resource_id == package["id"]
            assert event.contract_sha256 == package["contract_sha256"]
            details = json.loads(event.details_json)
            assert details["agent_package_id"] == package["id"]
            assert details["contract_sha256"] == package["contract_sha256"]
            assert details["output_route"] == "finance_income"
            assert details["verifier_status"] == "PASS"
            assert "Route this finance_income request" not in event.details_json
            assert "keychain" not in event.details_json.lower()
    finally:
        engine.dispose()
