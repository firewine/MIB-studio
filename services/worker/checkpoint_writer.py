from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.shared.db.models import Checkpoint
from services.shared.db.repositories.dataset_store import canonical_json
from services.shared.db.repositories.training_store import CheckpointRecordInput, TrainingStore


@dataclass(frozen=True)
class CheckpointWriteInput:
    job_id: str
    model_run_id: str
    dataset_id: str
    dataset_version: int
    training_config_hash: str
    step: int
    adapter_filename: str
    adapter_bytes: bytes
    trainer_backend: str
    loss: float
    optimizer_state_bytes: bytes | None
    rng_state_json: dict[str, Any] | None
    trainer_state: dict[str, Any]
    created_at: str


def write_checkpoint(session: Session, run_dir: Path, payload: CheckpointWriteInput) -> Checkpoint:
    checkpoint_root = run_dir / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    final_dir = checkpoint_root / str(payload.step)
    temp_dir = checkpoint_root / f".{payload.step}.tmp-{os.getpid()}"
    if final_dir.exists():
        raise FileExistsError(f"checkpoint already exists for step {payload.step}")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    try:
        adapter_path = temp_dir / payload.adapter_filename
        _write_bytes(adapter_path, payload.adapter_bytes)
        adapter_sha256 = _sha256_bytes(payload.adapter_bytes)

        optimizer_present = payload.optimizer_state_bytes is not None
        rng_present = payload.rng_state_json is not None
        if payload.optimizer_state_bytes is not None:
            optimizer_name = "optimizer.npz" if payload.adapter_filename.endswith(".npz") else "optimizer.pt"
            _write_bytes(temp_dir / optimizer_name, payload.optimizer_state_bytes)
        if payload.rng_state_json is not None:
            _write_text(temp_dir / "rng_state.json", canonical_json(payload.rng_state_json) + "\n")
        _write_text(temp_dir / "trainer_state.json", canonical_json(payload.trainer_state) + "\n")

        manifest = {
            "schema_version": "checkpoint_manifest.v1",
            "dataset_id": payload.dataset_id,
            "dataset_version": payload.dataset_version,
            "training_config_hash": payload.training_config_hash,
            "weights_sha256": adapter_sha256,
            "step": payload.step,
        }
        _write_text(temp_dir / "manifest.json", canonical_json(manifest) + "\n")
        _fsync_directory(temp_dir)
        os.replace(temp_dir, final_dir)
        _fsync_directory(checkpoint_root)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    metrics = {
        "step": payload.step,
        "loss": payload.loss,
        "adapter_sha256_at_step": adapter_sha256,
        "optimizer_state_present": optimizer_present,
        "rng_state_present": rng_present,
        "trainer_backend": payload.trainer_backend,
    }
    return TrainingStore(session).record_checkpoint(
        CheckpointRecordInput(
            job_id=payload.job_id,
            model_run_id=payload.model_run_id,
            step=payload.step,
            path=str(final_dir),
            metrics=metrics,
            dataset_id=payload.dataset_id,
            dataset_version=payload.dataset_version,
            training_config_hash=payload.training_config_hash,
            weights_sha256=adapter_sha256,
            created_at=payload.created_at,
        )
    )


def _write_bytes(path: Path, value: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _write_text(path: Path, value: str) -> None:
    _write_bytes(path, value.encode("utf-8"))


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
