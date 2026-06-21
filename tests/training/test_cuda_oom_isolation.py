from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.shared.db.models import Job, JobEvent, ModelRun
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.train_cuda import TrainCudaError, run_train_cuda_job
from tests.training.test_cuda_wrapper import create_queued_cuda_run, prepare_database


class CudaOomRunner:
    def run(self, config_path: Path, *, run_dir: Path) -> list[object]:
        raise RuntimeError("CUDA out of memory\nraw stack line that must be sanitized")


def test_simulated_cuda_oom_maps_to_terminal_failed_state_and_sanitized_event(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_cuda_run(database_url, mib_home)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            with pytest.raises(TrainCudaError) as exc_info:
                run_train_cuda_job(session, mib_home, job_id, runner=CudaOomRunner())
            session.commit()
            assert exc_info.value.error_class == "CUDA_OOM"

        with factory() as session:
            job = session.get(Job, job_id)
            model_run = session.get(ModelRun, model_run_id)
            assert job.status == "FAILED"
            assert job.error_class == "CUDA_OOM"
            assert "CUDA out of memory" in str(job.error_message)
            assert "\n" not in str(job.error_message)
            assert model_run.status == "FAILED"
            event = session.query(JobEvent).filter_by(job_id=job_id, event_type="error").one()
            payload = json.loads(event.payload_json)
            assert payload["error_class"] == "CUDA_OOM"
            assert "\n" not in payload["message"]
    finally:
        engine.dispose()
