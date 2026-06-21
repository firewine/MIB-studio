from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from services.shared.model_catalog import ModelCatalogError, load_model_catalog
from services.worker.model_cache import ModelCacheError, ModelCacheService


MODEL_ID = "test/model"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
WEIGHT_BYTES = b"tiny deterministic safetensors bytes"


class RecordingDownloader:
    def __init__(self, content: bytes = WEIGHT_BYTES, delay: float = 0.0) -> None:
        self.content = content
        self.delay = delay
        self.calls: list[tuple[str, str, str]] = []

    def download_file(self, *, model_id: str, revision: str, path: str, destination: Path) -> None:
        self.calls.append((model_id, revision, path))
        if self.delay:
            time.sleep(self.delay)
        destination.write_bytes(self.content)


def test_strict_model_catalog_loads_repo_manifest() -> None:
    catalog = load_model_catalog()

    assert {model.id for model in catalog.models} == {
        "google/gemma-2b-it",
        "microsoft/Phi-3.5-mini-instruct",
    }
    assert all(model.trust_remote_code is False for model in catalog.models)
    assert all(model.required_files for model in catalog.models)


def test_strict_manifest_rejects_day0_placeholder(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path, hf_commit_sha="M1_DAY0_FILL")

    with pytest.raises(ModelCatalogError) as excinfo:
        load_model_catalog(catalog_path)

    assert any("M1_DAY0_FILL" in error for error in excinfo.value.errors)


def test_model_cache_hit_verifies_required_files_without_download(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path)
    mib_home = tmp_path / ".mib-home"
    cache_file = cache_file_path(mib_home)
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(WEIGHT_BYTES)
    downloader = RecordingDownloader()

    result = ModelCacheService(mib_home, catalog_path=catalog_path, downloader=downloader, offline=True).ensure_model(
        MODEL_ID,
        "cuda",
        "train",
    )

    assert result.cache_dir == cache_file.parent
    assert result.required_files == ("model.safetensors",)
    assert result.downloaded_files == ()
    assert downloader.calls == []


def test_model_cache_miss_downloads_with_pinned_commit(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path)
    mib_home = tmp_path / ".mib-home"
    downloader = RecordingDownloader()

    result = ModelCacheService(mib_home, catalog_path=catalog_path, downloader=downloader, offline=False).ensure_model(
        MODEL_ID,
        "mlx",
        "eval",
    )

    assert cache_file_path(mib_home).read_bytes() == WEIGHT_BYTES
    assert result.downloaded_files == ("model.safetensors",)
    assert downloader.calls == [(MODEL_ID, COMMIT, "model.safetensors")]


def test_model_cache_lock_prevents_duplicate_downloads(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path)
    mib_home = tmp_path / ".mib-home"
    downloader = RecordingDownloader(delay=0.1)
    service = ModelCacheService(mib_home, catalog_path=catalog_path, downloader=downloader, offline=False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.ensure_model(MODEL_ID, "cuda", "train"), range(2)))

    assert [result.cache_dir for result in results] == [cache_file_path(mib_home).parent] * 2
    assert downloader.calls == [(MODEL_ID, COMMIT, "model.safetensors")]


def test_model_cache_offline_miss_returns_missing_files(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path)
    mib_home = tmp_path / ".mib-home"

    with pytest.raises(ModelCacheError) as excinfo:
        ModelCacheService(mib_home, catalog_path=catalog_path, offline=True).ensure_model(MODEL_ID, "cuda", "train")

    assert excinfo.value.code == "MODEL_CACHE_MISS_OFFLINE"
    assert excinfo.value.status_code == 409
    assert excinfo.value.details == {
        "model_id": MODEL_ID,
        "hf_commit_sha": COMMIT,
        "missing_files": ["model.safetensors"],
    }


def test_model_cache_hash_mismatch_quarantines_bad_file(tmp_path: Path) -> None:
    catalog_path = write_catalog(tmp_path)
    mib_home = tmp_path / ".mib-home"
    cache_file = cache_file_path(mib_home)
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"corrupt")

    with pytest.raises(ModelCacheError) as excinfo:
        ModelCacheService(mib_home, catalog_path=catalog_path, offline=True).ensure_model(MODEL_ID, "cuda", "train")

    assert excinfo.value.code == "MODEL_CACHE_HASH_MISMATCH"
    assert not cache_file.exists()
    quarantine_path = Path(str(excinfo.value.details["quarantine_path"]))
    assert quarantine_path.exists()
    assert quarantine_path.read_bytes() == b"corrupt"
    assert mib_home / "model_cache" / "quarantine" in quarantine_path.parents


def write_catalog(tmp_path: Path, *, hf_commit_sha: str = COMMIT, sha256: str | None = None) -> Path:
    catalog_path = tmp_path / "model_catalog.yaml"
    digest = sha256 or hashlib.sha256(WEIGHT_BYTES).hexdigest()
    catalog_path.write_text(
        f"""
models:
- id: {MODEL_ID}
  license: Test License
  trust_remote_code: false
  context_length: 2048
  train_seq_len: 512
  chat_template: tokenizer.apply_chat_template
  system_role: supported
  allowed_backends:
  - cuda
  - mlx
  lora_target:
  - all
  hf_commit_sha: {hf_commit_sha}
  files:
  - path: model.safetensors
    sha256: {digest}
    size_bytes: {len(WEIGHT_BYTES)}
    required: true
""".lstrip(),
        encoding="utf-8",
    )
    return catalog_path


def cache_file_path(mib_home: Path) -> Path:
    return mib_home / "model_cache" / f"test__model@{COMMIT}" / "model.safetensors"
