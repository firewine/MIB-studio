from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import urllib.request
from urllib.parse import quote
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from services.shared.model_catalog import ModelCatalog, ModelFile, ModelSpec, load_model_catalog


class ModelDownloader(Protocol):
    def download_file(self, *, model_id: str, revision: str, path: str, destination: Path) -> None:
        """Write the requested file to destination."""


class HTTPModelDownloader:
    def download_file(self, *, model_id: str, revision: str, path: str, destination: Path) -> None:
        model_part = quote(model_id, safe="/")
        path_part = quote(path, safe="/")
        url = f"https://huggingface.co/{model_part}/resolve/{revision}/{path_part}"
        request = urllib.request.Request(url, headers=auth_headers())
        with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)


@dataclass(frozen=True)
class ModelCacheResult:
    model_id: str
    hf_commit_sha: str
    cache_dir: Path
    required_files: tuple[str, ...]
    downloaded_files: tuple[str, ...]


class ModelCacheError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = 409
        self.details = details or {}
        super().__init__(message)


class ModelCacheService:
    def __init__(
        self,
        mib_home: Path,
        *,
        catalog_path: Path | None = None,
        downloader: ModelDownloader | None = None,
        offline: bool | None = None,
    ) -> None:
        self.mib_home = mib_home
        self.catalog_path = catalog_path
        self.offline = env_offline() if offline is None else offline
        self.downloader = downloader if downloader is not None or self.offline else HTTPModelDownloader()

    def ensure_model(self, base_model: str, backend: str, purpose: str) -> ModelCacheResult:
        catalog = load_model_catalog(self.catalog_path) if self.catalog_path else load_model_catalog()
        model = catalog.get(base_model)
        if backend not in model.allowed_backends:
            raise ModelCacheError(
                "MODEL_BACKEND_UNSUPPORTED",
                "Model is not allowed for the requested backend.",
                details={"model_id": model.id, "backend": backend, "allowed_backends": list(model.allowed_backends)},
            )

        cache_dir = self.model_cache_dir(model)
        lock_path = self.lock_path(model)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                return self._ensure_locked(model, catalog, cache_dir, purpose=purpose)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def model_cache_dir(self, model: ModelSpec) -> Path:
        return self.mib_home / "model_cache" / model.cache_subdir

    def lock_path(self, model: ModelSpec) -> Path:
        return self.mib_home / "model_cache" / "locks" / f"{model.cache_subdir}.lock"

    def _ensure_locked(
        self,
        model: ModelSpec,
        catalog: ModelCatalog,
        cache_dir: Path,
        *,
        purpose: str,
    ) -> ModelCacheResult:
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._verify_existing_files(model, cache_dir)
        missing = [item for item in model.required_files if not (cache_dir / item.path).exists()]
        if missing and self.offline:
            raise ModelCacheError(
                "MODEL_CACHE_MISS_OFFLINE",
                "Model cache is missing required files while offline mode is enabled.",
                details={
                    "model_id": model.id,
                    "hf_commit_sha": model.hf_commit_sha,
                    "missing_files": [item.path for item in missing],
                },
            )
        if missing and self.downloader is None:
            raise ModelCacheError(
                "MODEL_CACHE_MISS_OFFLINE",
                "Model cache is missing required files and no downloader is configured.",
                details={
                    "model_id": model.id,
                    "hf_commit_sha": model.hf_commit_sha,
                    "missing_files": [item.path for item in missing],
                },
            )

        downloaded: list[str] = []
        for item in missing:
            self._download_required_file(model, item, cache_dir, purpose=purpose)
            downloaded.append(item.path)
        self._verify_required_files(model, cache_dir, catalog)
        return ModelCacheResult(
            model_id=model.id,
            hf_commit_sha=model.hf_commit_sha,
            cache_dir=cache_dir,
            required_files=tuple(item.path for item in model.required_files),
            downloaded_files=tuple(downloaded),
        )

    def _verify_existing_files(self, model: ModelSpec, cache_dir: Path) -> None:
        for item in model.files:
            path = cache_dir / item.path
            if not path.exists():
                continue
            if sha256_file(path) != item.sha256:
                quarantined = quarantine_file(self.mib_home, model, path)
                raise ModelCacheError(
                    "MODEL_CACHE_HASH_MISMATCH",
                    "Cached model file hash does not match the strict catalog.",
                    details={"model_id": model.id, "hf_commit_sha": model.hf_commit_sha, "path": item.path, "quarantine_path": str(quarantined)},
                )

    def _verify_required_files(self, model: ModelSpec, cache_dir: Path, catalog: ModelCatalog) -> None:
        missing = []
        for item in model.required_files:
            path = cache_dir / item.path
            if not path.exists():
                missing.append(item.path)
            elif sha256_file(path) != item.sha256:
                quarantined = quarantine_file(self.mib_home, model, path)
                raise ModelCacheError(
                    "MODEL_CACHE_HASH_MISMATCH",
                    "Cached model file hash does not match the strict catalog.",
                    details={"model_id": model.id, "hf_commit_sha": model.hf_commit_sha, "path": item.path, "quarantine_path": str(quarantined)},
                )
        if missing:
            raise ModelCacheError(
                "MODEL_CACHE_MISS_OFFLINE",
                "Model cache is missing required files.",
                details={"model_id": model.id, "hf_commit_sha": model.hf_commit_sha, "missing_files": missing, "catalog": str(catalog.path)},
            )

    def _download_required_file(self, model: ModelSpec, item: ModelFile, cache_dir: Path, *, purpose: str) -> None:
        if self.downloader is None:
            raise AssertionError("downloader is required when files are missing")
        destination = cache_dir / item.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_name(destination.name + f".{os.getpid()}.tmp")
        if tmp.exists():
            tmp.unlink()
        self.downloader.download_file(model_id=model.id, revision=model.hf_commit_sha, path=item.path, destination=tmp)
        if not tmp.exists():
            raise ModelCacheError(
                "MODEL_CACHE_DOWNLOAD_FAILED",
                "Downloader did not create the requested model file.",
                details={"model_id": model.id, "hf_commit_sha": model.hf_commit_sha, "path": item.path, "purpose": purpose},
            )
        if sha256_file(tmp) != item.sha256:
            quarantined = quarantine_file(self.mib_home, model, tmp)
            raise ModelCacheError(
                "MODEL_CACHE_HASH_MISMATCH",
                "Downloaded model file hash does not match the strict catalog.",
                details={"model_id": model.id, "hf_commit_sha": model.hf_commit_sha, "path": item.path, "quarantine_path": str(quarantined)},
            )
        os.replace(tmp, destination)


def ensure_model(
    base_model: str,
    backend: str,
    purpose: str,
    *,
    mib_home: Path,
    catalog_path: Path | None = None,
    downloader: ModelDownloader | None = None,
    offline: bool | None = None,
) -> ModelCacheResult:
    return ModelCacheService(mib_home, catalog_path=catalog_path, downloader=downloader, offline=offline).ensure_model(
        base_model,
        backend,
        purpose,
    )


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def quarantine_file(mib_home: Path, model: ModelSpec, path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    quarantine_dir = mib_home / "model_cache" / "quarantine" / timestamp / model.cache_subdir
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    target = quarantine_dir / path.name
    shutil.move(str(path), target)
    return target


def env_offline() -> bool:
    return os.environ.get("MIB_OFFLINE") == "1"


def auth_headers() -> dict[str, str]:
    headers = {"User-Agent": "mib-studio-model-cache/0"}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
