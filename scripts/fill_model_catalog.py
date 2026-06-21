#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # Day-0 network fill may run before requirements are installed.
    yaml = None


HF_TOKEN_ENV_NAMES = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN")


def unquote_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv_tokens(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in HF_TOKEN_ENV_NAMES or os.environ.get(key):
            continue
        value = unquote_env_value(value)
        if value:
            os.environ[key] = value


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


def dump_catalog(data: dict) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)

    lines = ["models:"]
    for model in data.get("models", []):
        lines.append(f"  - id: {model['id']}")
        for key in [
            "license",
            "trust_remote_code",
            "context_length",
            "train_seq_len",
            "chat_template",
            "system_role",
            "allowed_backends",
            "lora_target",
            "hf_commit_sha",
        ]:
            value = model.get(key)
            if isinstance(value, bool):
                value_text = "true" if value else "false"
            elif isinstance(value, list):
                value_text = "[" + ", ".join(str(item) for item in value) + "]"
            else:
                value_text = str(value)
            lines.append(f"    {key}: {value_text}")
        lines.append("    files:")
        for item in model.get("files", []):
            lines.append(f"      - path: {item['path']}")
            lines.append(f"        sha256: {item['sha256']}")
            lines.append(f"        size_bytes: {item['size_bytes']}")
            lines.append(f"        required: {'true' if item.get('required') else 'false'}")
    return "\n".join(lines) + "\n"


def hf_token() -> str | None:
    load_dotenv_tokens()
    return next((os.environ.get(name) for name in HF_TOKEN_ENV_NAMES if os.environ.get(name)), None)


def open_hf_url(url: str, timeout: int):
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "mib-studio-model-catalog-fill/0.1")
    token = hf_token()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(request, timeout=timeout)


def hf_access_denied_message(repo_id: str, status_code: int) -> str:
    if hf_token():
        token_state = (
            "an HF token is present, but the token account may lack accepted terms, "
            "gated repo access, or fine-grained read permission"
        )
    else:
        token_state = "no HF token env var is set"
    return (
        f"HF access denied ({status_code}); {token_state}. "
        "Set HF_TOKEN, HUGGING_FACE_HUB_TOKEN, or HUGGINGFACE_TOKEN for the same HF account that accepted "
        "the model terms, then rerun. If terms were accepted after token creation, retry after propagation "
        "or create a fresh read token."
    )


def fetch_model_info(repo_id: str) -> dict:
    quoted = urllib.parse.quote(repo_id, safe="/")
    url = f"https://huggingface.co/api/models/{quoted}?blobs=true"
    try:
        with open_hf_url(url, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError(hf_access_denied_message(repo_id, exc.code)) from exc
        raise


def fetch_file_bytes(repo_id: str, commit: str, path: str) -> bytes:
    quoted_repo = urllib.parse.quote(repo_id, safe="/")
    quoted_path = urllib.parse.quote(path, safe="/")
    url = f"https://huggingface.co/{quoted_repo}/resolve/{commit}/{quoted_path}"
    try:
        with open_hf_url(url, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError(f"{path}: {hf_access_denied_message(repo_id, exc.code)}") from exc
        raise


def sibling_map(info: dict) -> dict[str, dict]:
    return {item.get("rfilename"): item for item in info.get("siblings", []) if item.get("rfilename")}


def is_weight_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name == "model.safetensors"
        or (name.startswith("model-") and name.endswith(".safetensors"))
        or name == "pytorch_model.bin"
        or (name.startswith("pytorch_model-") and name.endswith(".bin"))
    )


def apply_file_metadata(repo_id: str, commit: str, item: dict, siblings: dict[str, dict], errors: list[str]) -> None:
    path = item.get("path")
    meta = siblings.get(path)
    if not meta:
        if item.get("required", False):
            errors.append(f"{repo_id}: required file missing from HF metadata: {path}")
        return
    lfs = meta.get("lfs") or {}
    sha256 = lfs.get("sha256")
    size = meta.get("size") or lfs.get("size")
    if not sha256:
        if is_weight_file(str(path)):
            if item.get("required", False):
                errors.append(f"{repo_id}: required weight file has no lfs sha256 metadata: {path}")
            return
        try:
            data = fetch_file_bytes(repo_id, commit, str(path))
        except Exception as exc:
            if item.get("required", False):
                errors.append(f"{repo_id}: cannot download required metadata file for sha256: {path}: {exc}")
            return
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)
    if sha256:
        item["sha256"] = sha256
    if isinstance(size, int):
        item["size_bytes"] = size


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    data = load_catalog(catalog_path)
    wanted = set(args.models)
    errors: list[str] = []

    for model in data.get("models", []):
        repo_id = model.get("id")
        if repo_id not in wanted:
            continue
        try:
            info = fetch_model_info(repo_id)
        except Exception as exc:
            errors.append(f"{repo_id}: {exc}")
            continue
        commit = info.get("sha")
        if not isinstance(commit, str) or len(commit) != 40:
            errors.append(f"{repo_id}: missing 40-char HF commit sha")
            continue
        model["hf_commit_sha"] = commit
        siblings = sibling_map(info)
        existing = {item.get("path") for item in model.get("files", [])}
        for path in sorted(p for p in siblings if is_weight_file(p)):
            if path not in existing:
                model.setdefault("files", []).append({
                    "path": path,
                    "sha256": "M1_DAY0_FILL",
                    "size_bytes": 0,
                    "required": True,
                })
        weight_count = 0
        for item in model.get("files", []):
            path = str(item.get("path", ""))
            if item.get("required", False) and is_weight_file(path):
                weight_count += 1
            apply_file_metadata(repo_id, commit, item, siblings, errors)
        if weight_count == 0:
            errors.append(f"{repo_id}: no required model weight shard found")

    if errors:
        raise SystemExit("\n".join(errors))

    catalog_path.write_text(dump_catalog(data))
    print(f"updated {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
