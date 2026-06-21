from __future__ import annotations

import hashlib
import ipaddress
import platform
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit


SERVICE_NAME = "MIB Studio"
SERVICE_REF = quote(SERVICE_NAME, safe="")
LOCAL_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}


class CredentialStoreUnavailable(Exception):
    def __init__(self, message: str | None = None) -> None:
        self.platform = platform.system() or "unknown"
        super().__init__(message or "OS keychain is unavailable.")


@dataclass(frozen=True)
class NormalizedCredentialBaseUrl:
    value: str
    origin: str


class KeyringCredentialStore:
    def set_secret(self, account: str, secret: str) -> None:
        try:
            import keyring

            keyring.set_password(SERVICE_NAME, account, secret)
        except Exception as exc:
            raise CredentialStoreUnavailable(str(exc)) from exc

    def delete_secret(self, account: str) -> None:
        try:
            import keyring

            keyring.delete_password(SERVICE_NAME, account)
        except Exception as exc:
            if exc.__class__.__name__ == "PasswordDeleteError":
                return
            raise CredentialStoreUnavailable(str(exc)) from exc


def credential_account(provider: str, base_url: str) -> str:
    return f"credential:{provider}:{hashlib.sha256(base_url.encode('utf-8')).hexdigest()}"


def credential_keychain_ref(account: str) -> str:
    return f"keyring://{SERVICE_REF}/{account}"


def normalize_credential_base_url(provider: str, raw_base_url: str) -> NormalizedCredentialBaseUrl:
    parts = urlsplit(raw_base_url)
    if not parts.scheme or not parts.netloc:
        raise ValueError("base_url must include scheme and host")
    if parts.username or parts.password:
        raise ValueError("base_url must not include username or password")
    if parts.query or parts.fragment:
        raise ValueError("base_url must not include query or fragment")

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("base_url scheme must be http or https")

    host = _normalize_host(parts.hostname)
    port = parts.port
    if provider == "openai":
        if scheme != "https" or host != "api.openai.com" or port not in {None, 443}:
            raise ValueError("openai credentials require https://api.openai.com")
    elif provider == "openai_compatible":
        if scheme == "http" and host not in LOCAL_HTTP_HOSTS:
            raise ValueError("http base_url is allowed only for localhost OpenAI-compatible providers")
        _reject_private_non_local_ip(host)
    else:
        raise ValueError("unsupported credential provider")

    normalized_netloc = _netloc(host, scheme, port)
    origin = f"{scheme}://{normalized_netloc}"
    path = _normalize_path(parts.path)
    value = urlunsplit((scheme, normalized_netloc, path, "", ""))
    return NormalizedCredentialBaseUrl(value=value, origin=origin)


def _normalize_host(hostname: str | None) -> str:
    if not hostname:
        raise ValueError("base_url must include host")
    host = hostname.rstrip(".").lower()
    if not host:
        raise ValueError("base_url must include host")
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("base_url host is invalid") from exc


def _netloc(host: str, scheme: str, port: int | None) -> str:
    bracketed = f"[{host}]" if ":" in host and not host.startswith("[") else host
    if port is None or (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        return bracketed
    return f"{bracketed}:{port}"


def _normalize_path(path: str) -> str:
    if not path or path == "/":
        return ""
    return path.rstrip("/")


def _reject_private_non_local_ip(host: str) -> None:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if host in LOCAL_HTTP_HOSTS:
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified:
        raise ValueError("private or metadata IP base_url is not allowed")
