from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prepare = load_module("scripts/prepare_strict_model_cache.py", "prepare_strict_model_cache")


MODEL_ID = "test/model"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
WEIGHT_BYTES = b"tiny deterministic safetensors bytes"


class RecordingDownloader:
    def __init__(self, content: bytes = WEIGHT_BYTES) -> None:
        self.content = content
        self.calls: list[tuple[str, str, str]] = []

    def download_file(self, *, model_id: str, revision: str, path: str, destination: Path) -> None:
        self.calls.append((model_id, revision, path))
        destination.write_bytes(self.content)


def args_for(tmp_path: Path, *, allow_download: bool = False, model_cache_dir: Path | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        base_model=MODEL_ID,
        backend="cuda",
        model_cache_dir=str(model_cache_dir or tmp_path / "mib-home" / "model_cache"),
        purpose="external_cuda_training",
        catalog=str(write_catalog(tmp_path)),
        allow_download=allow_download,
        no_download=not allow_download,
        expected_status=None,
        json_output=str(tmp_path / "strict_model_cache_preparation.json"),
    )


def test_no_download_missing_cache_reports_not_ready(tmp_path: Path) -> None:
    report = prepare.build_report(args_for(tmp_path))

    assert report["status"] == prepare.NOT_READY_STATUS
    assert report["cache_ready"] is False
    assert report["download_allowed"] is False
    assert report["release_claimed_go"] is False
    assert report["m6_rc_claimed_go"] is False
    assert report["missing_files"] == ["model.safetensors"]
    assert report["error"]["code"] == "MODEL_CACHE_MISS_OFFLINE"
    assert "presets/model_catalog.yaml" in report["operator_next_actions"][0]
    assert "--allow-download" in report["operator_next_actions"][1]


def test_existing_strict_cache_reports_ready_without_download(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    cache_file = Path(args.model_cache_dir) / f"test__model@{COMMIT}" / "model.safetensors"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(WEIGHT_BYTES)
    downloader = RecordingDownloader()

    report = prepare.build_report(args, downloader=downloader)

    assert report["status"] == prepare.READY_STATUS
    assert report["cache_ready"] is True
    assert report["download_allowed"] is False
    assert report["downloaded_files"] == []
    assert report["missing_files"] == []
    assert report["model"]["cache_dir"] == str(cache_file.parent)
    assert report["required_files"][0]["present"] is True
    assert downloader.calls == []


def test_allow_download_fetches_pinned_missing_file(tmp_path: Path) -> None:
    downloader = RecordingDownloader()
    args = args_for(tmp_path, allow_download=True)

    report = prepare.build_report(args, downloader=downloader)

    assert report["status"] == prepare.READY_STATUS
    assert report["download_allowed"] is True
    assert report["downloaded_files"] == ["model.safetensors"]
    assert downloader.calls == [(MODEL_ID, COMMIT, "model.safetensors")]
    cache_file = Path(args.model_cache_dir) / f"test__model@{COMMIT}" / "model.safetensors"
    assert cache_file.read_bytes() == WEIGHT_BYTES


def test_rejects_model_cache_dir_that_does_not_point_to_model_cache(tmp_path: Path) -> None:
    report = prepare.build_report(args_for(tmp_path, model_cache_dir=tmp_path / "cache"))

    assert report["status"] == prepare.NOT_READY_STATUS
    assert report["error"]["code"] == "ValueError"
    assert "--model-cache-dir must point to the model_cache directory" in report["error"]["message"]


def write_catalog(tmp_path: Path) -> Path:
    catalog_path = tmp_path / "model_catalog.yaml"
    digest = hashlib.sha256(WEIGHT_BYTES).hexdigest()
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
  hf_commit_sha: {COMMIT}
  files:
  - path: model.safetensors
    sha256: {digest}
    size_bytes: {len(WEIGHT_BYTES)}
    required: true
""".lstrip(),
        encoding="utf-8",
    )
    return catalog_path
