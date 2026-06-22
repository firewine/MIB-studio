from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.db.models import Dataset, Example, ProjectRoute


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True)
class DatasetExampleInput:
    input: dict[str, Any]
    output: dict[str, Any]
    source: str


@dataclass(frozen=True)
class StoredDatasetArtifact:
    path: Path
    sha256: str
    sample_count: int


class DatasetStore:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home

    def next_version(self, project_id: str) -> int:
        current = self.session.scalar(select(func.max(Dataset.version)).where(Dataset.project_id == project_id))
        return int(current or 0) + 1

    def route_snapshot(self, project_id: str) -> list[dict[str, Any]]:
        statement = (
            select(ProjectRoute)
            .where(ProjectRoute.project_id == project_id)
            .order_by(ProjectRoute.created_at.asc(), ProjectRoute.id.asc())
        )
        return [
            {
                "route_id": route.route_id,
                "description": route.description,
                "is_unsafe": bool(route.is_unsafe),
                "task_type": route.task_type,
                "requires_calculation": bool(route.requires_calculation),
                "requires_human_review": bool(route.requires_human_review),
                "is_default": bool(route.is_default),
                "examples": json.loads(route.examples_json),
            }
            for route in self.session.scalars(statement)
        ]

    def create_dataset(
        self,
        *,
        project_id: str,
        version: int,
        status: str,
        examples: list[DatasetExampleInput],
        route_snapshot_json: str,
        route_snapshot_sha256: str,
        created_at: str,
    ) -> Dataset:
        artifact = self.write_dataset_jsonl(project_id=project_id, version=version, examples=examples)
        dataset = Dataset(
            id=new_id(),
            project_id=project_id,
            version=version,
            path=str(artifact.path),
            sha256=artifact.sha256,
            sample_count=artifact.sample_count,
            status=status,
            schema_version="router.v1",
            route_snapshot_json=route_snapshot_json,
            route_snapshot_sha256=route_snapshot_sha256,
            created_at=created_at,
        )
        self.session.add(dataset)
        self.session.flush()
        self.add_examples(dataset_id=dataset.id, examples=examples, created_at=created_at)
        self.session.flush()
        return dataset

    def add_examples(self, *, dataset_id: str, examples: list[DatasetExampleInput], created_at: str) -> None:
        for index, item in enumerate(examples):
            self.session.add(
                Example(
                    id=new_id(),
                    dataset_id=dataset_id,
                    row_index=index,
                    input_json=canonical_json(item.input),
                    output_json=canonical_json(item.output),
                    input_sha256=sha256_text(canonical_json(item.input)),
                    source=item.source,
                    split="validation" if (index + 1) % 10 == 0 else "train",
                    review_status="PENDING",
                    approved=0,
                    created_at=created_at,
                )
            )

    def examples_for_dataset(self, dataset_id: str) -> list[Example]:
        statement = select(Example).where(Example.dataset_id == dataset_id).order_by(Example.row_index.asc())
        return list(self.session.scalars(statement))

    def write_dataset_jsonl(
        self,
        *,
        project_id: str,
        version: int,
        examples: list[DatasetExampleInput],
    ) -> StoredDatasetArtifact:
        dataset_dir = self.mib_home / "projects" / project_id / "datasets" / str(version)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        path = dataset_dir / "dataset.jsonl"
        rows = [
            {
                "instruction": "Classify the request into one of the allowed routes.",
                "input": item.input,
                "output": item.output,
            }
            for item in examples
        ]
        text = "".join(canonical_json(row) + "\n" for row in rows)
        path.write_text(text, encoding="utf-8")
        return StoredDatasetArtifact(path=path, sha256=sha256_text(text), sample_count=len(rows))

    def rewrite_dataset_from_examples(self, dataset: Dataset, examples: list[Example]) -> None:
        artifact = self.write_dataset_jsonl(
            project_id=dataset.project_id,
            version=dataset.version,
            examples=[
                DatasetExampleInput(
                    input=json.loads(example.input_json),
                    output=json.loads(example.output_json),
                    source=example.source,
                )
                for example in examples
            ],
        )
        dataset.path = str(artifact.path)
        dataset.sha256 = artifact.sha256
        dataset.sample_count = artifact.sample_count
