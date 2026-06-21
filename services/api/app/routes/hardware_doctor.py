from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.hardware import HardwareProfileRead, HardwareScanRequest, JobAcceptedResponse
from services.api.app.services.hardware_service import HardwareService


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


@router.post("/hardware-doctor/scan", response_model=JobAcceptedResponse, status_code=202)
async def submit_hardware_scan(
    payload: HardwareScanRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(db_session),
) -> JobAcceptedResponse:
    trace_id = str(getattr(request.state, "trace_id", "missing-trace-id"))
    return HardwareService(session).submit_scan(payload, idempotency_key=idempotency_key, trace_id=trace_id)


@router.get("/hardware-doctor/result", response_model=HardwareProfileRead)
async def get_hardware_result(session: Session = Depends(db_session)) -> HardwareProfileRead:
    return HardwareService(session).latest()
