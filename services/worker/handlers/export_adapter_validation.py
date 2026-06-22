from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from services.shared.db.models import ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text


ADAPTER_PATHS = {
    "lora_adapter": ["adapter/adapter.safetensors", "adapter/adapter_config.json"],
    "mlx_lora_adapter": ["adapter/adapters.npz", "adapter/adapter_config.json"],
}


class ExportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def adapter_required_paths(adapter_format: str) -> list[str]:
    return ADAPTER_PATHS.get(adapter_format, ADAPTER_PATHS["lora_adapter"])


def copy_adapter(*, model_run: ModelRun, contract: dict[str, Any], root: Path) -> None:
    source = Path(str(model_run.adapter_path))
    adapter_format = str(contract["adapter"]["format"])
    expected = adapter_required_paths(adapter_format)
    backend_format = "mlx_lora_adapter" if model_run.backend == "mlx" else "lora_adapter"
    if adapter_format != backend_format:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "AgentContract adapter format does not match ModelRun backend.")
    source_files: dict[str, Path] = {}
    for relative in expected:
        src = source / Path(relative).name
        if not src.is_file():
            raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", f"Missing adapter file: {relative}")
        source_files[relative] = src
    validate_adapter_files(adapter_format=adapter_format, source_files=source_files)
    validate_adapter_lineage(model_run=model_run, adapter_dir=source)
    for relative, src in source_files.items():
        _copy(src, root / relative)


def validate_adapter_files(*, adapter_format: str, source_files: dict[str, Path]) -> None:
    _validate_adapter_config(source_files["adapter/adapter_config.json"], adapter_format)
    if adapter_format == "mlx_lora_adapter":
        _validate_mlx_npz(source_files["adapter/adapters.npz"])
        return
    _validate_safetensors(source_files["adapter/adapter.safetensors"])


def validate_adapter_lineage(*, model_run: ModelRun, adapter_dir: Path) -> None:
    if not model_run.adapter_sha256 or not model_run.artifact_manifest_sha256:
        raise ExportError("MODEL_RUN_NOT_EXPORTABLE", "ModelRun adapter artifact hashes are missing.")
    manifest_path = adapter_dir.parent / "manifest.json"
    if not manifest_path.is_file():
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact manifest is missing.")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    if sha256_text(manifest_text) != model_run.artifact_manifest_sha256:
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact manifest hash mismatch.")
    try:
        manifest = json.loads(manifest_text)
    except Exception as exc:
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact manifest is invalid JSON.") from exc
    if not isinstance(manifest, dict):
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact manifest is invalid.")
    current_rows = _adapter_file_rows(adapter_dir)
    current_sha = sha256_text(canonical_json(current_rows))
    if current_sha != model_run.adapter_sha256 or manifest.get("adapter_sha256") != current_sha:
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact hash mismatch.")
    if manifest.get("files") != current_rows:
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact file manifest mismatch.")


def _validate_adapter_config(path: Path, adapter_format: str) -> None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "Invalid adapter_config.json: expected JSON object.") from exc
    if not isinstance(raw, dict):
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "Invalid adapter_config.json: expected JSON object.")
    declared_format = raw.get("format")
    if declared_format is not None and declared_format != adapter_format:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "adapter_config.json format mismatch.")
    if adapter_format == "lora_adapter":
        peft_type = raw.get("peft_type")
        if peft_type is not None and str(peft_type).upper() != "LORA":
            raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "adapter_config.json peft_type mismatch.")
        if declared_format is None and peft_type is None:
            raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "adapter_config.json must declare format or peft_type.")
        return
    if declared_format != adapter_format:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", "adapter_config.json format mismatch.")


def _validate_safetensors(path: Path) -> None:
    try:
        from safetensors import safe_open

        with safe_open(path, framework="numpy") as handle:
            keys = list(handle.keys())
            if not keys:
                raise ValueError("no tensors")
            if not any(getattr(handle.get_tensor(key), "size", 0) > 0 for key in keys):
                raise ValueError("no non-empty tensors")
    except Exception as exc:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", f"Invalid adapter file: {path.name}.") from exc


def _validate_mlx_npz(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".npy")]
            if not names:
                raise ValueError("no npy arrays")
    except Exception as exc:
        raise ExportError("EXPORT_ADAPTER_FORMAT_MISMATCH", f"Invalid adapter file: {path.name}.") from exc


def _adapter_file_rows(adapter_dir: Path) -> list[dict[str, Any]]:
    run_dir = adapter_dir.parent
    rows = []
    for path in sorted(item for item in adapter_dir.rglob("*") if item.is_file()):
        rows.append({"path": str(path.relative_to(run_dir)), "sha256": _sha256_file(path), "size_bytes": path.stat().st_size})
    if not rows:
        raise ExportError("EXPORT_ADAPTER_LINEAGE_MISMATCH", "Adapter artifact directory is empty.")
    return rows


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
