from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.preset import PresetPage, PresetRead
from services.api.app.services.preset_service import PresetService


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


@router.get("/presets", response_model=PresetPage)
async def list_presets(session: Session = Depends(db_session)) -> PresetPage:
    return PresetService(session).list_presets()


@router.get("/presets/{id}", response_model=PresetRead)
async def get_preset(id: str, session: Session = Depends(db_session)) -> PresetRead:  # noqa: A002
    return PresetService(session).get_preset(id)
