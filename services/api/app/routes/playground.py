from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.playground import PlaygroundRunRequest, PlaygroundRunResponse
from services.api.app.services.playground_service import PlaygroundService


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


@router.post("/agent-packages/{agent_package_id}/playground-runs", response_model=PlaygroundRunResponse)
async def run_playground(
    agent_package_id: str,
    payload: PlaygroundRunRequest,
    session: Session = Depends(db_session),
) -> ORJSONResponse:
    result = PlaygroundService(session).run_playground(agent_package_id=agent_package_id, payload=payload)
    return ORJSONResponse(result.model_dump())
