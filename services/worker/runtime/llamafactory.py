from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml

from services.shared.db.repositories.dataset_store import canonical_json, sha256_text


@dataclass(frozen=True)
class TrainerJobInput:
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
class TrainerEvent:
    kind: str
    message: str | None = None
    step: int | None = None
    total_steps: int | None = None
    loss: float | None = None
    vram_gb: float | None = None
    tokens_per_sec: float | None = None


class LlamaFactoryRunner(Protocol):
    def run(self, config_path: Path, *, run_dir: Path) -> Iterable[TrainerEvent]:
        """Run LLaMA-Factory and yield sanitized log/metric events."""


class SubprocessLlamaFactoryRunner:
    def run(self, config_path: Path, *, run_dir: Path) -> Iterator[TrainerEvent]:
        process = subprocess.Popen(
            ["llamafactory-cli", "train", str(config_path)],
            cwd=str(run_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert process.stdout is not None
        for line in process.stdout:
            message = line.strip()
            if message:
                yield TrainerEvent(kind="log", message=sanitize_log(message))
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"llamafactory-cli exited with code {return_code}")


def write_llamafactory_artifacts(
    trainer_input: TrainerJobInput,
    *,
    model_cache_path: Path,
    dataset_id: str,
) -> Path:
    run_dir = Path(trainer_input.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "adapter").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    dataset_dir = run_dir / "dataset" / "llamafactory"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    train_config_json = canonical_json(trainer_input_to_dict(trainer_input))
    (run_dir / "train_config.json").write_text(train_config_json + "\n", encoding="utf-8")
    convert_dataset(Path(trainer_input.dataset_path), dataset_dir, dataset_id=dataset_id)
    config = backend_config(trainer_input, model_cache_path=model_cache_path, dataset_dir=dataset_dir, dataset_id=dataset_id)
    config_path = run_dir / "backend_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def trainer_input_to_dict(value: TrainerJobInput) -> dict[str, Any]:
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


def backend_config(trainer_input: TrainerJobInput, *, model_cache_path: Path, dataset_dir: Path, dataset_id: str) -> dict[str, Any]:
    hyperparams = trainer_input.hyperparams
    return {
        "stage": "sft",
        "do_train": True,
        "model_name_or_path": str(model_cache_path),
        "dataset": "mib_router_" + dataset_id,
        "dataset_dir": str(dataset_dir),
        "template": template_for_model(trainer_input.base_model),
        "finetuning_type": "lora",
        "lora_target": "all",
        "output_dir": str(Path(trainer_input.output_dir) / "adapter"),
        "overwrite_output_dir": True,
        "cutoff_len": trainer_input.max_seq_length,
        "per_device_train_batch_size": hyperparams["batch_size"],
        "gradient_accumulation_steps": hyperparams["grad_accumulation"],
        "learning_rate": hyperparams["learning_rate"],
        "num_train_epochs": hyperparams["epochs"],
        "logging_steps": 10,
        "save_steps": 100,
        "bf16": True,
        "quantization_bit": 4,
        "trust_remote_code": False,
        "seed": trainer_input.seed,
    }


def convert_dataset(dataset_path: Path, dataset_dir: Path, *, dataset_id: str) -> None:
    train_rows: list[dict[str, str]] = []
    valid_rows: list[dict[str, str]] = []
    for index, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        converted = {
            "instruction": str(row["instruction"]),
            "input": json.dumps(row["input"], sort_keys=True, ensure_ascii=False),
            "output": json.dumps(row["output"], sort_keys=True, ensure_ascii=False),
        }
        if (index + 1) % 10 == 0:
            valid_rows.append(converted)
        else:
            train_rows.append(converted)
    write_jsonl(dataset_dir / "train.jsonl", train_rows)
    write_jsonl(dataset_dir / "valid.jsonl", valid_rows)
    dataset_info = {
        "mib_router_" + dataset_id: {
            "file_name": "train.jsonl",
            "validation_file_name": "valid.jsonl",
            "columns": {"prompt": "instruction", "query": "input", "response": "output"},
        }
    }
    (dataset_dir / "dataset_info.json").write_text(canonical_json(dataset_info) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def write_manifest(run_dir: Path, *, trainer_backend: str = "llamafactory") -> tuple[Path, str, str]:
    adapter_dir = run_dir / "adapter"
    files = []
    for path in sorted(item for item in adapter_dir.rglob("*") if item.is_file()):
        files.append({"path": str(path.relative_to(run_dir)), "sha256": sha256_bytes(path.read_bytes()), "size_bytes": path.stat().st_size})
    if not files:
        raise FileNotFoundError("adapter artifact directory is empty")
    adapter_sha256 = sha256_text(canonical_json(files))
    manifest = {
        "schema_version": "adapter_manifest.v1",
        "trainer_backend": trainer_backend,
        "adapter_sha256": adapter_sha256,
        "files": files,
    }
    text = canonical_json(manifest) + "\n"
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(text, encoding="utf-8")
    return manifest_path, adapter_sha256, sha256_text(text)


def template_for_model(model_id: str) -> str:
    if "gemma" in model_id:
        return "gemma"
    if "Phi" in model_id or "phi" in model_id:
        return "phi"
    return "default"


def sanitize_log(value: str) -> str:
    return value.replace("\r", " ")[:500]


def sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
