from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.job import JobAcceptedResponse, JobControlResponse, JobSubmitRequest, ResumeJobRequest
from services.api.app.services.dataset_service import DatasetService
from services.api.app.services.job_control_service import JobControlService
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


@router.post("/projects/{id}/jobs", response_model=JobAcceptedResponse, status_code=202)
async def submit_project_job(
    id: str,  # noqa: A002
    payload: JobSubmitRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> JobAcceptedResponse:
    trace_id = str(getattr(request.state, "trace_id", "missing-trace-id"))
    if payload.type == "train":
        return TrainingService(session, home).submit_train_job(
            id,
            payload,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
    return DatasetService(session, home).submit_project_job(
        id,
        payload,
        idempotency_key=idempotency_key,
        trace_id=trace_id,
    )


@router.delete("/jobs/{job_id}", response_model=JobControlResponse, status_code=202)
async def cancel_job(
    job_id: str,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> JobControlResponse:
    return JobControlService(session, home).cancel_job(job_id)


@router.post("/jobs/{job_id}/resume", response_model=JobControlResponse, status_code=202)
async def resume_job(
    job_id: str,
    payload: ResumeJobRequest,
    request: Request,
    session: Session = Depends(db_session),
    home: Path = Depends(mib_home),
) -> JobControlResponse:
    trace_id = str(getattr(request.state, "trace_id", "missing-trace-id"))
    return JobControlService(session, home).resume_job(job_id, payload, trace_id=trace_id)
