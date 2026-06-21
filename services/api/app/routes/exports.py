from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import ORJSONResponse, Response
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.export import ExportParams, ExportRead, RevealExportResponse
from services.api.app.schemas.job import JobAcceptedResponse
from services.api.app.services.export_service import ExportService


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


@router.post("/projects/{id}/export", response_model=JobAcceptedResponse, status_code=202)
async def create_export(
    id: str,  # noqa: A002
    payload: ExportParams,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    trace_id = str(getattr(request.state, "trace_id", "missing-trace-id"))
    accepted = ExportService(session, home).submit_export(id, payload, idempotency_key=idempotency_key, trace_id=trace_id)
    return ORJSONResponse(accepted.model_dump(), status_code=202)


@router.get("/exports/{job_id}", response_model=ExportRead)
async def get_export(
    job_id: str,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    export = ExportService(session, home).get_export(job_id)
    return ORJSONResponse(export.model_dump())


@router.get("/exports/{job_id}/artifact")
async def download_export_artifact(
    job_id: str,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> Response:
    path = ExportService(session, home).artifact_path(job_id)
    return Response(
        path.read_bytes(),
        media_type="application/octet-stream",
        headers={"content-disposition": f'attachment; filename="{path.name}"'},
    )


@router.post("/exports/{job_id}/reveal", response_model=RevealExportResponse)
async def reveal_export_artifact(
    job_id: str,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    path = ExportService(session, home).reveal_export(job_id)
    return ORJSONResponse(RevealExportResponse(artifact_path=str(path), revealed=True).model_dump())
