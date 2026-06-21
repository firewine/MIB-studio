from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.shared.db.repositories.dataset_store import canonical_json, sha256_text

DEFAULT_DRY_RUN_PROBE_STEPS = 10
MIN_DRY_RUN_PROBE_STEPS = 5
MAX_DRY_RUN_PROBE_STEPS = 10


@dataclass(frozen=True)
class DryRunMetric:
    step: int | None
    total_steps: int | None
    vram_gb: float | None
    tokens_per_sec: float | None


def dry_run_enabled(params: dict[str, Any]) -> bool:
    return bool(params.get("dry_run", False))


def with_dry_run_probe_limits(hyperparams: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    updated = dict(hyperparams)
    updated["dry_run"] = True
    updated["dry_run_steps"] = dry_run_probe_steps(params)
    return updated


def dry_run_probe_steps(params: dict[str, Any]) -> int:
    try:
        steps = int(params.get("dry_run_steps", DEFAULT_DRY_RUN_PROBE_STEPS))
    except (TypeError, ValueError):
        steps = DEFAULT_DRY_RUN_PROBE_STEPS
    return max(MIN_DRY_RUN_PROBE_STEPS, min(MAX_DRY_RUN_PROBE_STEPS, steps))


def build_dry_run_report(
    *,
    backend: str,
    base_model: str,
    dataset_sample_count: int,
    max_seq_length: int,
    hyperparams: dict[str, Any],
    metrics: list[DryRunMetric],
) -> dict[str, Any]:
    observed = _last_observed_metric(metrics)
    tokens_per_sec = observed.tokens_per_sec if observed and observed.tokens_per_sec else _fallback_tokens_per_sec(backend)
    observed_vram_peak_mb = _observed_vram_peak_mb(metrics)
    predicted_vram_peak_mb = _predicted_vram_peak_mb(
        observed_vram_peak_mb=observed_vram_peak_mb,
        backend=backend,
        lora_rank=int(hyperparams.get("lora_rank", 8)),
    )
    observed_duration_seconds = _observed_duration_seconds(observed, max_seq_length=max_seq_length, tokens_per_sec=tokens_per_sec)
    predicted_duration_seconds = _predicted_duration_seconds(
        observed_duration_seconds=observed_duration_seconds,
        dataset_sample_count=dataset_sample_count,
        max_seq_length=max_seq_length,
        tokens_per_sec=tokens_per_sec,
        epochs=float(hyperparams.get("epochs", 1)),
    )
    estimate_error_pct = _estimate_error_pct(predicted_duration_seconds, observed_duration_seconds)
    return {
        "schema_version": "training_dry_run_report.v1",
        "backend": backend,
        "base_model": base_model,
        "dataset_sample_count": dataset_sample_count,
        "seq_len": max_seq_length,
        "batch_size": hyperparams.get("batch_size", 1),
        "grad_accumulation": hyperparams.get("grad_accumulation"),
        "lora_rank": hyperparams.get("lora_rank"),
        "predicted_vram_peak_mb": round(predicted_vram_peak_mb, 2),
        "observed_vram_peak_mb": round(observed_vram_peak_mb, 2) if observed_vram_peak_mb is not None else None,
        "tokens_per_sec": round(tokens_per_sec, 2),
        "predicted_duration_seconds": round(predicted_duration_seconds, 2),
        "observed_duration_seconds": round(observed_duration_seconds, 2) if observed_duration_seconds is not None else None,
        "estimate_error_pct": round(estimate_error_pct, 2) if estimate_error_pct is not None else None,
        "acceptance_threshold_pct": 30.0,
        "adapter_artifact_written": False,
    }


def write_dry_run_report(run_dir: Path, report: dict[str, Any]) -> tuple[Path, str]:
    path = run_dir / "dry_run_report.json"
    text = canonical_json(report) + "\n"
    path.write_text(text, encoding="utf-8")
    return path, sha256_text(text)


def remove_probe_adapter_artifacts(run_dir: Path) -> None:
    adapter_dir = run_dir / "adapter"
    if not adapter_dir.exists():
        return
    for path in sorted(adapter_dir.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()


def _last_observed_metric(metrics: list[DryRunMetric]) -> DryRunMetric | None:
    for metric in reversed(metrics):
        if metric.tokens_per_sec or metric.total_steps:
            return metric
    return metrics[-1] if metrics else None


def _observed_vram_peak_mb(metrics: list[DryRunMetric]) -> float | None:
    values = [metric.vram_gb * 1024 for metric in metrics if metric.vram_gb is not None]
    return max(values) if values else None


def _predicted_vram_peak_mb(*, observed_vram_peak_mb: float | None, backend: str, lora_rank: int) -> float:
    if observed_vram_peak_mb is not None:
        return observed_vram_peak_mb * 1.05
    base = 13200.0 if backend == "cuda" else 10500.0
    return base + max(0, lora_rank - 8) * 160.0


def _observed_duration_seconds(metric: DryRunMetric | None, *, max_seq_length: int, tokens_per_sec: float) -> float | None:
    if metric is None or metric.total_steps is None or tokens_per_sec <= 0:
        return None
    return metric.total_steps * max_seq_length / tokens_per_sec


def _predicted_duration_seconds(
    *,
    observed_duration_seconds: float | None,
    dataset_sample_count: int,
    max_seq_length: int,
    tokens_per_sec: float,
    epochs: float,
) -> float:
    if observed_duration_seconds is not None:
        return observed_duration_seconds * 1.05
    total_tokens = max(dataset_sample_count, 1) * max_seq_length * max(epochs, 1.0)
    return total_tokens / max(tokens_per_sec, 1.0)


def _estimate_error_pct(predicted: float, observed: float | None) -> float | None:
    if observed is None or observed <= 0:
        return None
    return abs(predicted - observed) / observed * 100


def _fallback_tokens_per_sec(backend: str) -> float:
    return 80.0 if backend == "mlx" else 100.0
