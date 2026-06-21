from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.dataset import (
    DatasetBuildRequest,
    DatasetPage,
    DatasetPatch,
    DatasetRead,
    DatasetWithExamples,
    ExamplePatch,
    ExampleRead,
)
from services.api.app.services.dataset_service import DatasetService


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


@router.post("/projects/{id}/datasets", response_model=DatasetRead, status_code=201)
async def create_dataset(
    id: str,  # noqa: A002
    payload: DatasetBuildRequest,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    dataset = DatasetService(session, home).build_dataset(id, payload)
    return ORJSONResponse(dataset.model_dump(), status_code=201)


@router.get("/projects/{id}/datasets", response_model=DatasetPage)
async def list_datasets(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    page = DatasetService(session, home).list_datasets(id, cursor=cursor, limit=limit, status=status)
    return ORJSONResponse(page.model_dump())


@router.get("/datasets/{id}", response_model=DatasetWithExamples)
async def get_dataset(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    dataset = DatasetService(session, home).get_dataset(id, cursor=cursor, limit=limit)
    return ORJSONResponse(dataset.model_dump())


@router.patch("/datasets/{id}", response_model=DatasetRead)
async def update_dataset(
    id: str,  # noqa: A002
    payload: DatasetPatch,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    dataset = DatasetService(session, home).patch_dataset(id, payload)
    return ORJSONResponse(dataset.model_dump())


@router.patch("/examples/{id}", response_model=ExampleRead)
async def update_example(
    id: str,  # noqa: A002
    payload: ExamplePatch,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    example = DatasetService(session, home).patch_example(id, payload)
    return ORJSONResponse(example.model_dump())
