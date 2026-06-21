from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.shared.db.models import EvalSet, Example
from services.shared.db.repositories.dataset_store import canonical_json, new_id, sha256_text


@dataclass(frozen=True)
class EvalSetArtifact:
    path: Path
    sha256: str
    sample_count: int


class EvalSetStore:
    def __init__(self, session: Session, mib_home: Path) -> None:
        self.session = session
        self.mib_home = mib_home

    def next_version(self, project_id: str) -> int:
        current = self.session.scalar(select(func.max(EvalSet.version)).where(EvalSet.project_id == project_id))
        return int(current or 0) + 1

    def write_eval_set_jsonl(
        self,
        *,
        project_id: str,
        version: int,
        examples: list[Example],
    ) -> EvalSetArtifact:
        eval_dir = self.mib_home / "projects" / project_id / "eval_sets" / str(version)
        eval_dir.mkdir(parents=True, exist_ok=True)
        path = eval_dir / "eval_set.jsonl"
        rows = [
            {
                "example_id": example.id,
                "input_sha256": example.input_sha256,
                "source": example.source,
                "input": json.loads(example.input_json),
                "output": json.loads(example.output_json),
            }
            for example in examples
        ]
        text = "".join(canonical_json(row) + "\n" for row in rows)
        path.write_text(text, encoding="utf-8")
        return EvalSetArtifact(path=path, sha256=sha256_text(text), sample_count=len(rows))

    def create_eval_set(
        self,
        *,
        project_id: str,
        dataset_id: str,
        purpose: str,
        examples: list[Example],
        route_snapshot_sha256: str,
        labeler_ids_json: str,
        kappa: float | None,
        frozen_at: str,
        created_at: str,
    ) -> EvalSet:
        version = self.next_version(project_id)
        artifact = self.write_eval_set_jsonl(project_id=project_id, version=version, examples=examples)
        eval_set = EvalSet(
            id=new_id(),
            project_id=project_id,
            dataset_id=dataset_id,
            version=version,
            path=str(artifact.path),
            sha256=artifact.sha256,
            sample_count=artifact.sample_count,
            purpose=purpose,
            route_snapshot_sha256=route_snapshot_sha256,
            labeler_ids_json=labeler_ids_json,
            kappa=kappa,
            frozen_at=frozen_at,
            is_holdout=1,
            created_at=created_at,
        )
        self.session.add(eval_set)
        self.session.flush()
        return eval_set
