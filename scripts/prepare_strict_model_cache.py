#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from services.shared.model_catalog import ModelCatalogError, ModelSpec, load_model_catalog
from services.worker.model_cache import ModelCacheError, ModelDownloader, ModelCacheService


SCHEMA_VERSION = "mib_strict_model_cache_preparation.v1"
READY_STATUS = "READY_STRICT_MODEL_CACHE"
NOT_READY_STATUS = "NOT_READY_STRICT_MODEL_CACHE"
LOCKED_BASE_MODELS = {"google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def mib_home_from_model_cache_dir(model_cache_dir: Path) -> Path:
    if model_cache_dir.name != "model_cache":
        raise ValueError("--model-cache-dir must point to the model_cache directory, for example /tmp/mib-strict-model-cache-phi/model_cache")
    return model_cache_dir.parent


def required_file_rows(model: ModelSpec, model_cache_dir: Path) -> list[dict[str, Any]]:
    cache_root = model_cache_dir / model.cache_subdir
    rows: list[dict[str, Any]] = []
    for item in model.required_files:
        path = cache_root / item.path
        rows.append(
            {
                "path": item.path,
                "cache_path": str(path),
                "present": path.is_file(),
                "expected_sha256": item.sha256,
                "expected_size_bytes": item.size_bytes,
                "actual_size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return rows


def build_report(args: argparse.Namespace, *, downloader: ModelDownloader | None = None) -> dict[str, Any]:
    model_cache_dir = Path(args.model_cache_dir)
    allow_download = bool(args.allow_download)
    try:
        mib_home = mib_home_from_model_cache_dir(model_cache_dir)
        catalog_path = Path(args.catalog) if args.catalog else None
        catalog = load_model_catalog(catalog_path) if catalog_path else load_model_catalog()
        model = catalog.get(args.base_model)
        service = ModelCacheService(
            mib_home,
            catalog_path=catalog_path,
            downloader=downloader,
            offline=not allow_download,
        )
        result = service.ensure_model(args.base_model, args.backend, args.purpose)
        required_rows = required_file_rows(model, model_cache_dir)
        return {
            "schema_version": SCHEMA_VERSION,
            "date": now_utc(),
            "gate": "mib-studio-strict-model-cache-preparation",
            "status": READY_STATUS,
            "release_claimed_go": False,
            "m6_rc_claimed_go": False,
            "cache_ready": True,
            "download_allowed": allow_download,
            "inputs": {
                "base_model": args.base_model,
                "backend": args.backend,
                "purpose": args.purpose,
                "model_cache_dir": str(model_cache_dir),
                "catalog": str(catalog.path),
            },
            "model": {
                "id": result.model_id,
                "hf_commit_sha": result.hf_commit_sha,
                "cache_subdir": model.cache_subdir,
                "cache_dir": str(result.cache_dir),
                "required_file_count": len(result.required_files),
            },
            "required_files": required_rows,
            "downloaded_files": list(result.downloaded_files),
            "missing_files": [],
            "error": None,
            "operator_next_actions": [],
        }
    except (ModelCacheError, ModelCatalogError, ValueError) as exc:
        details = getattr(exc, "details", {})
        model: ModelSpec | None = None
        catalog_display = str(Path(args.catalog)) if args.catalog else str(REPO_ROOT / "presets" / "model_catalog.yaml")
        try:
            catalog_path = Path(args.catalog) if args.catalog else None
            catalog = load_model_catalog(catalog_path) if catalog_path else load_model_catalog()
            model = catalog.get(args.base_model)
            catalog_display = str(catalog.path)
        except Exception:
            model = None
        missing_files = details.get("missing_files", []) if isinstance(details, dict) else []
        if not isinstance(missing_files, list):
            missing_files = []
        error_code = getattr(exc, "code", type(exc).__name__)
        error_message = getattr(exc, "message", str(exc))
        return {
            "schema_version": SCHEMA_VERSION,
            "date": now_utc(),
            "gate": "mib-studio-strict-model-cache-preparation",
            "status": NOT_READY_STATUS,
            "release_claimed_go": False,
            "m6_rc_claimed_go": False,
            "cache_ready": False,
            "download_allowed": allow_download,
            "inputs": {
                "base_model": args.base_model,
                "backend": args.backend,
                "purpose": args.purpose,
                "model_cache_dir": str(model_cache_dir),
                "catalog": catalog_display,
            },
            "model": {
                "id": model.id if model else args.base_model,
                "hf_commit_sha": model.hf_commit_sha if model else None,
                "cache_subdir": model.cache_subdir if model else None,
                "cache_dir": str(model_cache_dir / model.cache_subdir) if model else None,
                "required_file_count": len(model.required_files) if model else 0,
            },
            "required_files": required_file_rows(model, model_cache_dir) if model else [],
            "downloaded_files": [],
            "missing_files": [str(item) for item in missing_files],
            "error": {
                "code": error_code,
                "message": error_message,
                "details": details,
            },
            "operator_next_actions": [
                "Populate the strict model cache with the required pinned files from presets/model_catalog.yaml.",
                "Rerun this command with --allow-download on a trusted networked host if the cache is missing.",
                "Do not commit model weights or copied model cache files to this repository.",
            ],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or verify the strict base-model cache for external CUDA training.")
    parser.add_argument("--base-model", choices=sorted(LOCKED_BASE_MODELS), required=True)
    parser.add_argument("--backend", choices=["cuda", "mlx"], default="cuda")
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--purpose", default="external_cuda_training")
    parser.add_argument("--catalog", help="Optional model catalog path. Defaults to presets/model_catalog.yaml.")
    parser.add_argument("--allow-download", action="store_true", help="Allow downloading missing pinned files from Hugging Face.")
    parser.add_argument("--no-download", action="store_true", help="Explicitly keep the default offline/no-download behavior.")
    parser.add_argument("--expected-status", choices=[READY_STATUS, NOT_READY_STATUS])
    parser.add_argument("--json-output", default="artifacts/review/strict_model_cache_preparation.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_json(args.json_output, report)
    print(
        json.dumps(
            {
                "json_output": args.json_output,
                "status": report["status"],
                "cache_ready": report["cache_ready"],
                "download_allowed": report["download_allowed"],
            },
            sort_keys=True,
        )
    )
    if args.expected_status:
        return 0 if report["status"] == args.expected_status else 1
    return 0 if report["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
