from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator
from sqlalchemy.orm import Session

from services.shared.db.models import AgentPackage, Benchmark, ExportArtifact, Job, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.repositories.export_store import ExportStore
from services.shared.model_catalog import ModelSpec, load_model_catalog
from services.worker.handlers.export_adapter_validation import ExportError, adapter_required_paths, copy_adapter


REPO_ROOT = Path(__file__).resolve().parents[3]
ZIP_TEMPLATE = REPO_ROOT / "packages" / "agent-runtime" / "templates" / "zip_runtime"
LOADER_ROOT = REPO_ROOT / "packages" / "agent-runtime" / "loaders"
SCHEMA_ROOT = REPO_ROOT / "schemas"
MANIFEST_SCHEMA_PATH = SCHEMA_ROOT / "export_manifest.schema.json"
BASE_MANIFEST_FILES = [
    ("agent_contract.yaml", "agent_contract", True),
    ("route_catalog.json", "route_catalog", True),
    ("benchmark/report.json", "benchmark_report", True),
    ("base_model_manifest.json", "model_manifest", True),
    ("schemas/router_input.schema.json", "input_schema", True),
    ("schemas/router_output.schema.json", "output_schema", True),
    ("runtime/agents/run.py", "runtime_entrypoint", True),
    ("runtime/agents/verifier.py", "runtime_code", True),
    ("runtime/agents/router_inference.py", "runtime_code", True),
    ("runtime/loaders/transformers_lora.py", "runtime_code", True),
    ("runtime/loaders/mlx_lora.py", "runtime_code", True),
    ("requirements-runtime.txt", "runtime_requirements", True),
]


def run_zip_export_job(session: Session, mib_home: Path, job_id: str) -> str:
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
        model = load_model_catalog().get(str(contract["base_model"]))
        ts = utc_now()
        store.mark_running(job=job, export=export, ts=ts)
        export_dir = mib_home / "projects" / package.project_id / "exports" / export.id
        root = export_dir / "root"
        artifact_path = export_dir / f"{package.agent_id.replace('.', '_')}-{export.export_type}.zip"
        _reset_dir(root)
        export_dir.mkdir(parents=True, exist_ok=True)
        _write_export_tree(root=root, package=package, benchmark=benchmark, model_run=model_run, contract=contract, model=model)
        manifest = _build_manifest(root=root, package=package, benchmark=benchmark, model_run=model_run, contract=contract, model=model)
        _write_json(root / "manifest.json", manifest)
        manifest_sha = sha256_text(canonical_json(manifest))
        _validate_manifest(manifest)
        _write_zip(root, artifact_path)
        artifact_sha = _sha256_file(artifact_path)
        store.mark_succeeded(
            job=job, export=export, manifest_path=str(root / "manifest.json"), manifest_sha256=manifest_sha,
            artifact_path=str(artifact_path), artifact_sha256=artifact_sha, ts=utc_now(),
        )
        return export.id
    except ExportError as exc:
        store.mark_failed(job=job, export=export, error_message=exc.message, ts=utc_now())
        raise
    except Exception as exc:
        message = str(exc).replace("\n", " ")[:500] or exc.__class__.__name__
        store.mark_failed(job=job, export=export, error_message=message, ts=utc_now())
        raise ExportError("EXPORT_FAILED", message) from exc


def _write_export_tree(*, root: Path, package: AgentPackage, benchmark: Benchmark, model_run: ModelRun, contract: dict[str, Any], model: ModelSpec) -> None:
    _write_text(root / "agent_contract.yaml", package.contract_yaml)
    _write_json(root / "route_catalog.json", contract["route_catalog"])
    for schema_name in ("router_input.schema.json", "router_output.schema.json"):
        _copy(SCHEMA_ROOT / schema_name, root / "schemas" / schema_name)
    _copy(Path(str(benchmark.report_path)), root / "benchmark" / "report.json")
    _write_json(root / "base_model_manifest.json", _base_model_manifest(model))
    copy_adapter(model_run=model_run, contract=contract, root=root)
    for source, target in ((ZIP_TEMPLATE / "agents", "agents"), (LOADER_ROOT, "loaders")):
        shutil.copytree(source, root / "runtime" / target)
    _copy(ZIP_TEMPLATE / "requirements-runtime.txt", root / "requirements-runtime.txt")
    _write_text(root / "README_RUN.md", _readme(package.agent_id))
    if "gemma" in model.id.lower():
        _write_text(root / "licenses" / "GEMMA_TERMS_NOTICE.txt", "Gemma model use requires compliance with Google's Gemma Terms of Use.\n")


