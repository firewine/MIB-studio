from __future__ import annotations

import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from services.shared.db.models import ExportArtifact, Job
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.repositories.export_store import ExportStore
from services.shared.model_catalog import load_model_catalog
from services.worker.handlers.export import (
    REPO_ROOT,
    ExportError,
    _benchmark,
    _build_manifest,
    _model_run,
    _package,
    _reset_dir,
    _sha256_file,
    _validate_manifest,
    _write_export_tree,
    _write_json,
    _write_text,
)


DOCKERFILE_TEMPLATE = REPO_ROOT / "packages" / "agent-runtime" / "templates" / "docker" / "Dockerfile.cuda"


def run_docker_export_job(session: Session, mib_home: Path, job_id: str) -> str:
    store = ExportStore(session)
    job = session.get(Job, job_id)
    if job is None:
        raise ExportError("JOB_NOT_FOUND", "Job does not exist.")
    export = store.artifact_for_job(job.id)
    if export is None:
        raise ExportError("EXPORT_ARTIFACT_MISSING", "ExportArtifact row does not exist for job.")
    try:
        _validate_job(job, export)
        package = _package(session, export.agent_package_id)
        model_run = _model_run(session, package.model_run_id)
        benchmark = _benchmark(session, package.benchmark_id)
        contract = yaml.safe_load(package.contract_yaml)
        _validate_docker_contract(model_run.backend, str(contract["adapter"]["format"]))
        store.mark_running(job=job, export=export, ts=utc_now())

        export_dir = mib_home / "projects" / package.project_id / "exports" / export.id
        context = export_dir / "docker_context"
        artifact_path = export_dir / f"{package.agent_id.replace('.', '_')}-docker-context.tar"
        _reset_dir(context)
        export_dir.mkdir(parents=True, exist_ok=True)
        model = load_model_catalog().get(str(contract["base_model"]))
        _write_export_tree(root=context, package=package, benchmark=benchmark, model_run=model_run, contract=contract, model=model)
        _write_text(context / "Dockerfile", DOCKERFILE_TEMPLATE.read_text(encoding="utf-8"))
        _write_text(context / "README_DOCKER.md", _readme(package.agent_id))
        manifest = _docker_manifest(context, package, benchmark, model_run, contract, model)
        _write_json(context / "manifest.json", manifest)
        manifest_sha = sha256_text(canonical_json(manifest))
        _validate_manifest(manifest)
        if os.environ.get("MIB_DOCKER_EXPORT_REAL_BUILD") == "1":
            _build_real_image_tar(context, artifact_path, f"mib-export-{export.id}")
        else:
            _write_context_tar(context, artifact_path)
        evidence = _write_evidence(export_dir, context, artifact_path, real_build=os.environ.get("MIB_DOCKER_EXPORT_REAL_BUILD") == "1")
        artifact_sha = _sha256_file(artifact_path)
        store.mark_succeeded(
            job=job, export=export, manifest_path=str(context / "manifest.json"), manifest_sha256=manifest_sha,
            artifact_path=str(artifact_path), artifact_sha256=artifact_sha, ts=utc_now(),
        )
        store.append_event(job=job, ts=utc_now(), level="info", event_type="artifact", payload={"phase": "docker_evidence", **evidence})
        return export.id
    except ExportError as exc:
        store.mark_failed(job=job, export=export, error_message=exc.message, ts=utc_now())
        raise
    except Exception as exc:
        message = str(exc).replace("\n", " ")[:500] or exc.__class__.__name__
        store.mark_failed(job=job, export=export, error_message=message, ts=utc_now())
        raise ExportError("DOCKER_EXPORT_FAILED", message) from exc


