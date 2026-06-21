from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def request_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id or "missing-trace-id")


def error_payload(error: APIError, trace_id: str) -> dict[str, Any]:
    return {
        "error_code": error.error_code,
        "message": error.message,
        "details": error.details,
        "trace_id": trace_id,
    }


def error_response(error: APIError, trace_id: str) -> ORJSONResponse:
    response = ORJSONResponse(error_payload(error, trace_id), status_code=error.status_code)
    response.headers["x-trace-id"] = trace_id
    return response


def json_safe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for item in errors:
        copied = dict(item)
        if isinstance(copied.get("ctx"), dict):
            copied["ctx"] = {key: str(value) for key, value in copied["ctx"].items()}
        safe.append(copied)
    return safe


async def api_error_handler(request: Request, exc: APIError) -> ORJSONResponse:
    return error_response(exc, request_trace_id(request))


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> ORJSONResponse:
    return error_response(
        APIError(
            "VALIDATION_ERROR",
            "Request validation failed.",
            status_code=422,
            details={"errors": json_safe_errors(exc.errors())},
        ),
        request_trace_id(request),
    )


async def http_error_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> ORJSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    if exc.status_code == 405:
        code = "METHOD_NOT_ALLOWED"
    return error_response(
        APIError(code, str(exc.detail), status_code=exc.status_code),
        request_trace_id(request),
    )
