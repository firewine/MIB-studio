from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import yaml
from safetensors.numpy import save_file

from services.shared.db.models import AgentPackage, ExportArtifact, ModelRun
from services.api.app.services.agent_contract import contract_sha256
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.export import run_zip_export_job
from tests.agent_package.test_contract_builder import create_valid_report, fine_tuned_model_run_id
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for
from tests.eval.test_benchmark_report import completed_benchmark


def write_valid_cuda_adapter(adapter_dir: Path) -> None:
    save_file(
        {"base_model.model.router.lora_A.weight": np.ones((1, 1), dtype=np.float32)},
        adapter_dir / "adapter.safetensors",
    )
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps({"format": "lora_adapter", "peft_type": "LORA"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_valid_mlx_adapter(adapter_dir: Path) -> None:
    np.savez(adapter_dir / "adapters.npz", layers_0=np.ones((1,), dtype=np.float32))
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps({"format": "mlx_lora_adapter"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_adapter_manifest(adapter_dir: Path, *, trainer_backend: str) -> tuple[str, str]:
    run_dir = adapter_dir.parent
    rows = [
        {
            "path": str(path.relative_to(run_dir)),
            "sha256": _sha256_bytes(path.read_bytes()),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(item for item in adapter_dir.rglob("*") if item.is_file())
    ]
    adapter_sha256 = sha256_text(canonical_json(rows))
    manifest = {
        "schema_version": "adapter_manifest.v1",
        "trainer_backend": trainer_backend,
        "adapter_sha256": adapter_sha256,
        "files": rows,
    }
    if trainer_backend == "mlx_lm":
        manifest["adapter_format"] = "mlx_lora_adapter"
    manifest_text = canonical_json(manifest) + "\n"
    (run_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
    return adapter_sha256, sha256_text(manifest_text)


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


async def create_exportable_package(tmp_path: Path) -> tuple[str, Path, dict[str, str]]:
    database_url, mib_home, fixture = completed_benchmark(tmp_path)
    await create_valid_report(database_url, mib_home, fixture.benchmark_id)
    model_run_id = fine_tuned_model_run_id(fixture.targets)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, model_run_id)
            assert model_run is not None
            adapter_dir = tmp_path / "runs" / model_run.id / "adapter"
            adapter_dir.mkdir(parents=True)
            if model_run.backend == "mlx":
                write_valid_mlx_adapter(adapter_dir)
                adapter_sha256, manifest_sha256 = write_adapter_manifest(adapter_dir, trainer_backend="mlx_lm")
            else:
                write_valid_cuda_adapter(adapter_dir)
                adapter_sha256, manifest_sha256 = write_adapter_manifest(adapter_dir, trainer_backend="llamafactory")
            model_run.adapter_path = str(adapter_dir)
            model_run.adapter_sha256 = adapter_sha256
            model_run.artifact_manifest_sha256 = manifest_sha256
            session.commit()
    finally:
        engine.dispose()
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
    package = response.json()
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
async def test_export_api_accepts_cuda_docker_and_rejects_mlx_docker(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        response = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "docker"},
                headers=auth_headers(),
            )
        )
    assert response.status_code == 202
    assert response.json()["created_resource_type"] == "export"

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            stored = session.get(AgentPackage, package["id"])
            assert model_run is not None and stored is not None
            model_run.backend = "mlx"
            model_run.method = "mlx_lora"
            contract = yaml.safe_load(stored.contract_yaml)
            contract["adapter"]["format"] = "mlx_lora_adapter"
            stored.contract_yaml = yaml.safe_dump(contract, sort_keys=False)
            stored.contract_sha256 = contract_sha256(stored.contract_yaml)
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        rejected = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "docker"},
                headers=auth_headers(),
            )
        )
    assert rejected.status_code == 409
    assert rejected.json()["error_code"] == "DOCKER_UNAVAILABLE"
    assert rejected.json()["details"]["export_type"] == "docker"