def _build_manifest(*, root: Path, package: AgentPackage, benchmark: Benchmark, model_run: ModelRun, contract: dict[str, Any], model: ModelSpec) -> dict[str, Any]:
    adapter_format = str(contract["adapter"]["format"])
    required_paths = adapter_required_paths(adapter_format)
    files = [_file_entry(root, path, role, required) for path, role, required in _manifest_files(adapter_format, model.id)]
    return {
        "schema_version": "export_manifest.v1",
        "agent_package_id": package.id,
        "agent_id": package.agent_id,
        "contract_sha256": package.contract_sha256,
        "route_catalog_sha256": package.route_catalog_sha256,
        "benchmark_report_sha256": benchmark.report_sha256,
        "export_type": "zip",
        "created_at": utc_now(),
        "adapter": {"format": adapter_format, "required_paths": required_paths},
        "base_model": {
            "id": model.id,
            "hf_commit_sha": model.hf_commit_sha,
            "materialization": "external_cache",
            "cache_env": "MIB_MODEL_CACHE_DIR",
            "cache_subdir": model.cache_subdir,
            "required_files": _model_required_files(model),
        },
        "runtime": {
            "native_endpoint": "/agents/{agent_id}/run",
            "openai_endpoint": "/v1/chat/completions",
            "entrypoint": "agents.run:app",
            "run_command": "cd runtime && python3 -m uvicorn agents.run:app --host 127.0.0.1 --port 8000",
            "compatible_backends": [model_run.backend],
            "requires_bearer_token_env": "MIB_RUNTIME_BEARER_TOKEN",
            "requires_bearer_token_min_length": 32,
        },
        "files": files,
    }


def _manifest_files(adapter_format: str, model_id: str) -> list[tuple[str, str, bool]]:
    files = list(BASE_MANIFEST_FILES)
    files.extend((path, "adapter" if path.endswith((".safetensors", ".npz")) else "adapter_config", True) for path in adapter_required_paths(adapter_format))
    if "gemma" in model_id.lower():
        files.append(("licenses/GEMMA_TERMS_NOTICE.txt", "license_notice", False))
    return files


def _validate_job(job: Job, export: ExportArtifact) -> None:
    if job.type != "export" or export.export_type != "zip":
        raise ExportError("JOB_TYPE_UNSUPPORTED", "M6-001 handles zip export jobs only.")
    if job.status not in {"QUEUED", "RUNNING"} or export.status not in {"QUEUED", "RUNNING"}:
        raise ExportError("EXPORT_JOB_NOT_RUNNABLE", "Export job is not runnable.")


def _package(session: Session, package_id: str) -> AgentPackage:
    package = session.get(AgentPackage, package_id)
    if package is None:
        raise ExportError("AGENT_PACKAGE_NOT_FOUND", "AgentPackage does not exist.")
    return package


def _model_run(session: Session, model_run_id: str) -> ModelRun:
    model_run = session.get(ModelRun, model_run_id)
    if model_run is None or model_run.status != "SUCCEEDED" or not model_run.adapter_path or not model_run.adapter_sha256 or not model_run.artifact_manifest_sha256:
        raise ExportError("MODEL_RUN_NOT_EXPORTABLE", "ModelRun is not exportable.")
    return model_run


def _benchmark(session: Session, benchmark_id: str) -> Benchmark:
    benchmark = session.get(Benchmark, benchmark_id)
    if benchmark is None or benchmark.status != "COMPLETED" or not benchmark.report_path or not benchmark.report_sha256:
        raise ExportError("BENCHMARK_REPORT_INVALID", "Benchmark report is not exportable.")
    report = json.loads(Path(str(benchmark.report_path)).read_text(encoding="utf-8"))
    if _benchmark_report_sha256(report) != benchmark.report_sha256:
        raise ExportError("BENCHMARK_REPORT_INVALID", "Benchmark report hash does not match.")
    return benchmark


def _base_model_manifest(model: ModelSpec) -> dict[str, Any]: return {"id": model.id, "hf_commit_sha": model.hf_commit_sha, "cache_subdir": model.cache_subdir, "required_files": _model_required_files(model)}

def _model_required_files(model: ModelSpec) -> list[dict[str, Any]]: return [{"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes} for item in model.required_files]


def _benchmark_report_sha256(report: dict[str, Any]) -> str:
    without_hash = json.loads(json.dumps(report, sort_keys=True))
    without_hash.get("artifact_hashes", {}).pop("report_sha256", None)
    return sha256_text(canonical_json(without_hash))


def _file_entry(root: Path, relative: str, role: str, required: bool) -> dict[str, Any]:
    path = root / relative
    return {"path": relative, "role": role, "sha256": _sha256_file(path), "size_bytes": path.stat().st_size, "required": required}


def _validate_manifest(manifest: dict[str, Any]) -> None:
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft7Validator(schema).iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        raise ExportError("EXPORT_MANIFEST_INVALID", "; ".join(error.message for error in errors))


def _write_zip(root: Path, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(artifact_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(root).as_posix())


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _write_json(path: Path, value: Any) -> None: _write_text(path, canonical_json(value) + "\n")

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _readme(agent_id: str) -> str:
    return (
        "# MIB exported runtime\n\n"
        "Install requirements-runtime.txt, provide MIB_MODEL_CACHE_DIR and MIB_RUNTIME_BEARER_TOKEN, then run:\n\n"
        "cd runtime && python3 -m uvicorn agents.run:app --host 127.0.0.1 --port 8000\n\n"
        f"Native endpoint: POST /agents/{agent_id}/run\n"
    )


def _sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def utc_now() -> str: return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
