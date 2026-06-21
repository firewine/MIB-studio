from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from services.shared.db.models import ExportArtifact, ModelRun
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.export import run_zip_export_job
from tests.agent_package.test_verifier import create_package
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for


async def create_exportable_package(tmp_path: Path) -> tuple[str, Path, dict[str, str]]:
    database_url, mib_home, package = await create_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            adapter_dir = tmp_path / "adapters" / model_run.id
            adapter_dir.mkdir(parents=True)
            if model_run.backend == "mlx":
                (adapter_dir / "adapters.npz").write_bytes(b"mlx adapter")
                (adapter_dir / "adapter_config.json").write_text('{"format":"mlx_lora_adapter"}\n', encoding="utf-8")
            else:
                (adapter_dir / "adapter.safetensors").write_bytes(b"cuda adapter")
                (adapter_dir / "adapter_config.json").write_text('{"format":"lora_adapter"}\n', encoding="utf-8")
            model_run.adapter_path = str(adapter_dir)
            session.commit()
    finally:
        engine.dispose()
    return database_url, mib_home, package


def run_export_worker(database_url: str, mib_home: Path, job_id: str) -> ExportArtifact:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            export_id = run_zip_export_job(session, mib_home, job_id)
            session.commit()
        with factory() as session:
            export = session.get(ExportArtifact, export_id)
            assert export is not None
            return export
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_export_api_creates_zip_job_and_serves_hash_verified_artifact(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
        assert accepted.status_code == 202
        job = accepted.json()
        assert job["created_resource_type"] == "export"
        assert job["created_resource_id"]

        queued = await call_api(client.get(f"/exports/{job['job_id']}", headers=auth_headers()))
        assert queued.status_code == 200
        assert queued.json()["status"] == "QUEUED"

    export = run_export_worker(database_url, mib_home, job["job_id"])
    assert export.status == "SUCCEEDED"
    assert export.manifest_sha256 and export.artifact_sha256

    async with client_for(database_url, mib_home) as client:
        completed = await call_api(client.get(f"/exports/{job['job_id']}", headers=auth_headers()))
        assert completed.status_code == 200
        body = completed.json()
        assert body["artifact_url"] == f"/exports/{job['job_id']}/artifact"
        assert body["reveal_url"] == f"/exports/{job['job_id']}/reveal"

        artifact = await call_api(client.get(body["artifact_url"], headers=auth_headers()))
        assert artifact.status_code == 200
        assert zipfile.is_zipfile(Path(export.artifact_path or ""))
        assert b"manifest.json" in artifact.content

        revealed = await call_api(client.post(body["reveal_url"], headers=auth_headers()))
        assert revealed.status_code == 200
        assert revealed.json()["artifact_path"] == export.artifact_path


@pytest.mark.asyncio
async def test_export_api_rejects_docker_until_m6_002(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "docker"},
                headers=auth_headers(),
            )
        )
    assert response.status_code == 409
    assert response.json()["error_code"] == "MILESTONE_LOCKED"
