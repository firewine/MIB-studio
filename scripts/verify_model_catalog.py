#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # Day-0 --skip-install verification runs before requirements-dev.
    yaml = None


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def is_git_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def is_weight_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name == "model.safetensors"
        or (name.startswith("model-") and name.endswith(".safetensors"))
        or name == "pytorch_model.bin"
        or (name.startswith("pytorch_model-") and name.endswith(".bin"))
    )


EXPECTED_MODELS: dict[str, dict[str, object]] = {
    "google/gemma-2b-it": {
        "license": "Gemma Terms of Use",
        "context_length": 8192,
        "train_seq_len": 1024,
        "chat_template": "tokenizer.apply_chat_template",
        "system_role": "unsupported_prepend_to_user",
        "allowed_backends": ["cuda", "mlx"],
        "lora_target": ["all"],
        "required_files": {
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "model-00001-of-00002.safetensors",
            "model-00002-of-00002.safetensors",
        },
    },
    "microsoft/Phi-3.5-mini-instruct": {
        "license": "MIT",
        "context_length": 131072,
        "train_seq_len": 1024,
        "chat_template": "tokenizer.apply_chat_template",
        "system_role": "supported",
        "allowed_backends": ["cuda", "mlx"],
        "lora_target": ["all"],
        "required_files": {
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "model-00001-of-00002.safetensors",
            "model-00002-of-00002.safetensors",
        },
    },
}


def load_catalog(path: Path) -> dict:
    text = path.read_text()
    if yaml is not None:
        return yaml.safe_load(text) or {}

    models: list[dict[str, object]] = []
    current_model: dict[str, object] | None = None
    current_file: dict[str, object] | None = None
    current_list_key: str | None = None
    in_files = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "models:":
            continue
        if stripped.startswith("- id:"):
            current_model = {}
            models.append(current_model)
            current_file = None
            current_list_key = None
            in_files = False
            key, value = stripped[2:].split(":", 1)
            current_model[key.strip()] = parse_scalar(value.strip())
            continue
        if current_model is None:
            continue
        if stripped == "files:":
            current_model["files"] = []
            current_file = None
            current_list_key = None
            in_files = True
            continue
        if in_files and stripped.startswith("- ") and ":" in stripped[2:]:
            current_file = {}
            current_model.setdefault("files", []).append(current_file)  # type: ignore[union-attr]
            key, value = stripped[2:].split(":", 1)
            current_file[key.strip()] = parse_scalar(value.strip())
            continue
        if current_list_key and stripped.startswith("- "):
            current_model.setdefault(current_list_key, [])  # type: ignore[arg-type]
            current_model[current_list_key].append(parse_scalar(stripped[2:].strip()))  # type: ignore[index,union-attr]
            continue
        if in_files and current_file is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_file[key.strip()] = parse_scalar(value.strip())
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                current_model[key] = parse_scalar(value)
                current_list_key = None
                in_files = False
            else:
                current_model[key] = []
                current_list_key = key
                in_files = False
    return {"models": models}


def parse_scalar(value: str) -> object:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    return value


def placeholder_paths(value: object, path: str = "$") -> list[str]:
    if value == "M1_DAY0_FILL":
        return [path]
    if isinstance(value, dict):
        paths: list[str] = []
        for key, child in value.items():
            paths.extend(placeholder_paths(child, f"{path}.{key}"))
        return paths
    if isinstance(value, list):
        paths: list[str] = []
        for index, child in enumerate(value):
            paths.extend(placeholder_paths(child, f"{path}[{index}]"))
        return paths
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--cache-dir", default="models")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--allow-day0-placeholders", action="store_true")
    parser.add_argument("--json-output")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    data = load_catalog(catalog_path)
    errors: list[str] = []
    seen: set[str] = set()

    if not args.allow_day0_placeholders:
        for placeholder_path in placeholder_paths(data):
            errors.append(f"{placeholder_path}: M1_DAY0_FILL placeholder is not allowed in strict catalog")

    models = data.get("models", [])
    if not isinstance(models, list):
        errors.append("$.models must be a list")
        models = []
    actual_ids = {model.get("id") for model in models if isinstance(model, dict)}
    expected_ids = set(EXPECTED_MODELS)
    if actual_ids != expected_ids:
        errors.append(f"strict catalog model IDs must be exactly {sorted(expected_ids)}, got {sorted(str(x) for x in actual_ids)}")

    for idx, model in enumerate(models):
        if not isinstance(model, dict):
            errors.append(f"models[{idx}] must be object")
            continue
        model_id = model.get("id")
        if not model_id or model_id in seen:
            errors.append(f"models[{idx}].id missing or duplicate")
        seen.add(model_id)
        expected = EXPECTED_MODELS.get(str(model_id))
        if expected:
            for key in ["license", "context_length", "train_seq_len", "chat_template", "system_role"]:
                if model.get(key) != expected[key]:
                    errors.append(f"{model_id}: {key} must be {expected[key]!r}")
            for key in ["allowed_backends", "lora_target"]:
                if list(model.get(key, [])) != expected[key]:
                    errors.append(f"{model_id}: {key} must be {expected[key]!r}")
        if model.get("trust_remote_code") is not False:
            errors.append(f"{model_id}: trust_remote_code must be false")
        commit = model.get("hf_commit_sha")
        if commit == "M1_DAY0_FILL" and args.allow_day0_placeholders:
            pass
        elif not is_git_sha(commit):
            errors.append(f"{model_id}: hf_commit_sha must be 40 lowercase git SHA after fill")
        required_weight_count = 0
        required_paths: set[str] = set()
        for file_idx, item in enumerate(model.get("files", [])):
            if not isinstance(item, dict):
                errors.append(f"{model_id}: files[{file_idx}] must be object")
                continue
            item_path = str(item.get("path", ""))
            if not item_path or item_path.startswith("/") or ".." in Path(item_path).parts:
                errors.append(f"{model_id}: files[{file_idx}].path must be a relative safe path")
            if item.get("required", False):
                required_paths.add(item_path)
            if item.get("required", False) and is_weight_file(item_path):
                required_weight_count += 1
            if not isinstance(item.get("size_bytes"), int) or item.get("size_bytes", 0) <= 0:
                errors.append(f"{model_id}: files[{file_idx}].size_bytes must be a positive integer")
            sha = item.get("sha256")
            if sha == "M1_DAY0_FILL" and args.allow_day0_placeholders:
                continue
            if sha == "M1_DAY0_FILL":
                errors.append(f"{model_id}: files[{file_idx}].sha256 still contains M1_DAY0_FILL")
                continue
            if not is_sha256(sha):
                errors.append(f"{model_id}: files[{file_idx}].sha256 must be 64 lowercase hex")
            local = Path(args.cache_dir) / str(model_id).replace("/", "__") / str(item.get("path", ""))
            if local.exists() and is_sha256(sha):
                actual = hashlib.sha256(local.read_bytes()).hexdigest()
                if actual != sha:
                    errors.append(f"{model_id}: cached file hash mismatch for {item.get('path')}")
        if not args.allow_day0_placeholders and required_weight_count == 0:
            errors.append(f"{model_id}: strict catalog must include at least one required model weight shard")
        if expected and not args.allow_day0_placeholders:
            missing = sorted(expected["required_files"] - required_paths)  # type: ignore[operator]
            if missing:
                errors.append(f"{model_id}: missing required strict files: {missing}")

    summary = {
        "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "model_count": len(data.get("models", [])),
        "errors": errors,
        "no_download": args.no_download,
    }
    text = json.dumps(summary, sort_keys=True)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(text + "\n")
    print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
