from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.training import ModelRunPage, ModelRunRead
from services.api.app.services.training_service import TrainingService


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


@router.get("/projects/{id}/model-runs", response_model=ModelRunPage)
async def list_model_runs(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    backend: str | None = None,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    page = TrainingService(session, home).list_model_runs(id, cursor=cursor, limit=limit, status=status, backend=backend)
    return ORJSONResponse(page.model_dump())


@router.get("/model-runs/{id}", response_model=ModelRunRead)
async def get_model_run(
    id: str,  # noqa: A002
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    model_run = TrainingService(session, home).get_model_run(id)
    return ORJSONResponse(model_run.model_dump())