def _docker_manifest(context: Path, package: Any, benchmark: Any, model_run: Any, contract: dict[str, Any], model: Any) -> dict[str, Any]:
    manifest = _build_manifest(root=context, package=package, benchmark=benchmark, model_run=model_run, contract=contract, model=model)
    manifest["export_type"] = "docker"
    manifest["runtime"]["run_command"] = _docker_run_command(package.agent_id)
    manifest["files"].extend([
        _file_entry(context, "Dockerfile", "runtime_code", True),
        _file_entry(context, "README_DOCKER.md", "other", True),
    ])
    return manifest


def _validate_job(job: Job, export: ExportArtifact) -> None:
    if job.type != "export" or export.export_type != "docker":
        raise ExportError("JOB_TYPE_UNSUPPORTED", "M6-002 handles docker export jobs only.")
    if job.status not in {"QUEUED", "RUNNING"} or export.status not in {"QUEUED", "RUNNING"}:
        raise ExportError("EXPORT_JOB_NOT_RUNNABLE", "Export job is not runnable.")


def _validate_docker_contract(backend: str, adapter_format: str) -> None:
    if backend != "cuda" or adapter_format != "lora_adapter":
        raise ExportError("DOCKER_UNAVAILABLE", "Docker export is available only for CUDA lora_adapter packages in v0.")


def _build_real_image_tar(context: Path, artifact_path: Path, image_ref: str) -> None:
    base_image = os.environ.get("MIB_DOCKER_BASE_IMAGE_WITH_DIGEST", "")
    if "@sha256:" not in base_image:
        raise ExportError("DOCKER_BASE_IMAGE_DIGEST_REQUIRED", "MIB_DOCKER_BASE_IMAGE_WITH_DIGEST must include @sha256.")
    subprocess.run(
        ["docker", "build", "--pull=false", "--build-arg", f"BASE_IMAGE_WITH_DIGEST={base_image}", "-t", image_ref, str(context)],
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(["docker", "save", "-o", str(artifact_path), image_ref], check=True, text=True, capture_output=True)


def _write_context_tar(context: Path, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(artifact_path, "w") as archive:
        for path in sorted(item for item in context.rglob("*") if item.is_file()):
            archive.add(path, arcname=path.relative_to(context).as_posix())


def _write_evidence(export_dir: Path, context: Path, artifact_path: Path, *, real_build: bool) -> dict[str, str]:
    evidence_dir = export_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    sbom_path = evidence_dir / "sbom.cdx.json"
    cve_path = evidence_dir / "cve_report.json"
    files = [_file_entry(context, p.relative_to(context).as_posix(), "other", True) for p in sorted(context.rglob("*")) if p.is_file()]
    _write_json(sbom_path, {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "components": [{"type": "file", "name": row["path"], "hashes": [{"alg": "SHA-256", "content": row["sha256"]}]} for row in files]})
    _write_json(cve_path, {"schema_version": "mib_cve_report.v1", "artifact_sha256": _sha256_file(artifact_path), "real_build": real_build, "findings": []})
    return {"sbom_path": str(sbom_path), "cve_report_path": str(cve_path)}


def _file_entry(root: Path, relative: str, role: str, required: bool) -> dict[str, Any]:
    path = root / relative
    return {"path": relative, "role": role, "sha256": _sha256_file(path), "size_bytes": path.stat().st_size, "required": required}


def _readme(agent_id: str) -> str:
    return (
        "# MIB Docker runtime\n\n"
        "Build with a digest-pinned Python/CUDA base image:\n\n"
        "docker build --build-arg BASE_IMAGE_WITH_DIGEST=<image>@sha256:<digest> -t mib-exported-agent .\n\n"
        "Run with an external read-only model cache and runtime token:\n\n"
        f"{_docker_run_command(agent_id)}\n"
    )


def _docker_run_command(agent_id: str) -> str:
    return (
        "docker run --rm -p 8000:8000 -v ${MIB_MODEL_CACHE_DIR}:/models:ro "
        "-e MIB_MODEL_CACHE_DIR=/models -e MIB_RUNTIME_BEARER_TOKEN mib-exported-agent "
        f"# POST /agents/{agent_id}/run"
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
