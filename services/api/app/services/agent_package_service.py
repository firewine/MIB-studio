from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.agent_package import AgentPackageCreate, AgentPackagePage, AgentPackageRead
from services.api.app.services.agent_contract import AgentContractError, build_contract_yaml, slugify_agent
from services.api.app.services.benchmark_report import report_hash_status
from services.shared.db.models import AgentPackage, Benchmark, Dataset, ModelRun, Project
from services.shared.db.repositories.dataset_store import new_id


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class AgentPackageService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home

    def create_package(self, project_id: str, payload: AgentPackageCreate) -> AgentPackageRead:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})
        model_run = self._model_run_or_404(payload.model_run_id)
        benchmark = self._benchmark_or_404(payload.benchmark_id)
        dataset = self._dataset_or_404(model_run.dataset_id)
        self._validate_inputs(project_id, model_run, benchmark, dataset)

        version = self._next_contract_version(project_id)
        agent_slug = payload.agent_slug or slugify_agent(project.name)
        agent_id = f"{agent_slug}.v{version}"
        try:
            contract_yaml, contract_hash = build_contract_yaml(
                agent_id=agent_id,
                model_run=model_run,
                dataset=dataset,
                benchmark=benchmark,
                fallback=payload.fallback,
            )
        except AgentContractError as exc:
            raise APIError(
                "AGENT_CONTRACT_INVALID",
                "Agent contract could not be built.",
                status_code=409,
                details={"reason": str(exc)},
            ) from exc

        package = AgentPackage(
            id=new_id(),
            agent_id=agent_id,
            project_id=project_id,
            model_run_id=model_run.id,
            benchmark_id=benchmark.id,
            route_catalog_sha256=dataset.route_snapshot_sha256,
            contract_yaml=contract_yaml,
            contract_version=version,
            contract_sha256=contract_hash,
            created_at=utc_now(),
        )
        self.session.add(package)
        self.session.flush()
        return self._read_package(package)

    def list_packages(self, project_id: str, *, cursor: str | None = None, limit: int = 50) -> AgentPackagePage:
        self._project_or_404(project_id)
        statement = select(AgentPackage).where(AgentPackage.project_id == project_id)
        if cursor:
            created_at, package_id = json.loads(cursor)
            statement = statement.where(
                (AgentPackage.created_at < created_at) | ((AgentPackage.created_at == created_at) & (AgentPackage.id < package_id))
            )
        rows = list(
            self.session.scalars(statement.order_by(AgentPackage.created_at.desc(), AgentPackage.id.desc()).limit(limit + 1))
        )
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = json.dumps([last.created_at, last.id], separators=(",", ":"))
        return AgentPackagePage(items=[self._read_package(row) for row in rows[:limit]], next_cursor=next_cursor)

    def get_package(self, package_id: str) -> AgentPackageRead:
        package = self.session.get(AgentPackage, package_id)
        if package is None:
            raise APIError("AGENT_PACKAGE_NOT_FOUND", "AgentPackage does not exist.", status_code=404, details={"package_id": package_id})
        return self._read_package(package)

    def _validate_inputs(self, project_id: str, model_run: ModelRun, benchmark: Benchmark, dataset: Dataset) -> None:
        if model_run.project_id != project_id or benchmark.project_id != project_id or dataset.project_id != project_id:
            raise APIError("AGENT_PACKAGE_PROJECT_MISMATCH", "Package inputs must belong to the requested project.", status_code=409)
        if model_run.status != "SUCCEEDED" or not model_run.adapter_path or not model_run.adapter_sha256:
            raise APIError("MODEL_RUN_NOT_PACKAGEABLE", "ModelRun must be SUCCEEDED with adapter artifact metadata.", status_code=409)
        if benchmark.status != "COMPLETED":
            raise APIError("BENCHMARK_NOT_COMPLETED", "Benchmark must be COMPLETED before packaging.", status_code=409)
        hash_status, _ = report_hash_status(benchmark)
        if hash_status != "VALID":
            raise APIError(
                "BENCHMARK_REPORT_HASH_INVALID",
                "Benchmark report hash must recompute as VALID before packaging.",
                status_code=409,
                details={"benchmark_id": benchmark.id, "hash_status": hash_status},
            )

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _model_run_or_404(self, model_run_id: str) -> ModelRun:
        model_run = self.session.get(ModelRun, model_run_id)
        if model_run is None:
            raise APIError("MODEL_RUN_NOT_FOUND", "ModelRun does not exist.", status_code=404, details={"model_run_id": model_run_id})
        return model_run

    def _benchmark_or_404(self, benchmark_id: str) -> Benchmark:
        benchmark = self.session.get(Benchmark, benchmark_id)
        if benchmark is None:
            raise APIError("BENCHMARK_NOT_FOUND", "Benchmark does not exist.", status_code=404, details={"benchmark_id": benchmark_id})
        return benchmark

    def _dataset_or_404(self, dataset_id: str) -> Dataset:
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise APIError("DATASET_NOT_FOUND", "Dataset does not exist.", status_code=404, details={"dataset_id": dataset_id})
        return dataset

    def _next_contract_version(self, project_id: str) -> int:
        current = self.session.scalar(select(func.max(AgentPackage.contract_version)).where(AgentPackage.project_id == project_id))
        return int(current or 0) + 1

    def _read_package(self, package: AgentPackage) -> AgentPackageRead:
        return AgentPackageRead(
            id=package.id,
            agent_id=package.agent_id,
            project_id=package.project_id,
            model_run_id=package.model_run_id,
            benchmark_id=package.benchmark_id,
            route_catalog_sha256=package.route_catalog_sha256,
            contract_version=package.contract_version,
            contract_yaml=package.contract_yaml,
            contract_sha256=package.contract_sha256,
            created_at=package.created_at,
        )
