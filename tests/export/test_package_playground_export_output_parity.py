from __future__ import annotations

import pytest
import httpx

from tests.export.test_exported_runtime_smoke import ROUTES, create_runtime_root, load_core_router, runtime_app, runtime_contract


@pytest.mark.asyncio
async def test_package_playground_export_output_parity_for_canned_inputs(tmp_path, monkeypatch) -> None:
    root = create_runtime_root(tmp_path)
    app = runtime_app(root, monkeypatch)
    core = load_core_router()
    contract = runtime_contract()
    headers = {"Authorization": "Bearer " + "x" * 32}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://runtime.test") as client:
        for text in [
            "finance_income calculate 1200 salary tax",
            "risk_summary downside exposure overview",
            "human_review manual compliance review",
            "blocked_pii ssn private data",
        ]:
            payload = {"text": text, "allowed_routes": ROUTES}
            expected = core.run_router_inference(input_payload=payload, contract=contract)
            response = await client.post("/agents/support_router.v1/run", json={"input": payload}, headers=headers)
            assert response.status_code == 200
            assert response.json()["output"] == expected
