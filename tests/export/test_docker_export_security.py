from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from services.shared.db.models import ExportArtifact
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.export_docker import run_docker_export_job
from tests.export.test_export_api import create_exportable_package
from tests.eval.test_benchmark_report import auth_headers, call_api, client_for


def run_docker_worker(database_url: str, mib_home: Path, job_id: str) -> ExportArtifact:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            export_id = run_docker_export_job(session, mib_home, job_id)
            session.commit()
        with factory() as session:
            export = session.get(ExportArtifact, export_id)
            assert export is not None
            return export
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_docker_export_worker_writes_context_tar_manifest_and_evidence(tmp_path: Path) -> None:
    database_url, mib_home, package = await create_exportable_package(tmp_path)
    async with client_for(database_url, mib_home) as client:
        accepted = await call_api(
            client.post(
                f"/projects/{package['project_id']}/export",
                json={"agent_package_id": package["id"], "export_type": "docker"},
                headers=auth_headers(),
            )
        )
    assert accepted.status_code == 202

    export = run_docker_worker(database_url, mib_home, accepted.json()["job_id"])
    assert export.status == "SUCCEEDED"
    artifact_path = Path(export.artifact_path or "")
    manifest_path = Path(export.manifest_path or "")
    assert artifact_path.suffix == ".tar"
    assert export.manifest_sha256 and export.artifact_sha256

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["export_type"] == "docker"
    assert manifest["runtime"]["openai_endpoint"] == "/v1/chat/completions"
    assert "docker run" in manifest["runtime"]["run_command"]
    assert ":/models:ro" in manifest["runtime"]["run_command"]
    assert any(item["path"] == "Dockerfile" and item["role"] == "runtime_code" for item in manifest["files"])

    with tarfile.open(artifact_path) as archive:
        names = {member.name for member in archive.getmembers() if member.isfile()}
    assert {"Dockerfile", "manifest.json", "runtime/agents/run.py", "requirements-runtime.txt"} <= names
    assert not any(name.startswith("base_model/") or name.startswith("model_cache/") for name in names)

    evidence_dir = artifact_path.parent / "evidence"
    scan = subprocess.run(
        [
            sys.executable,
            "scripts/scan_export_artifact.py",
            "--artifact",
            str(artifact_path),
            "--sbom",
            str(evidence_dir / "sbom.cdx.json"),
            "--cve-report",
            str(evidence_dir / "cve_report.json"),
            "--require-docker-evidence",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert scan.returncode == 0, scan.stdout + scan.stderr
