from __future__ import annotations

import json
from typing import Any

from services.api.app.schemas.router_validation import validate_router_example
from services.shared.db.models import Dataset
from services.shared.db.repositories.dataset_store import DatasetExampleInput, canonical_json, sha256_text
from services.worker.handlers.dataset_gen_contracts import DatasetGenWorkerError


def validate_generated_examples(
    raw_examples: list[dict[str, Any]],
    source_dataset: Dataset,
    guard_hashes: set[str],
    *,
    target_count: int,
    hard_negative_min_count: int,
) -> list[DatasetExampleInput]:
    if len(raw_examples) < target_count:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_UNDER_GENERATED",
            "Teacher response produced fewer examples than requested.",
            error_class="TEACHER_API_ERROR",
        )

    route_ids = [route["route_id"] for route in json.loads(source_dataset.route_snapshot_json)]
    examples: list[DatasetExampleInput] = []
    row_errors: list[dict[str, Any]] = []
    overlaps: list[str] = []
    for index, raw in enumerate(raw_examples):
        input_payload = raw.get("input")
        output_payload = raw.get("output")
        source = raw.get("source") or "teacher"
        if not isinstance(input_payload, dict) or not isinstance(output_payload, dict):
            row_errors.append({"row_index": index, "code": "ROW_SHAPE_INVALID"})
            continue
        if source not in {"teacher", "hard_negative"}:
            row_errors.append({"row_index": index, "code": "SOURCE_INVALID"})
            continue
        input_sha256 = sha256_text(canonical_json(input_payload))
        if input_sha256 in guard_hashes:
            overlaps.append(input_sha256)
        errors = validate_router_example(input_payload, output_payload, route_ids)
        if errors:
            row_errors.append(
                {"row_index": index, "errors": [error.model_dump() for error in errors], "code": "SCHEMA_VALIDATION_FAILED"}
            )
            continue
        examples.append(DatasetExampleInput(input=input_payload, output=output_payload, source=str(source)))

    if overlaps:
        raise DatasetGenWorkerError(
            "TEACHER_GUARD_SYNTHETIC_OVERLAP",
            "Teacher synthetic examples overlap with the frozen teacher_guard inputs.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    if row_errors:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_SCHEMA_INVALID",
            "Teacher synthetic examples failed router schema validation.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    if len(examples) < target_count:
        raise DatasetGenWorkerError(
            "TEACHER_SYNTHETIC_UNDER_VALIDATED",
            "Teacher response did not produce enough schema-valid examples.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    hard_negative_count = sum(1 for example in examples if example.source == "hard_negative")
    if hard_negative_count < hard_negative_min_count:
        raise DatasetGenWorkerError(
            "DATASET_HARD_NEGATIVE_MIN_NOT_MET",
            f"Teacher response produced {hard_negative_count} schema-valid hard negatives; {hard_negative_min_count} required.",
            error_class="SCHEMA_VALIDATION_FAIL",
        )
    return examples
