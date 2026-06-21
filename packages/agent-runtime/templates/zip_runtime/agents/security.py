from __future__ import annotations

import hmac
import os


TOKEN_ENV = "MIB_RUNTIME_BEARER_TOKEN"
MIN_TOKEN_LENGTH = 32


def expected_token() -> str:
    token = os.environ.get(TOKEN_ENV, "")
    if len(token) < MIN_TOKEN_LENGTH:
        raise RuntimeError(f"{TOKEN_ENV} must be at least {MIN_TOKEN_LENGTH} characters")
    return token


def authorize(authorization_header: str | None) -> bool:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False
    candidate = authorization_header.removeprefix("Bearer ").strip()
    return hmac.compare_digest(candidate, expected_token())
