#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LOCKED_BASE_MODELS = {"google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"}
MIN_ADAPTER_BYTES = 1024


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def adapter_file_rows(adapter_dir: Path) -> list[dict[str, Any]]:
    run_dir = adapter_dir.parent
    rows = []
    for path in sorted(item for item in adapter_dir.rglob("*") if item.is_file()):
        rows.append({"path": str(path.relative_to(run_dir)), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    return rows


def load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{label}: invalid JSON object: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{label}: expected JSON object")
        return {}
    return data


def validate_config(config: dict[str, Any], *, expected_base_model: str | None, errors: list[str]) -> dict[str, Any]:
    peft_type = str(config.get("peft_type", "")).upper()
    if peft_type != "LORA":
        errors.append("adapter_config.json: peft_type must be LORA")
    base_model = config.get("base_model_name_or_path")
    if not isinstance(base_model, str) or base_model not in LOCKED_BASE_MODELS:
        errors.append(f"adapter_config.json: base_model_name_or_path must be one of {sorted(LOCKED_BASE_MODELS)}")
    if expected_base_model and base_model != expected_base_model:
        errors.append(f"adapter_config.json: base model {base_model!r} does not match expected {expected_base_model!r}")
    for key in ["r", "lora_alpha"]:
        if not isinstance(config.get(key), int) or int(config.get(key, 0)) <= 0:
            errors.append(f"adapter_config.json: {key} must be a positive integer")
    target_modules = config.get("target_modules")
    if not isinstance(target_modules, list) or not target_modules or not all(isinstance(item, str) and item for item in target_modules):
        errors.append("adapter_config.json: target_modules must be a non-empty string list")
    return {"base_model": base_model, "peft_type": peft_type}


def validate_safetensors(path: Path, errors: list[str]) -> dict[str, Any]:
    if path.stat().st_size < MIN_ADAPTER_BYTES:
        errors.append(f"adapter.safetensors: file is fixture-sized ({path.stat().st_size} bytes)")
    try:
        from safetensors import safe_open

        tensor_count = 0
        tensor_elements = 0
        lora_key_count = 0
        with safe_open(path, framework="numpy") as handle:
            for key in handle.keys():
                tensor_count += 1
                tensor = handle.get_tensor(key)
                size = int(getattr(tensor, "size", 0))
                tensor_elements += size
                if "lora" in key.lower():
                    lora_key_count += 1
        if tensor_count == 0:
            errors.append("adapter.safetensors: no tensors found")
        if tensor_elements <= 0:
            errors.append("adapter.safetensors: tensors have no elements")
        if lora_key_count == 0:
            errors.append("adapter.safetensors: no LoRA tensor keys found")
        return {"tensor_count": tensor_count, "tensor_elements": tensor_elements, "lora_key_count": lora_key_count}
    except Exception as exc:
        errors.append(f"adapter.safetensors: invalid safetensors file: {exc}")
        return {"tensor_count": 0, "tensor_elements": 0, "lora_key_count": 0}


def validate_manifest(path: Path, *, adapter_dir: Path, adapter_sha256: str, errors: list[str]) -> dict[str, Any]:
    manifest = load_json(path, errors, "manifest")
    if not manifest:
        return {}
    if manifest.get("adapter_format") not in {None, "lora_adapter"}:
        errors.append("manifest: adapter_format must be lora_adapter when present")
    if manifest.get("trainer_backend") not in {"llamafactory", "mlx_lm"}:
        errors.append("manifest: trainer_backend must be llamafactory or mlx_lm")
    if manifest.get("adapter_sha256") != adapter_sha256:
        errors.append("manifest: adapter_sha256 mismatch")
    rows = adapter_file_rows(adapter_dir)
    if manifest.get("files") != rows:
        errors.append("manifest: files do not match adapter directory")
    return manifest


def verify_adapter(*, adapter_dir: Path, expected_base_model: str | None = None, manifest_path: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    adapter_path = adapter_dir / "adapter.safetensors"
    config_path = adapter_dir / "adapter_config.json"
    if not adapter_dir.is_dir():
        errors.append(f"adapter directory does not exist: {adapter_dir}")
    if not adapter_path.is_file():
        errors.append("missing adapter.safetensors")
    if not config_path.is_file():
        errors.append("missing adapter_config.json")
    config = load_json(config_path, errors, "adapter_config.json") if config_path.is_file() else {}
    config_summary = validate_config(config, expected_base_model=expected_base_model, errors=errors) if config else {}
    tensor_summary = validate_safetensors(adapter_path, errors) if adapter_path.is_file() else {}
    rows = adapter_file_rows(adapter_dir) if adapter_dir.is_dir() else []
    adapter_sha = sha256_text(canonical_json(rows)) if rows else None
    manifest_summary = {}
    if manifest_path is not None:
        if not manifest_path.is_file():
            errors.append(f"manifest does not exist: {manifest_path}")
        elif adapter_sha is not None:
            manifest_summary = validate_manifest(manifest_path, adapter_dir=adapter_dir, adapter_sha256=adapter_sha, errors=errors)
    return {
        "schema_version": "mib_real_adapter_artifact_intake.v1",
        "status": "GO_REAL_ADAPTER_ARTIFACT_INTAKE" if not errors else "NOT_GO_REAL_ADAPTER_ARTIFACT_INTAKE",
        "adapter_dir": str(adapter_dir),
        "expected_base_model": expected_base_model,
        "adapter_sha256": adapter_sha,
        "artifact_manifest_sha256": sha256_file(manifest_path) if manifest_path and manifest_path.is_file() else None,
        "config": config_summary,
        "safetensors": tensor_summary,
        "manifest_present": manifest_path is not None and manifest_path.is_file(),
        "manifest": {"trainer_backend": manifest_summary.get("trainer_backend"), "adapter_format": manifest_summary.get("adapter_format")}
        if manifest_summary
        else {},
        "errors": errors,
    }


def write_self_test_adapter(root: Path) -> tuple[Path, Path]:
    import numpy as np
    from safetensors.numpy import save_file

    adapter_dir = root / "run" / "adapter"
    adapter_dir.mkdir(parents=True)
    save_file(
        {
            "base_model.model.layers.0.self_attn.q_proj.lora_A.weight": np.ones((64, 64), dtype=np.float32),
            "base_model.model.layers.0.self_attn.q_proj.lora_B.weight": np.ones((64, 64), dtype=np.float32),
        },
        adapter_dir / "adapter.safetensors",
    )
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps(
            {
                "base_model_name_or_path": "microsoft/Phi-3.5-mini-instruct",
                "lora_alpha": 16,
                "peft_type": "LORA",
                "r": 8,
                "target_modules": ["q_proj"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = adapter_file_rows(adapter_dir)
    adapter_sha = sha256_text(canonical_json(rows))
    manifest = {
        "adapter_format": "lora_adapter",
        "adapter_sha256": adapter_sha,
        "files": rows,
        "trainer_backend": "llamafactory",
    }
    manifest_path = adapter_dir.parent / "manifest.json"
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    return adapter_dir, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-dir")
    parser.add_argument("--base-model", choices=sorted(LOCKED_BASE_MODELS))
    parser.add_argument("--manifest")
    parser.add_argument("--json-output", default="artifacts/review/real_adapter_artifact_intake.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            adapter_dir, manifest_path = write_self_test_adapter(Path(tmpdir))
            report = verify_adapter(adapter_dir=adapter_dir, expected_base_model="microsoft/Phi-3.5-mini-instruct", manifest_path=manifest_path)
    else:
        if not args.adapter_dir:
            raise SystemExit("--adapter-dir is required unless --self-test is set")
        report = verify_adapter(
            adapter_dir=Path(args.adapter_dir),
            expected_base_model=args.base_model,
            manifest_path=Path(args.manifest) if args.manifest else None,
        )

    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "GO_REAL_ADAPTER_ARTIFACT_INTAKE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
