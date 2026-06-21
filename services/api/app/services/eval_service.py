from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.eval import EvalSetCreate, EvalSetPage, EvalSetRead
from services.shared.db.models import Dataset, EvalSet, Example, Project
from services.shared.db.repositories.dataset_store import canonical_json
from services.shared.db.repositories.eval_store import EvalSetStore


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class EvalSetService:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.store = EvalSetStore(session, mib_home)

    def create_eval_set(self, project_id: str, payload: EvalSetCreate) -> EvalSetRead:
        project = self._project_or_404(project_id)
        if project.archived_at is not None:
            raise APIError("PROJECT_ARCHIVED", "Archived projects are read-only.", status_code=409, details={"project_id": project_id})

        dataset = self._dataset_or_404(payload.dataset_id)
        if dataset.project_id != project_id:
            raise APIError(
                "DATASET_PROJECT_MISMATCH",
                "Dataset does not belong to the requested project.",
                status_code=409,
                details={"project_id": project_id, "dataset_id": dataset.id},
            )

        examples = self._select_examples(dataset, payload.example_ids)
        self._require_approved(dataset, examples)
        self._guard_teacher_source(payload.purpose, examples)
        self._guard_exact_overlap(payload.purpose, dataset, examples)

        now = utc_now()
        eval_set = self.store.create_eval_set(
            project_id=project_id,
            dataset_id=dataset.id,
            purpose=payload.purpose,
            examples=examples,
            route_snapshot_sha256=dataset.route_snapshot_sha256,
            labeler_ids_json=canonical_json(payload.labeler_ids),
            kappa=payload.kappa,
            frozen_at=now,
            created_at=now,
        )
        return self._read_eval_set(eval_set)

    def list_eval_sets(
        self,
        project_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        purpose: str | None = None,
    ) -> EvalSetPage:
        self._project_or_404(project_id)
        statement: Select[tuple[EvalSet]] = select(EvalSet).where(EvalSet.project_id == project_id)
        if purpose:
            statement = statement.where(EvalSet.purpose == purpose)
        if cursor:
            statement = statement.where(EvalSet.version < int(cursor))
        statement = statement.order_by(EvalSet.version.desc()).limit(limit + 1)
        eval_sets = list(self.session.scalars(statement))
        next_cursor = str(eval_sets[limit - 1].version) if len(eval_sets) > limit else None
        return EvalSetPage(items=[self._read_eval_set(item) for item in eval_sets[:limit]], next_cursor=next_cursor)

    def get_eval_set(self, eval_set_id: str) -> EvalSetRead:
        return self._read_eval_set(self._eval_set_or_404(eval_set_id))

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _dataset_or_404(self, dataset_id: str) -> Dataset:
        dataset = self.session.get(Dataset, dataset_id)
        if dataset is None:
            raise APIError("DATASET_NOT_FOUND", "Dataset does not exist.", status_code=404, details={"dataset_id": dataset_id})
        return dataset

    def _eval_set_or_404(self, eval_set_id: str) -> EvalSet:
        eval_set = self.session.get(EvalSet, eval_set_id)
        if eval_set is None:
            raise APIError("EVAL_SET_NOT_FOUND", "EvalSet does not exist.", status_code=404, details={"eval_set_id": eval_set_id})
        return eval_set

    def _select_examples(self, dataset: Dataset, example_ids: list[str]) -> list[Example]:
        examples = list(
            self.session.scalars(
                select(Example).where(Example.dataset_id == dataset.id).order_by(Example.row_index.asc())
            )
        )
        by_id = {example.id: example for example in examples}
        missing = [example_id for example_id in example_ids if example_id not in by_id]
        if missing:
            raise APIError(
                "EXAMPLE_NOT_FOUND",
                "One or more examples do not exist for this dataset.",
                status_code=404,
                details={"dataset_id": dataset.id, "example_ids": missing},
            )
        return [by_id[example_id] for example_id in example_ids]

    def _require_approved(self, dataset: Dataset, examples: list[Example]) -> None:
        unapproved = [example.id for example in examples if not example.approved or example.review_status != "APPROVED"]
        if unapproved:
            raise APIError(
                "EVAL_SET_EXAMPLES_NOT_APPROVED",
                "EvalSet freeze requires approved examples.",
                status_code=409,
                details={"dataset_id": dataset.id, "example_ids": unapproved},
            )

    def _guard_teacher_source(self, purpose: str, examples: list[Example]) -> None:
        generated = [example.id for example in examples if example.source in {"teacher", "hard_negative"}]
        if generated:
            raise APIError(
                "EVAL_SET_PRE_TEACHER_REQUIRED",
                f"{purpose} EvalSet must use pre-teacher gold examples.",
                status_code=409,
                details={"example_ids": generated},
            )

    def _guard_exact_overlap(self, purpose: str, dataset: Dataset, examples: list[Example]) -> None:
        if purpose == "teacher_guard":
            return
        selected_ids = {example.id for example in examples}
        selected_hashes = {example.input_sha256 for example in examples}
        statement = select(Example).where(
            Example.dataset_id == dataset.id,
            Example.id.not_in(selected_ids),
            Example.input_sha256.in_(selected_hashes),
        )
        overlaps = [example.id for example in self.session.scalars(statement)]
        if overlaps:
            raise APIError(
                "TRAIN_EVAL_OVERLAP",
                "EvalSet examples overlap with non-selected dataset examples.",
                status_code=409,
                details={"dataset_id": dataset.id, "overlap_example_ids": overlaps},
            )

    def _read_eval_set(self, eval_set: EvalSet) -> EvalSetRead:
        return EvalSetRead(
            id=eval_set.id,
            project_id=eval_set.project_id,
            dataset_id=eval_set.dataset_id,
            purpose=eval_set.purpose,  # type: ignore[arg-type]
            version=eval_set.version,
            path=eval_set.path,
            sha256=eval_set.sha256,
            sample_count=eval_set.sample_count,
            route_snapshot_sha256=eval_set.route_snapshot_sha256,
            labeler_ids_json=json.loads(eval_set.labeler_ids_json),
            kappa=eval_set.kappa,
            frozen_at=eval_set.frozen_at,
            created_at=eval_set.created_at,
        )
