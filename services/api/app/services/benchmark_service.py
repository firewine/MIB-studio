from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.benchmark import BenchmarkPage, BenchmarkRead, BenchmarkReportRead
from services.api.app.services.benchmark_report import BenchmarkReportBuilder, BenchmarkReportError, report_hash_status
from services.shared.db.models import Benchmark, Project


class BenchmarkService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home

    def list_benchmarks(
        self,
        project_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
    ) -> BenchmarkPage:
        self._project_or_404(project_id)
        statement = select(Benchmark).where(Benchmark.project_id == project_id)
        if status:
            statement = statement.where(Benchmark.status == status)
        if cursor:
            created_at, benchmark_id = json.loads(cursor)
            statement = statement.where(
                (Benchmark.created_at < created_at) | ((Benchmark.created_at == created_at) & (Benchmark.id < benchmark_id))
            )
        rows = list(self.session.scalars(statement.order_by(Benchmark.created_at.desc(), Benchmark.id.desc()).limit(limit + 1)))
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = json.dumps([last.created_at, last.id], separators=(",", ":"))
        return BenchmarkPage(items=[self._read_benchmark(row) for row in rows[:limit]], next_cursor=next_cursor)

    def get_benchmark(self, benchmark_id: str) -> BenchmarkRead:
        return self._read_benchmark(self._benchmark_or_404(benchmark_id))

    def get_report(self, benchmark_id: str) -> BenchmarkReportRead:
        benchmark = self._benchmark_or_404(benchmark_id)
        builder = BenchmarkReportBuilder(self.session, self.mib_home)
        status, report = report_hash_status(benchmark)
        if status == "MISSING" and builder.can_generate(benchmark):
            try:
                report = builder.generate_and_store(benchmark)
            except BenchmarkReportError as exc:
                raise APIError(
                    "BENCHMARK_REPORT_INVALID",
                    "Benchmark report could not be generated.",
                    status_code=409,
                    details={"benchmark_id": benchmark.id, "reason": str(exc)},
                ) from exc
            status, report = report_hash_status(benchmark)
        return BenchmarkReportRead(
            benchmark_id=benchmark.id,
            report_sha256=benchmark.report_sha256,
            hash_status=status,  # type: ignore[arg-type]
            report=report,
        )

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _benchmark_or_404(self, benchmark_id: str) -> Benchmark:
        benchmark = self.session.get(Benchmark, benchmark_id)
        if benchmark is None:
            raise APIError("BENCHMARK_NOT_FOUND", "Benchmark does not exist.", status_code=404, details={"benchmark_id": benchmark_id})
        return benchmark

    def _read_benchmark(self, benchmark: Benchmark) -> BenchmarkRead:
        hash_status, _ = report_hash_status(benchmark)
        return BenchmarkRead(
            id=benchmark.id,
            project_id=benchmark.project_id,
            job_id=benchmark.job_id,
            eval_set_id=benchmark.eval_set_id,
            status=benchmark.status,  # type: ignore[arg-type]
            report_sha256=benchmark.report_sha256,
            hash_status=hash_status,  # type: ignore[arg-type]
            parity_status=benchmark.parity_status,  # type: ignore[arg-type]
            created_at=benchmark.created_at,
            completed_at=benchmark.completed_at,
        )
