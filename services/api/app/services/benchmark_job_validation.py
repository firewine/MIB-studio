from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError, json_safe_errors
from services.api.app.schemas.job import BenchmarkParams
from services.shared.db.models import Credential, EvalSet, ModelRun


def parse_benchmark_params(raw_params: dict[str, Any]) -> BenchmarkParams:
    try:
        return BenchmarkParams.model_validate(raw_params)
    except ValidationError as exc:
        raise APIError(
            "VALIDATION_ERROR",
            "Request validation failed.",
            status_code=422,
            details={"errors": json_safe_errors(exc.errors())},
        ) from exc


def benchmark_eval_set(session: Session, project_id: str, eval_set_id: str) -> EvalSet:
    eval_set = session.get(EvalSet, eval_set_id)
    if eval_set is None:
        raise APIError("EVAL_SET_NOT_FOUND", "EvalSet does not exist.", status_code=404, details={"eval_set_id": eval_set_id})
    if eval_set.project_id != project_id:
        raise APIError(
            "EVAL_SET_PROJECT_MISMATCH",
            "EvalSet does not belong to the requested project.",
            status_code=409,
            details={"project_id": project_id, "eval_set_id": eval_set.id},
        )
    if eval_set.purpose not in {"benchmark_gold", "finance_reference"} or eval_set.sample_count < 200:
        raise APIError(
            "BENCHMARK_EVAL_SET_REQUIRED",
            "Benchmark requires a frozen benchmark-quality EvalSet.",
            status_code=409,
            details={"eval_set_id": eval_set.id, "purpose": eval_set.purpose, "sample_count": eval_set.sample_count},
        )
    return eval_set


def validate_benchmark_targets(session: Session, project_id: str, params: BenchmarkParams) -> None:
    by_type: dict[str, list[Any]] = {}
    for target in params.targets:
        by_type.setdefault(target.target_type, []).append(target)

    _require_exact_targets(by_type)
    fine_tuned = by_type.get("fine_tuned", [])
    if not 1 <= len(fine_tuned) <= 2:
        raise APIError(
            "BENCHMARK_FINE_TUNED_TARGET_REQUIRED",
            "Benchmark requires one completed fine_tuned target, or two for CUDA/MLX parity.",
            status_code=422,
            details={"actual": len(fine_tuned)},
        )
    if len(by_type.get("local_large", [])) > 1:
        raise APIError(
            "BENCHMARK_TARGETS_REQUIRED",
            "Benchmark allows at most one optional local_large target.",
            status_code=422,
            details={"target_type": "local_large", "actual": len(by_type.get("local_large", []))},
        )

    _validate_prompt_targets(by_type["prompt_only"])
    _validate_teacher_targets(session, by_type["teacher"])
    _validate_rule_targets(by_type["rule_based"])
    _validate_fine_tuned_targets(session, project_id, fine_tuned)
    _validate_local_large_targets(by_type.get("local_large", []))


def _require_exact_targets(by_type: dict[str, list[Any]]) -> None:
    required_counts = {"prompt_only": 1, "teacher": 1, "rule_based": 1}
    for target_type, expected in required_counts.items():
        actual = len(by_type.get(target_type, []))
        if actual != expected:
            raise APIError(
                "BENCHMARK_TARGETS_REQUIRED",
                "Benchmark requires exactly one prompt_only, teacher, and rule_based target.",
                status_code=422,
                details={"target_type": target_type, "expected": expected, "actual": actual},
            )


def _validate_prompt_targets(targets: list[Any]) -> None:
    for target in targets:
        if target.backend != "prompt_only" or not target.base_model or not target.prompt_template_sha256:
            raise APIError(
                "BENCHMARK_TARGET_INVALID",
                "prompt_only target requires prompt_only backend, base_model, and prompt_template_sha256.",
                status_code=422,
                details={"target_key": target.target_key},
            )


def _validate_teacher_targets(session: Session, targets: list[Any]) -> None:
    for target in targets:
        credential = session.get(Credential, target.credential_id or "")
        if target.backend != "teacher" or credential is None or credential.is_revoked:
            raise APIError(
                "BENCHMARK_TEACHER_CREDENTIAL_REQUIRED",
                "teacher target requires an active local credential reference.",
                status_code=409,
                details={"target_key": target.target_key, "credential_id": target.credential_id},
            )


def _validate_rule_targets(targets: list[Any]) -> None:
    for target in targets:
        if target.backend != "rule_based" or not target.routing_rules_path or not target.routing_rules_sha256:
            raise APIError(
                "BENCHMARK_TARGET_INVALID",
                "rule_based target requires routing_rules_path and routing_rules_sha256.",
                status_code=422,
                details={"target_key": target.target_key},
            )


def _validate_fine_tuned_targets(session: Session, project_id: str, targets: list[Any]) -> None:
    for target in targets:
        model_run = session.get(ModelRun, target.model_run_id or "")
        if model_run is None or model_run.project_id != project_id:
            raise APIError(
                "MODEL_RUN_NOT_FOUND",
                "fine_tuned benchmark target ModelRun does not exist for this project.",
                status_code=404,
                details={"target_key": target.target_key, "model_run_id": target.model_run_id},
            )
        if target.backend != model_run.backend:
            raise APIError(
                "BENCHMARK_TARGET_BACKEND_MISMATCH",
                "fine_tuned target backend must match the ModelRun backend.",
                status_code=409,
                details={"target_key": target.target_key, "target_backend": target.backend, "model_run_backend": model_run.backend},
            )
        if model_run.status != "SUCCEEDED" or not model_run.adapter_sha256 or not model_run.artifact_manifest_sha256:
            raise APIError(
                "MODEL_RUN_NOT_READY",
                "fine_tuned benchmark target requires a completed ModelRun with adapter lineage.",
                status_code=409,
                details={"target_key": target.target_key, "model_run_id": model_run.id, "status": model_run.status},
            )


def _validate_local_large_targets(targets: list[Any]) -> None:
    for target in targets:
        if target.backend != "local_large" or target.required:
            raise APIError(
                "BENCHMARK_TARGET_INVALID",
                "local_large target must be optional and use local_large backend.",
                status_code=422,
                details={"target_key": target.target_key},
            )
