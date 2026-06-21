from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from services.shared.db.models import AuditEvent
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for
from tests.eval.test_eval_runner import ROUTES
from tests.playground.test_playground_local_inference import create_playground_package


@pytest.mark.asyncio
async def test_playground_records_audit_metadata_without_raw_prompt_or_credential(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_playground_package(tmp_path)
    raw_texts = [
        "finance_income raw prompt should be hashed only",
        "ambiguous low confidence human_review raw prompt should be hashed only",
    ]
    async with client_for(database_url, mib_home) as client:
        for text in raw_texts:
            response = await call_api(
                client.post(
                    f"/agent-packages/{package['id']}/playground-runs",
                    json={"input": {"text": text, "allowed_routes": ROUTES}},
                    headers=auth_headers(),
                )
            )
            assert response.status_code == 200

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            rows = session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.resource_type == "agent_package",
                    AuditEvent.resource_id == package["id"],
                    AuditEvent.action == "playground_run",
                )
                .order_by(AuditEvent.ts.asc())
            ).all()
            assert len(rows) == 2
            for event in rows:
                assert event.contract_sha256 == package["contract_sha256"]
                details = json.loads(event.details_json)
                assert details["agent_package_id"] == package["id"]
                assert details["contract_sha256"] == package["contract_sha256"]
                assert details["input_sha256"]
                assert details["fallback_provider"] == "openai_compatible"
                assert details["verifier_status"] in {"PASS", "FAIL"}
                assert "keychain" not in event.details_json.lower()
                assert "api_key" not in event.details_json.lower()
                assert all(raw_text not in event.details_json for raw_text in raw_texts)
    finally:
        engine.dispose()
