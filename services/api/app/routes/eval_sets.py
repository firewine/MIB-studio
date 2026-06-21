from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.eval import EvalSetCreate, EvalSetPage, EvalSetRead
from services.api.app.services.eval_service import EvalSetService


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


@router.post("/projects/{id}/eval-sets", response_model=EvalSetRead, status_code=201)
async def create_eval_set(
    id: str,  # noqa: A002
    payload: EvalSetCreate,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    eval_set = EvalSetService(session, home).create_eval_set(id, payload)
    return ORJSONResponse(eval_set.model_dump(), status_code=201)


@router.get("/projects/{id}/eval-sets", response_model=EvalSetPage)
async def list_eval_sets(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    purpose: str | None = None,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    page = EvalSetService(session, home).list_eval_sets(id, cursor=cursor, limit=limit, purpose=purpose)
    return ORJSONResponse(page.model_dump())


@router.get("/eval-sets/{id}", response_model=EvalSetRead)
async def get_eval_set(
    id: str,  # noqa: A002
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    eval_set = EvalSetService(session, home).get_eval_set(id)
    return ORJSONResponse(eval_set.model_dump())
