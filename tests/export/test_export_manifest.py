from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
from safetensors.numpy import save_file
from jsonschema import Draft7Validator

from services.shared.db.models import ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.export import ExportError, run_zip_export_job
from tests.export.test_export_api import create_exportable_package, run_export_worker
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for


@pytest.mark.asyncio
async def test_export_manifest_schema_hash_roles_and_secret_scan(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    export = run_export_worker(database_url, mib_home, accepted.json()["job_id"])
    manifest_path = Path(export.manifest_path or "")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(Path("schemas/export_manifest.schema.json").read_text(encoding="utf-8"))
    Draft7Validator(schema).validate(manifest)
    assert export.manifest_sha256 == sha256_text(canonical_json(manifest))
    assert manifest["base_model"]["materialization"] == "external_cache"
    assert manifest["base_model"]["cache_env"] == "MIB_MODEL_CACHE_DIR"
    roles = {item["role"] for item in manifest["files"]}
    assert {"agent_contract", "route_catalog", "input_schema", "output_schema", "benchmark_report", "model_manifest"} <= roles
    assert all(not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts for item in manifest["files"])

    with zipfile.ZipFile(export.artifact_path or "") as archive:
        names = set(archive.namelist())
    assert "manifest.json" in names
    assert "base_model_manifest.json" in names
    assert not any(name.startswith("base_model/") or name.startswith("model_cache/") for name in names)

    scan = subprocess.run(
        [sys.executable, "scripts/scan_export_artifact.py", "--artifact", str(export.artifact_path)],
        check=False,
        text=True,
        capture_output=True,
    )
    assert scan.returncode == 0, scan.stdout + scan.stderr


@pytest.mark.asyncio
async def test_export_rejects_adapter_format_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            adapter_dir = Path(str(model_run.adapter_path))
            (adapter_dir / "adapter.safetensors").unlink()
            (adapter_dir / "adapters.npz").write_bytes(b"wrong format")
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(ExportError, match="Missing adapter file"):
                run_zip_export_job(session, mib_home, accepted.json()["job_id"])
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_export_rejects_malformed_safetensors_adapter(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            adapter_dir = Path(str(model_run.adapter_path))
            (adapter_dir / "adapter.safetensors").write_bytes(b"cuda adapter")
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(ExportError, match="Invalid adapter file: adapter.safetensors"):
                run_zip_export_job(session, mib_home, accepted.json()["job_id"])
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_export_rejects_adapter_config_format_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            adapter_dir = Path(str(model_run.adapter_path))
            (adapter_dir / "adapter_config.json").write_text('{"format":"mlx_lora_adapter"}\n', encoding="utf-8")
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(ExportError, match="adapter_config.json format mismatch"):
                run_zip_export_job(session, mib_home, accepted.json()["job_id"])
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_export_rejects_adapter_file_hash_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            adapter_dir = Path(str(model_run.adapter_path))
            save_file({"base_model.model.router.lora_A.weight": np.zeros((1, 1), dtype=np.float32)}, adapter_dir / "adapter.safetensors")
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(ExportError, match="Adapter artifact hash mismatch"):
                run_zip_export_job(session, mib_home, accepted.json()["job_id"])
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_export_rejects_adapter_manifest_hash_mismatch(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            model_run = session.get(ModelRun, package["model_run_id"])
            assert model_run is not None
            manifest_path = Path(str(model_run.adapter_path)).parent / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["trainer_backend"] = "tampered"
            manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
            session.commit()
    finally:
        engine.dispose()

    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "zip"},
                headers=auth_headers(),
            )
        )
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(ExportError, match="Adapter artifact manifest hash mismatch"):
                run_zip_export_job(session, mib_home, accepted.json()["job_id"])
    finally:
        engine.dispose()
