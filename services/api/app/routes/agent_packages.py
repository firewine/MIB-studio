from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.agent_package import AgentPackageCreate, AgentPackagePage, AgentPackageRead
from services.api.app.services.agent_package_service import AgentPackageService


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


@router.post("/projects/{id}/agent-packages", response_model=AgentPackageRead, status_code=201)
async def create_agent_package(
    id: str,  # noqa: A002
    payload: AgentPackageCreate,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    package = AgentPackageService(session, home).create_package(id, payload)
    return ORJSONResponse(package.model_dump(), status_code=201)


@router.get("/projects/{id}/agent-packages", response_model=AgentPackagePage)
async def list_agent_packages(
    id: str,  # noqa: A002
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    page = AgentPackageService(session, home).list_packages(id, cursor=cursor, limit=limit)
    return ORJSONResponse(page.model_dump())


@router.get("/agent-packages/{agent_package_id}", response_model=AgentPackageRead)
async def get_agent_package(
    agent_package_id: str,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> ORJSONResponse:
    package = AgentPackageService(session, home).get_package(agent_package_id)
    return ORJSONResponse(package.model_dump())
