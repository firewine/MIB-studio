from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.teacher_packet import (
    TeacherPacketApprovalRead,
    TeacherPacketPreviewRead,
    TeacherPacketPreviewRequest,
)
from services.api.app.services.teacher_packet_service import TeacherPacketService


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


@router.post("/projects/{id}/teacher-packets/preview", response_model=TeacherPacketPreviewRead)
async def preview_teacher_packet(
    id: str,  # noqa: A002
    payload: TeacherPacketPreviewRequest,
    session: Session = Depends(db_session),
) -> ORJSONResponse:
    packet = TeacherPacketService(session).preview_packet(id, payload)
    return ORJSONResponse(packet.model_dump())


@router.post("/teacher-packets/{id}/approve", response_model=TeacherPacketApprovalRead)
async def approve_teacher_packet(
    id: str,  # noqa: A002
    session: Session = Depends(db_session),
) -> ORJSONResponse:
    approval = TeacherPacketService(session).approve_packet(id)
    return ORJSONResponse(approval.model_dump())
