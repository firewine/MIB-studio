from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.train_cuda import TrainCudaError, run_train_cuda_job
from tests.training.test_cuda_oom_isolation import CudaOomRunner
from tests.training.test_cuda_wrapper import create_queued_cuda_run, prepare_database


def auth_headers() -> dict[str, str]:
    return {"host": "127.0.0.1:8910", "authorization": "Bearer test-token"}


async def call_api(awaitable: Any) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


def client_for(database_url: str, mib_home: Path) -> httpx.AsyncClient:
    settings = Settings(
        app_env="production",
        dev_auth="bootstrap",
        bootstrap_token="test-token",
        database_url=database_url,
        mib_home=mib_home,
    )
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://127.0.0.1:8910")


@pytest.mark.asyncio
async def test_model_run_monitor_read_survives_worker_cuda_oom(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_cuda_run(database_url, mib_home)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(TrainCudaError):
                run_train_cuda_job(session, mib_home, job_id, runner=CudaOomRunner())
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        response = await call_api(client.get(f"/model-runs/{model_run_id}", headers=auth_headers()))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == model_run_id
    assert body["job_id"] == job_id
    assert body["status"] == "FAILED"
