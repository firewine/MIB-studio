from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.schemas.credential import CredentialPage, CredentialUpsert
from services.api.app.services.credential_service import CredentialService, SecretStore


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


def credential_store(request: Request) -> SecretStore:
    return request.app.state.credential_store


@router.get("/credentials", response_model=CredentialPage)
async def list_credentials(
    session: Session = Depends(db_session),
    store: SecretStore = Depends(credential_store),
) -> CredentialPage:
    return CredentialService(session, store).list_credentials()


@router.put("/credentials/{provider}", status_code=204)
async def upsert_credential(
    provider: str,
    payload: CredentialUpsert,
    session: Session = Depends(db_session),
    store: SecretStore = Depends(credential_store),
) -> Response:
    CredentialService(session, store).upsert_credential(provider, payload)
    return Response(status_code=204)


@router.delete("/credentials/{provider}", status_code=204)
async def delete_credential(
    provider: str,
    session: Session = Depends(db_session),
    store: SecretStore = Depends(credential_store),
) -> Response:
    CredentialService(session, store).delete_credential(provider)
    return Response(status_code=204)
