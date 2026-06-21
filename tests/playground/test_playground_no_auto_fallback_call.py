from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from services.shared.db.models import AuditEvent, Credential
from services.shared.db.session import create_sqlite_engine, session_factory
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for
from tests.eval.test_eval_runner import ROUTES
from tests.playground.test_playground_local_inference import create_playground_package


@pytest.mark.asyncio
async def test_playground_does_not_call_fallback_before_user_approval(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_playground_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/agent-packages/{package['id']}/playground-runs",
                json={
                    "input": {
                        "text": "ambiguous low confidence finance_income request",
                        "allowed_routes": ROUTES,
                    },
                    "approve_fallback": False,
                },
                headers=auth_headers(),
            )
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verifier_status"] == "FAIL"
    assert body["fallback_required"] is True
    assert body["fallback_used"] is False
    assert any(error.startswith("confidence_threshold:") for error in body["verifier_errors"])

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            credential_audits = session.scalars(select(AuditEvent).where(AuditEvent.event_type == "credential_access")).all()
            assert credential_audits == []
            event = session.get(AuditEvent, body["audit_event_id"])
            assert event is not None
            details = json.loads(event.details_json)
            assert details["fallback_decision"] == "requires_user_approval"
            assert details["fallback_required"] is True
            assert details["fallback_used"] is False
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_playground_approved_fallback_requires_local_credential(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_playground_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            credential = session.scalar(select(Credential).where(Credential.provider == "openai_compatible"))
            assert credential is not None
            credential.is_revoked = 1
            credential.revoked_at = "2026-01-01T00:00:00.000Z"
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/agent-packages/{package['id']}/playground-runs",
                json={
                    "input": {
                        "text": "ambiguous low confidence risk_summary request",
                        "allowed_routes": ROUTES,
                    },
                    "approve_fallback": True,
                },
                headers=auth_headers(),
            )
        )
    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "FALLBACK_CREDENTIAL_REQUIRED"
    assert body["details"]["provider"] == "openai_compatible"
    assert body["details"]["audit_event_id"]

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            event = session.get(AuditEvent, body["details"]["audit_event_id"])
            assert event is not None
            details = json.loads(event.details_json)
            assert details["fallback_decision"] == "missing_credential"
            assert details["fallback_required"] is True
            assert details["fallback_used"] is False
    finally:
        engine.dispose()
