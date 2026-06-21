from __future__ import annotations

from dataclasses import dataclass


ALLOWED_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"}
ALLOWED_HEADERS = {
    "authorization",
    "content-type",
    "idempotency-key",
    "last-event-id",
    "x-trace-id",
}
VARY_VALUE = "Origin, Access-Control-Request-Method, Access-Control-Request-Headers"


@dataclass(frozen=True)
class OriginSettings:
    app_env: str
    bind_host: str


def host_name(host_header: str | None) -> str:
    if not host_header:
        return ""
    return host_header.rsplit("@", 1)[-1].split(":", 1)[0].strip().lower()


def host_is_allowed(host_header: str | None, settings: OriginSettings) -> bool:
    host = host_name(host_header)
    if host == "127.0.0.1":
        return True
    return settings.app_env == "development" and host == "localhost"


def origin_is_allowed(origin: str | None, settings: OriginSettings) -> bool:
    if not origin:
        return True
    allowed = {"tauri://localhost"}
    if settings.app_env == "development":
        allowed.add("http://localhost:1420")
    return origin in allowed


def is_cors_preflight(method: str, origin: str | None, requested_method: str | None) -> bool:
    return method.upper() == "OPTIONS" and bool(origin) and bool(requested_method)


def requested_headers_are_allowed(header_value: str | None) -> bool:
    if not header_value:
        return True
    requested = {part.strip().lower() for part in header_value.split(",") if part.strip()}
    return requested <= ALLOWED_HEADERS


def requested_method_is_allowed(method: str | None) -> bool:
    return bool(method) and method.upper() in ALLOWED_METHODS


def cors_preflight_headers(origin: str) -> dict[str, str]:
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": ", ".join(sorted(ALLOWED_METHODS)),
        "access-control-allow-headers": ", ".join(sorted(ALLOWED_HEADERS)),
        "vary": VARY_VALUE,
    }
