from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.shared.db.models import Dataset, Job, ModelRun
from services.shared.db.repositories.training_store import TrainingStore
from services.worker.runtime.mlx_lm import (
    MlxLmRunner,
    MlxTrainerEvent,
    MlxTrainerJobInput,
    SubprocessMlxLmRunner,
    write_mlx_artifacts,
    write_mlx_manifest,
)


class TrainMlxError(Exception):
    def __init__(self, code: str, message: str, *, error_class: str = "UNKNOWN") -> None:
        self.code = code
        self.message = message
        self.error_class = error_class
        super().__init__(message)


def run_train_mlx_job(
    session: Session,
    mib_home: Path,
    job_id: str,
    *,
    runner: MlxLmRunner | None = None,
) -> str:
    store = TrainingStore(session)
    job = session.get(Job, job_id)
    if job is None:
        raise TrainMlxError("JOB_NOT_FOUND", "Job does not exist.", error_class="ARTIFACT_MISSING")
    model_run = _model_run_for_job(session, job)
    dataset = session.get(Dataset, model_run.dataset_id)
    if dataset is None:
        raise TrainMlxError("DATASET_NOT_FOUND", "Training dataset does not exist.", error_class="ARTIFACT_MISSING")
    _validate_mlx_job(job, model_run)

    try:
        store.mark_running(job=job, model_run=model_run, ts=utc_now())
        run_dir = mib_home / "projects" / model_run.project_id / "runs" / model_run.id
        trainer_input = _trainer_input(job, model_run, dataset, run_dir)
        model_cache_path = mib_home / "model_cache" / json.loads(model_run.config_json)["model_cache_subdir"]
        config_path = write_mlx_artifacts(trainer_input, model_cache_path=model_cache_path)
        for event in (runner or SubprocessMlxLmRunner()).run(config_path, run_dir=run_dir):
            _record_trainer_event(store, job, model_run, event)
        manifest_path, adapter_sha256, manifest_sha256 = write_mlx_manifest(run_dir)
        store.mark_succeeded(
            job=job,
            model_run=model_run,
            adapter_path=str(manifest_path.parent / "adapter"),
            adapter_sha256=adapter_sha256,
            artifact_manifest_sha256=manifest_sha256,
            ts=utc_now(),
        )
        return model_run.id
    except TrainMlxError as exc:
        store.mark_failed(job=job, model_run=model_run, error_class=exc.error_class, error_message=exc.message, ts=utc_now())
        raise
    except Exception as exc:
        message = sanitize_error(str(exc) or exc.__class__.__name__)
        store.mark_failed(job=job, model_run=model_run, error_class="UNKNOWN", error_message=message, ts=utc_now())
        raise TrainMlxError("MLX_TRAIN_FAILED", message) from exc


def _model_run_for_job(session: Session, job: Job) -> ModelRun:
    params = json.loads(job.params_json)
    model_run_id = str(params.get("model_run_id") or "")
    model_run = session.get(ModelRun, model_run_id)
    if model_run is None:
        raise TrainMlxError("MODEL_RUN_NOT_FOUND", "ModelRun does not exist for train job.", error_class="ARTIFACT_MISSING")
    return model_run


def _validate_mlx_job(job: Job, model_run: ModelRun) -> None:
    if job.type != "train":
        raise TrainMlxError("JOB_TYPE_UNSUPPORTED", "Job is not a train job.")
    if model_run.backend != "mlx" or model_run.method != "mlx_lora":
        raise TrainMlxError(
            "TRAIN_BACKEND_UNSUPPORTED",
            "MLX wrapper only handles backend=mlx method=mlx_lora.",
            error_class="PERMISSION_DENIED",
        )
    if job.status not in {"QUEUED", "RUNNING"} or model_run.status not in {"QUEUED", "RUNNING"}:
        raise TrainMlxError("TRAIN_JOB_NOT_RUNNABLE", "Train job is not in a runnable state.", error_class="PERMISSION_DENIED")


def _trainer_input(job: Job, model_run: ModelRun, dataset: Dataset, run_dir: Path) -> MlxTrainerJobInput:
    params = json.loads(job.params_json)
    config = json.loads(model_run.config_json)
    training_preset = str(params.get("training_preset") or "balanced")
    return MlxTrainerJobInput(
        job_id=job.id,
        project_id=model_run.project_id,
        model_run_id=model_run.id,
        dataset_path=dataset.path,
        dataset_sha256=dataset.sha256,
        base_model=model_run.base_model,
        backend=model_run.backend,
        method=model_run.method,
        output_dir=str(run_dir),
        seed=model_run.seed,
        max_seq_length=1024,
        hyperparams=hyperparams(training_preset, config.get("hardware_profile_id")),
    )


def hyperparams(training_preset: str, hardware_profile_id: Any) -> dict[str, Any]:
    presets = {
        "quick": {"epochs": 1, "learning_rate": 0.0001, "batch_size": 1},
        "balanced": {"epochs": 3, "learning_rate": 0.0001, "batch_size": 1},
        "production": {"epochs": 5, "learning_rate": 0.0001, "batch_size": 1},
    }
    chosen = dict(presets.get(training_preset, presets["balanced"]))
    chosen["hardware_profile_id"] = hardware_profile_id
    return chosen


def _record_trainer_event(store: TrainingStore, job: Job, model_run: ModelRun, event: MlxTrainerEvent) -> None:
    ts = utc_now()
    if event.kind == "log":
        store.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="log",
            payload={"phase": "running", "model_run_id": model_run.id, "message": event.message or ""},
        )
        return
    if event.kind == "metric":
        store.append_event(
            job=job,
            ts=ts,
            level="info",
            event_type="metric",
            payload={
                "phase": "running",
                "model_run_id": model_run.id,
                "step": event.step,
                "total_steps": event.total_steps,
                "loss": event.loss,
                "vram_gb": event.vram_gb,
                "tokens_per_sec": event.tokens_per_sec,
                "checkpoint_id": None,
            },
        )


def sanitize_error(value: str) -> str:
    return value.replace("\n", " ")[:500]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
