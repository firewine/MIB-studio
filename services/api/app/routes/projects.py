from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.project import ProjectCreate, ProjectPage, ProjectPatch, ProjectRead
from services.api.app.services.project_service import ProjectService


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


@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(payload: ProjectCreate, session: Session = Depends(db_session)) -> ProjectRead:
    return ProjectService(session).create_project(payload)


@router.get("/projects", response_model=ProjectPage)
async def list_projects(
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    include_archived: bool = False,
    session: Session = Depends(db_session),
) -> ProjectPage:
    return ProjectService(session).list_projects(cursor=cursor, limit=limit, include_archived=include_archived)


@router.get("/projects/{id}", response_model=ProjectRead)
async def get_project(id: str, session: Session = Depends(db_session)) -> ProjectRead:  # noqa: A002
    return ProjectService(session).get_project(id)


@router.patch("/projects/{id}", response_model=ProjectRead)
async def update_project(id: str, payload: ProjectPatch, session: Session = Depends(db_session)) -> ProjectRead:  # noqa: A002
    return ProjectService(session).patch_project(id, payload)


@router.delete("/projects/{id}", status_code=204)
async def archive_project(id: str, session: Session = Depends(db_session)) -> Response:  # noqa: A002
    ProjectService(session).archive_project(id)
    return Response(status_code=204)
