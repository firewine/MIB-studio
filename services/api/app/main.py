from __future__ import annotations

import json
import re
import socket
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.app.core.config import Settings, load_settings
from services.api.app.core.errors import (
    APIError,
    api_error_handler,
    error_response,
    http_error_handler,
    validation_error_handler,
)
from services.api.app.routes.presets import router as presets_router
from services.api.app.routes.projects import router as projects_router
from services.shared.db.session import create_sqlite_engine, session_factory
from services.shared.security.auth import SecurityError, format_bootstrap_line, validate_bearer_header
from services.shared.security.origin import (
    OriginSettings,
    cors_preflight_headers,
    host_is_allowed,
    is_cors_preflight,
    origin_is_allowed,
    requested_headers_are_allowed,
    requested_method_is_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_SEED = REPO_ROOT / "schemas" / "openapi.json"
ROUTE_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE"]


@lru_cache(maxsize=1)
def openapi_seed() -> dict[str, Any]:
    return json.loads(OPENAPI_SEED.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def operation_patterns() -> tuple[tuple[str, re.Pattern[str], str, str], ...]:
    patterns: list[tuple[str, re.Pattern[str], str, str]] = []
    for template, methods in openapi_seed().get("paths", {}).items():
        regex = "^" + re.sub(r"\{[^/]+}", r"[^/]+", re.escape(template).replace(r"\{", "{").replace(r"\}", "}")) + "$"
        for method, spec in methods.items():
            if isinstance(spec, dict) and "operationId" in spec:
                patterns.append((method.upper(), re.compile(regex), template, str(spec["operationId"])))
    return tuple(patterns)


def operation_id_for(method: str, path: str) -> tuple[str, str]:
    for pattern_method, pattern, template, operation_id in operation_patterns():
        if pattern_method == method.upper() and pattern.match(path):
            return operation_id, template
    return "unknown", path


def create_bootstrap_line(settings: Settings, port: int, pid: int | None = None) -> str:
    base_url = f"http://{settings.bind_host}:{port}"
    return format_bootstrap_line(base_url, settings.bootstrap_token, pid)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    app = FastAPI(title="MIB Studio Local Daemon", version=app_settings.version)
    app.state.settings = app_settings
    app.state.db_engine = create_sqlite_engine(app_settings.database_url)
    app.state.db_session_factory = session_factory(app.state.db_engine)

    def custom_openapi() -> dict[str, Any]:
        return openapi_seed()

    app.openapi = custom_openapi  # type: ignore[method-assign]
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    @app.middleware("http")
    async def local_api_guard(request: Request, call_next: Any) -> Response:
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        request.state.trace_id = trace_id
        origin_settings = OriginSettings(app_env=app_settings.app_env, bind_host=app_settings.bind_host)

        try:
            if not host_is_allowed(request.headers.get("host"), origin_settings):
                raise APIError(
                    "HOST_NOT_ALLOWED",
                    "Host header is not allowed.",
                    status_code=403,
                    details={"host": request.headers.get("host", "")},
                )

            origin = request.headers.get("origin")
            if not origin_is_allowed(origin, origin_settings):
                raise APIError(
                    "ORIGIN_NOT_ALLOWED",
                    "Origin is not allowed.",
                    status_code=403,
                    details={"origin": origin or ""},
                )

            requested_method = request.headers.get("access-control-request-method")
            if is_cors_preflight(request.method, origin, requested_method):
                if not requested_method_is_allowed(requested_method) or not requested_headers_are_allowed(
                    request.headers.get("access-control-request-headers")
                ):
                    raise APIError("CORS_PREFLIGHT_NOT_ALLOWED", "CORS preflight is not allowed.", status_code=403)
                response = Response(status_code=204)
                for key, value in cors_preflight_headers(origin or "").items():
                    response.headers[key] = value
                response.headers["x-trace-id"] = trace_id
                return response

            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > app_settings.body_max_bytes:
                raise APIError("REQUEST_TOO_LARGE", "Request body exceeds the configured limit.", status_code=413)

            if request.url.path != "/healthz":
                try:
                    validate_bearer_header(request.headers.get("authorization"), app_settings)
                except SecurityError as exc:
                    raise APIError(exc.error_code, exc.message, status_code=exc.status_code) from exc

            response = await call_next(request)
        except APIError as exc:
            response = error_response(exc, trace_id)

        response.headers["x-trace-id"] = trace_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": app_settings.version}

    app.include_router(projects_router)
    app.include_router(presets_router)

    @app.api_route("/{path:path}", methods=ROUTE_METHODS)
    async def milestone_locked(request: Request, path: str) -> ORJSONResponse:
        operation_id, template = operation_id_for(request.method, "/" + path)
        raise APIError(
            "MILESTONE_LOCKED",
            "This operation is locked until its implementation milestone.",
            status_code=409,
            details={
                "required_milestone": "future",
                "current_milestone": "M1-001",
                "operation_id": operation_id,
                "path_template": template,
            },
        )

    return app


app = create_app()


def run_daemon(settings: Settings | None = None) -> None:
    app_settings = settings or load_settings()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((app_settings.bind_host, app_settings.bind_port))
    server_socket.listen(128)
    port = int(server_socket.getsockname()[1])

    print(create_bootstrap_line(app_settings, port), flush=True)

    import uvicorn

    config = uvicorn.Config(
        create_app(app_settings),
        host=app_settings.bind_host,
        port=port,
        log_level="warning",
        log_config=None,
    )
    uvicorn.Server(config).run(sockets=[server_socket])


if __name__ == "__main__":
    run_daemon()
