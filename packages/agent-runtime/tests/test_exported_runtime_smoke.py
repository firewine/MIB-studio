from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def test_runtime_template_files_exist() -> None:
    root = Path("packages/agent-runtime/templates/zip_runtime")
    for relative in [
        "agents/run.py",
        "agents/verifier.py",
        "agents/fallback.py",
        "agents/security.py",
        "requirements-runtime.txt",
    ]:
        assert (root / relative).is_file()


def test_exported_runtime_native_and_openai_endpoints(tmp_path, monkeypatch) -> None:
    pytest = __import__("pytest")
    fastapi = pytest.importorskip("fastapi")
    pytest.importorskip("yaml")
    testclient = pytest.importorskip("fastapi.testclient")

    source = Path("packages/agent-runtime/templates/zip_runtime")
    runtime = tmp_path / "runtime"
    shutil.copytree(source, runtime)
    contract = {
        "agent_id": "support_router.v1",
        "route_catalog": {
            "schema_version": "route_catalog.v1",
            "sha256": "0" * 64,
            "routes": [
                {"route_id": "finance_income", "description": "Finance income", "is_unsafe": False, "order": 0},
                {"route_id": "human_review", "description": "Human review", "is_unsafe": True, "order": 1},
            ],
        },
    }
    (runtime / "agent_contract.yaml").write_text(__import__("yaml").safe_dump(contract))

    monkeypatch.setenv("MIB_RUNTIME_BEARER_TOKEN", "x" * 32)
    monkeypatch.syspath_prepend(str(runtime))
    sys.modules.pop("agents.run", None)
    app = __import__("agents.run", fromlist=["app"]).app
    client = testclient.TestClient(app)

    assert client.get("/healthz").json() == {"ok": True}
    assert client.post("/agents/support_router.v1/run", json={"text": "hi"}).status_code == 401
    authorized = {"Authorization": "Bearer " + "x" * 32}
    native = client.post("/agents/support_router.v1/run", json={"text": "hi"}, headers=authorized)
    assert native.status_code == 200
    assert native.json()["verifier_passed"] is True

    openai = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers=authorized,
    )
    assert openai.status_code == 200
    content = openai.json()["choices"][0]["message"]["content"]
    assert json.loads(content)["route"] == "finance_income"
    stream = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
        headers=authorized,
    )
    assert stream.status_code == 400
