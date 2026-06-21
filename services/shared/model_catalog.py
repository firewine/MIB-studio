from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_CATALOG_PATH = REPO_ROOT / "presets" / "model_catalog.yaml"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ModelCatalogError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class ModelFile:
    path: str
    sha256: str
    size_bytes: int
    required: bool


@dataclass(frozen=True)
class ModelSpec:
    id: str
    license: str
    trust_remote_code: bool
    context_length: int
    train_seq_len: int
    chat_template: str
    system_role: str
    allowed_backends: tuple[str, ...]
    lora_target: tuple[str, ...]
    hf_commit_sha: str
    files: tuple[ModelFile, ...]

    @property
    def cache_subdir(self) -> str:
        return sanitize_model_id(self.id) + "@" + self.hf_commit_sha

    @property
    def required_files(self) -> tuple[ModelFile, ...]:
        return tuple(item for item in self.files if item.required)


@dataclass(frozen=True)
class ModelCatalog:
    path: Path
    models: tuple[ModelSpec, ...]

    def get(self, model_id: str) -> ModelSpec:
        for model in self.models:
            if model.id == model_id:
                return model
        raise ModelCatalogError([f"{model_id}: model id is not present in strict catalog"])


def load_model_catalog(path: Path = DEFAULT_MODEL_CATALOG_PATH) -> ModelCatalog:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors = placeholder_errors(data)
    models_raw = data.get("models")
    if not isinstance(models_raw, list) or not models_raw:
        raise ModelCatalogError(["$.models must be a non-empty list"])

    models: list[ModelSpec] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(models_raw):
        if not isinstance(raw, dict):
            errors.append(f"models[{index}] must be an object")
            continue
        model = parse_model(raw, index, errors)
        if model is None:
            continue
        if model.id in seen_ids:
            errors.append(f"{model.id}: duplicate model id")
        seen_ids.add(model.id)
        models.append(model)

    if errors:
        raise ModelCatalogError(errors)
    return ModelCatalog(path=path, models=tuple(models))


def parse_model(raw: dict[str, Any], index: int, errors: list[str]) -> ModelSpec | None:
    model_id = require_str(raw, "id", f"models[{index}]", errors)
    hf_commit_sha = require_str(raw, "hf_commit_sha", str(model_id or f"models[{index}]"), errors)
    files_raw = raw.get("files")
    if not isinstance(files_raw, list) or not files_raw:
        errors.append(f"{model_id}: files must be a non-empty list")
        files_raw = []
    files = parse_files(str(model_id or f"models[{index}]"), files_raw, errors)

    if not model_id:
        return None
    if raw.get("trust_remote_code") is not False:
        errors.append(f"{model_id}: trust_remote_code must be false")
    if not hf_commit_sha or not GIT_SHA_RE.fullmatch(hf_commit_sha):
        errors.append(f"{model_id}: hf_commit_sha must be a pinned 40-hex git SHA")
        hf_commit_sha = "0" * 40
    if not any(item.required and is_weight_file(item.path) for item in files):
        errors.append(f"{model_id}: strict catalog must include at least one required model weight shard")

    return ModelSpec(
        id=model_id,
        license=require_str(raw, "license", model_id, errors) or "",
        trust_remote_code=bool(raw.get("trust_remote_code")),
        context_length=require_positive_int(raw, "context_length", model_id, errors),
        train_seq_len=require_positive_int(raw, "train_seq_len", model_id, errors),
        chat_template=require_str(raw, "chat_template", model_id, errors) or "",
        system_role=require_str(raw, "system_role", model_id, errors) or "",
        allowed_backends=tuple(require_str_list(raw, "allowed_backends", model_id, errors)),
        lora_target=tuple(require_str_list(raw, "lora_target", model_id, errors)),
        hf_commit_sha=hf_commit_sha,
        files=tuple(files),
    )


def parse_files(model_id: str, files_raw: list[Any], errors: list[str]) -> list[ModelFile]:
    files: list[ModelFile] = []
    seen_paths: set[str] = set()
    for index, raw_file in enumerate(files_raw):
        if not isinstance(raw_file, dict):
            errors.append(f"{model_id}: files[{index}] must be an object")
            continue
        file_path = require_str(raw_file, "path", f"{model_id}: files[{index}]", errors)
        sha256 = require_str(raw_file, "sha256", f"{model_id}: files[{index}]", errors)
        size_bytes = require_positive_int(raw_file, "size_bytes", f"{model_id}: files[{index}]", errors)
        required = raw_file.get("required")
        if type(required) is not bool:
            errors.append(f"{model_id}: files[{index}].required must be boolean")
            required = False
        if file_path:
            if file_path in seen_paths:
                errors.append(f"{model_id}: duplicate file path {file_path}")
            seen_paths.add(file_path)
            if not is_safe_relative_path(file_path):
                errors.append(f"{model_id}: files[{index}].path must be a safe relative path")
        if not sha256 or not SHA256_RE.fullmatch(sha256):
            errors.append(f"{model_id}: files[{index}].sha256 must be 64 lowercase hex")
            sha256 = "0" * 64
        files.append(ModelFile(path=file_path or "", sha256=sha256, size_bytes=size_bytes, required=bool(required)))
    return files


def require_str(raw: dict[str, Any], key: str, owner: str, errors: list[str]) -> str | None:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{owner}: {key} must be a non-empty string")
        return None
    return value


def require_positive_int(raw: dict[str, Any], key: str, owner: str, errors: list[str]) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or value <= 0:
        errors.append(f"{owner}: {key} must be a positive integer")
        return 0
    return value


def require_str_list(raw: dict[str, Any], key: str, owner: str, errors: list[str]) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{owner}: {key} must be a non-empty string list")
        return []
    return list(value)


def placeholder_errors(value: Any, path: str = "$") -> list[str]:
    if value == "M1_DAY0_FILL":
        return [f"{path}: M1_DAY0_FILL placeholder is not allowed in strict catalog"]
    if isinstance(value, dict):
        errors: list[str] = []
        for key, child in value.items():
            errors.extend(placeholder_errors(child, f"{path}.{key}"))
        return errors
    if isinstance(value, list):
        errors = []
        for index, child in enumerate(value):
            errors.extend(placeholder_errors(child, f"{path}[{index}]"))
        return errors
    return []


def sanitize_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def is_weight_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name == "model.safetensors"
        or (name.startswith("model-") and name.endswith(".safetensors"))
        or name == "pytorch_model.bin"
        or (name.startswith("pytorch_model-") and name.endswith(".bin"))
    )


def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts
