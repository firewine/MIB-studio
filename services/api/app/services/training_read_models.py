from __future__ import annotations

from services.api.app.schemas.training import ModelRunRead
from services.shared.db.models import ModelRun


def read_model_run(model_run: ModelRun, *, job_id: str | None) -> ModelRunRead:
    return ModelRunRead(
        id=model_run.id,
        job_id=job_id,
        project_id=model_run.project_id,
        dataset_id=model_run.dataset_id,
        base_model=model_run.base_model,  # type: ignore[arg-type]
        backend=model_run.backend,  # type: ignore[arg-type]
        method=model_run.method,  # type: ignore[arg-type]
        adapter_path=model_run.adapter_path,
        adapter_sha256=model_run.adapter_sha256,
        artifact_manifest_sha256=model_run.artifact_manifest_sha256,
        status=model_run.status,  # type: ignore[arg-type]
        seed=model_run.seed,
        config_hash=model_run.config_hash,
        best_checkpoint_id=model_run.best_checkpoint_id,
        resumable=bool(model_run.resumable),
        started_at=model_run.started_at,
        ended_at=model_run.ended_at,
        created_at=model_run.created_at,
    )
