from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.benchmark import BenchmarkPage, BenchmarkRead, BenchmarkReportRead
from services.api.app.services.benchmark_service import BenchmarkService


router = APIRouter()


async def db_session(request: Request) -> AsyncGenerator[Session, None]:
    factory: sessionmaker[Session] = request.app.state.db_session_factory
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mib_home(request: Request) -> Path:
    return request.app.state.settings.mib_home


@router.get("/projects/{id}/benchmarks", response_model=BenchmarkPage)
async def list_benchmarks(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    page = BenchmarkService(session, home).list_benchmarks(id, cursor=cursor, limit=limit, status=status)
    return ORJSONResponse(page.model_dump())


@router.get("/benchmarks/{id}", response_model=BenchmarkRead)
async def get_benchmark(
    id: str,  # noqa: A002
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    benchmark = BenchmarkService(session, home).get_benchmark(id)
    return ORJSONResponse(benchmark.model_dump())


@router.get("/benchmarks/{id}/report", response_model=BenchmarkReportRead)
async def get_benchmark_report(
    id: str,  # noqa: A002
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    report = BenchmarkService(session, home).get_report(id)
    return ORJSONResponse(report.model_dump())
