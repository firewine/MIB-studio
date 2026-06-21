from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from services.shared.db.repositories.dataset_store import canonical_json, sha256_text


@dataclass(frozen=True)
class MlxTrainerJobInput:
    job_id: str
    project_id: str
    model_run_id: str
    dataset_path: str
    dataset_sha256: str
    base_model: str
    backend: str
    method: str
    output_dir: str
    seed: int
    max_seq_length: int
    hyperparams: dict[str, Any]


@dataclass(frozen=True)
class MlxTrainerEvent:
    kind: str
    message: str | None = None
    step: int | None = None
    total_steps: int | None = None
    loss: float | None = None
    vram_gb: float | None = None
    tokens_per_sec: float | None = None


class MlxLmRunner(Protocol):
    def run(self, config_path: Path, *, run_dir: Path) -> Iterable[MlxTrainerEvent]:
        """Run mlx-lm and yield sanitized events."""


class SubprocessMlxLmRunner:
    def run(self, config_path: Path, *, run_dir: Path) -> Iterator[MlxTrainerEvent]:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        command = [
            "python",
            "-m",
            "mlx_lm.lora",
            "--model",
            str(config["model"]),
            "--train",
            "--data",
            str(config["data"]),
            "--adapter-path",
            str(config["adapter_path"]),
            "--iters",
            str(config["iters"]),
            "--batch-size",
            str(config["batch_size"]),
            "--learning-rate",
            str(config["learning_rate"]),
        ]
        process = subprocess.Popen(command, cwd=str(run_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.stdout is not None
        for line in process.stdout:
            message = line.strip()
            if message:
                yield MlxTrainerEvent(kind="log", message=sanitize_log(message))
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"mlx_lm.lora exited with code {return_code}")


def write_mlx_artifacts(
    trainer_input: MlxTrainerJobInput,
    *,
    model_cache_path: Path,
) -> Path:
    run_dir = Path(trainer_input.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "adapter").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    dataset_dir = run_dir / "dataset" / "mlx"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "train_config.json").write_text(canonical_json(trainer_input_to_dict(trainer_input)) + "\n", encoding="utf-8")
    train_count = convert_dataset(Path(trainer_input.dataset_path), dataset_dir)
    config = backend_config(trainer_input, model_cache_path=model_cache_path, dataset_dir=dataset_dir, train_count=train_count)
    config_path = run_dir / "backend_config.json"
    config_path.write_text(canonical_json(config) + "\n", encoding="utf-8")
    return config_path


def trainer_input_to_dict(value: MlxTrainerJobInput) -> dict[str, Any]:
    return {
        "job_id": value.job_id,
        "project_id": value.project_id,
        "model_run_id": value.model_run_id,
        "dataset_path": value.dataset_path,
        "dataset_sha256": value.dataset_sha256,
        "base_model": value.base_model,
        "backend": value.backend,
        "method": value.method,
        "output_dir": value.output_dir,
        "seed": value.seed,
        "max_seq_length": value.max_seq_length,
        "hyperparams": value.hyperparams,
    }


def backend_config(
    trainer_input: MlxTrainerJobInput,
    *,
    model_cache_path: Path,
    dataset_dir: Path,
    train_count: int,
) -> dict[str, Any]:
    hyperparams = trainer_input.hyperparams
    iters = max(1, int(hyperparams["epochs"] * train_count / hyperparams["batch_size"]))
    if hyperparams.get("dry_run"):
        iters = int(hyperparams["dry_run_steps"])
    return {
        "model": str(model_cache_path),
        "train": True,
        "data": str(dataset_dir),
        "adapter_path": str(Path(trainer_input.output_dir) / "adapter"),
        "iters": iters,
        "batch_size": hyperparams["batch_size"],
        "learning_rate": hyperparams["learning_rate"],
        "max_seq_length": trainer_input.max_seq_length,
        "seed": trainer_input.seed,
        "trust_remote_code": False,
    }


def convert_dataset(dataset_path: Path, dataset_dir: Path) -> int:
    train_rows: list[dict[str, list[dict[str, str]]]] = []
    valid_rows: list[dict[str, list[dict[str, str]]]] = []
    for index, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        converted = {
            "messages": [
                {
                    "role": "user",
                    "content": str(row["instruction"]) + "\n\n" + json.dumps(row["input"], sort_keys=True, ensure_ascii=False),
                },
                {"role": "assistant", "content": json.dumps(row["output"], sort_keys=True, ensure_ascii=False)},
            ]
        }
        if (index + 1) % 10 == 0:
            valid_rows.append(converted)
        else:
            train_rows.append(converted)
    write_jsonl(dataset_dir / "train.jsonl", train_rows)
    write_jsonl(dataset_dir / "valid.jsonl", valid_rows)
    return len(train_rows)


def write_jsonl(path: Path, rows: list[dict[str, list[dict[str, str]]]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def write_mlx_manifest(run_dir: Path) -> tuple[Path, str, str]:
    adapter_dir = run_dir / "adapter"
    files = []
    for path in sorted(item for item in adapter_dir.rglob("*") if item.is_file()):
        files.append({"path": str(path.relative_to(run_dir)), "sha256": sha256_bytes(path.read_bytes()), "size_bytes": path.stat().st_size})
    if not files:
        raise FileNotFoundError("adapter artifact directory is empty")
    adapter_sha256 = sha256_text(canonical_json(files))
    manifest = {
        "schema_version": "adapter_manifest.v1",
        "trainer_backend": "mlx_lm",
        "adapter_format": "mlx_lora_adapter",
        "adapter_sha256": adapter_sha256,
        "files": files,
    }
    text = canonical_json(manifest) + "\n"
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(text, encoding="utf-8")
    return manifest_path, adapter_sha256, sha256_text(text)


def sanitize_log(value: str) -> str:
    return value.replace("\r", " ")[:500]


def sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
