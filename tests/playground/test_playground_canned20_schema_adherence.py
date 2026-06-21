from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tests.eval.test_benchmark_report import auth_headers, call_api, client_for
from tests.eval.test_eval_runner import ROUTES
from tests.playground.test_playground_local_inference import create_playground_package


CANNED_INPUTS = [
    "finance_income income calculation for a salary adjustment",
    "finance_income revenue summary with 1200 in monthly income",
    "risk_summary summarize exposure and downside risk",
    "risk_summary volatility risk overview for a portfolio",
    "investment_advice_block block direct stock buy advice",
    "investment_advice_block sell recommendation request",
    "human_review escalate this manual approval case",
    "human_review compliance review needed before reply",
    "blocked_pii user shared ssn and passport details",
    "blocked_pii private personal identifier in request",
    "blocked_unsupported illegal exploit request",
    "blocked_unsupported unsupported malware workflow",
    "finance_income calculate tax on 4500 revenue",
    "risk_summary give a downside summary",
    "investment_advice_block investment advice about a stock",
    "human_review needs human review",
    "blocked_pii pii disclosure",
    "blocked_unsupported unsupported hack request",
    "finance_income profit and cost estimate",
    "risk_summary risk exposure overview",
]


@pytest.mark.asyncio
async def test_playground_canned20_outputs_schema_adherent_json(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_playground_package(tmp_path)
    schema = json.loads(Path("schemas/router_output.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    async with client_for(database_url, mib_home) as client:
        for text in CANNED_INPUTS:
            response = await call_api(
                client.post(
                    f"/agent-packages/{package['id']}/playground-runs",
                    json={"input": {"text": text, "allowed_routes": ROUTES}},
                    headers=auth_headers(),
                )
            )
            assert response.status_code == 200
            body = response.json()
            assert body["verifier_status"] == "PASS"
            assert body["fallback_required"] is False
            assert body["fallback_used"] is False
            assert body["output"]["route"] in ROUTES
            validator.validate(body["output"])
