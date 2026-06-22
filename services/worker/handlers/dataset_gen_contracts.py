from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class TeacherSyntheticClient(Protocol):
    def generate_examples(self, packet: dict[str, Any], *, target_count: int) -> Sequence[dict[str, Any]]:
        """Return raw teacher examples shaped as {'input': {...}, 'output': {...}}."""


@dataclass(frozen=True)
class DatasetGenResult:
    job_id: str
    dataset_id: str
    generated_count: int
    hard_negative_count: int
    validated_count: int
    rejected_count: int
    packet_sha256: str


class DatasetGenWorkerError(Exception):
    def __init__(self, code: str, message: str, *, error_class: str = "UNKNOWN") -> None:
        self.code = code
        self.message = message
        self.error_class = error_class
        super().__init__(message)
