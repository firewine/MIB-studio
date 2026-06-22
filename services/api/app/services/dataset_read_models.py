from __future__ import annotations

import json

from services.api.app.schemas.dataset import DatasetRead, ExampleRead
from services.shared.db.models import Dataset, Example


def read_dataset(dataset: Dataset) -> DatasetRead:
    return DatasetRead(
        id=dataset.id,
        project_id=dataset.project_id,
        version=dataset.version,
        status=dataset.status,  # type: ignore[arg-type]
        path=dataset.path,
        sample_count=dataset.sample_count,
        sha256=dataset.sha256,
        schema_version=dataset.schema_version,
        route_snapshot_sha256=dataset.route_snapshot_sha256,
        created_at=dataset.created_at,
        frozen_at=dataset.frozen_at,
    )


def read_example(example: Example) -> ExampleRead:
    return ExampleRead(
        id=example.id,
        dataset_id=example.dataset_id,
        source=example.source,  # type: ignore[arg-type]
        input=json.loads(example.input_json),
        output=json.loads(example.output_json),
        review_status=example.review_status,  # type: ignore[arg-type]
        approved=bool(example.approved),
        validation_errors=[],
        created_at=example.created_at,
    )
