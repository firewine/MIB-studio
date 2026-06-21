from __future__ import annotations

import json
from pathlib import Path

import yaml

from services.shared.db.models import Job, JobEvent, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text
from services.shared.db.session import create_sqlite_engine, session_factory
from services.worker.handlers.train_cuda import run_train_cuda_job
from services.worker.handlers.train_mlx import run_train_mlx_job
from services.worker.runtime.llamafactory import TrainerEvent
from services.worker.runtime.mlx_lm import MlxTrainerEvent
from tests.training.test_cuda_wrapper import create_queued_cuda_run, prepare_database as prepare_cuda_database
from tests.training.test_mlx_wrapper import create_queued_mlx_run, prepare_database as prepare_mlx_database


class DryRunCudaRunner:
    def run(self, config_path: Path, *, run_dir: Path) -> list[TrainerEvent]:
        assert config_path.exists()
        (run_dir / "adapter" / "probe.safetensors").write_bytes(b"probe adapter")
        return [
            TrainerEvent(kind="log", message="dry-run cuda probe"),
            TrainerEvent(kind="metric", step=10, total_steps=10, loss=0.4, vram_gb=12.0, tokens_per_sec=100.0),
        ]


class DryRunMlxRunner:
    def run(self, config_path: Path, *, run_dir: Path) -> list[MlxTrainerEvent]:
        assert config_path.exists()
        (run_dir / "adapter" / "probe.npz").write_bytes(b"probe adapter")
        return [
            MlxTrainerEvent(kind="log", message="dry-run mlx probe"),
            MlxTrainerEvent(kind="metric", step=8, total_steps=8, loss=0.35, vram_gb=9.0, tokens_per_sec=80.0),
        ]


def test_cuda_dry_run_writes_estimate_report_without_adapter_artifact(tmp_path: Path) -> None:
    database_url = prepare_cuda_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_cuda_run(database_url, mib_home)
    enable_dry_run(database_url, job_id)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert run_train_cuda_job(session, mib_home, job_id, runner=DryRunCudaRunner()) == model_run_id
            session.commit()

        run_dir = mib_home / "projects" / "project_1" / "runs" / model_run_id
        backend_config = yaml.safe_load((run_dir / "backend_config.yaml").read_text(encoding="utf-8"))
        train_config = json.loads((run_dir / "train_config.json").read_text(encoding="utf-8"))
        report = json.loads((run_dir / "dry_run_report.json").read_text(encoding="utf-8"))
        assert backend_config["max_steps"] == 10
        assert backend_config["save_strategy"] == "no"
        assert train_config["hyperparams"]["dry_run"] is True
        assert train_config["hyperparams"]["dry_run_steps"] == 10
        assert report["backend"] == "cuda"
        assert report["observed_vram_peak_mb"] == 12288.0
        assert report["predicted_vram_peak_mb"] == 12902.4
        assert report["tokens_per_sec"] == 100.0
        assert report["estimate_error_pct"] <= 30.0
        assert report["adapter_artifact_written"] is False
        assert not (run_dir / "manifest.json").exists()
        assert list((run_dir / "adapter").glob("*")) == []

        with factory() as session:
            job = session.get(Job, job_id)
            model_run = session.get(ModelRun, model_run_id)
            assert job.status == "SUCCEEDED"
            assert model_run.status == "SUCCEEDED"
            assert model_run.adapter_path is None
            artifact = session.query(JobEvent).filter_by(job_id=job_id, event_type="artifact").one()
            payload = json.loads(artifact.payload_json)
            assert payload["phase"] == "dry_run_completed"
            assert payload["dry_run_report_sha256"] == sha256_text(canonical_json(report) + "\n")
    finally:
        engine.dispose()


def test_mlx_dry_run_uses_same_report_contract_without_adapter_artifact(tmp_path: Path) -> None:
    database_url = prepare_mlx_database(tmp_path)
    mib_home = tmp_path / ".mib-home"
    job_id, model_run_id, _ = create_queued_mlx_run(database_url, mib_home)
    enable_dry_run(database_url, job_id)

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert run_train_mlx_job(session, mib_home, job_id, runner=DryRunMlxRunner()) == model_run_id
            session.commit()

        run_dir = mib_home / "projects" / "project_1" / "runs" / model_run_id
        backend_config = json.loads((run_dir / "backend_config.json").read_text(encoding="utf-8"))
        train_config = json.loads((run_dir / "train_config.json").read_text(encoding="utf-8"))
        report = json.loads((run_dir / "dry_run_report.json").read_text(encoding="utf-8"))
        assert backend_config["iters"] == 10
        assert train_config["hyperparams"]["dry_run"] is True
        assert train_config["hyperparams"]["dry_run_steps"] == 10
        assert report["backend"] == "mlx"
        assert report["observed_vram_peak_mb"] == 9216.0
        assert report["predicted_vram_peak_mb"] == 9676.8
        assert report["tokens_per_sec"] == 80.0
        assert report["estimate_error_pct"] <= 30.0
        assert report["adapter_artifact_written"] is False
        assert not (run_dir / "manifest.json").exists()
        assert list((run_dir / "adapter").glob("*")) == []
    finally:
        engine.dispose()


def enable_dry_run(database_url: str, job_id: str) -> None:
    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            job = session.get(Job, job_id)
            params = json.loads(job.params_json)
            params["dry_run"] = True
            job.params_json = canonical_json(params)
            session.commit()
    finally:
        engine.dispose()
