from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


POLICY_VERSION = "pii.v1"
PATH_KEYS = {"path", "file_path", "filepath", "source_file", "raw_file", "csv_path"}

PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
    ("phone", re.compile(r"(?:\+82[-\s]?)?0?1[016789][-\s]?\d{3,4}[-\s]?\d{4}\b"), "<PHONE>"),
    ("rrn", re.compile(r"\b\d{6}-?[1-4]\d{6}\b"), "<RRN>"),
    ("card", re.compile(r"\b(?:\d[ -]?){13,19}\b"), "<CARD>"),
    ("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<IP>"),
)


@dataclass
class PiiMaskSummary:
    entity_counts: Counter[str] = field(default_factory=Counter)
    masked_count: int = 0

    def record(self, entity_type: str) -> None:
        self.entity_counts[entity_type] += 1
        self.masked_count += 1

    def as_dict(self, *, example_count: int) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "example_count": example_count,
            "masked_count": self.masked_count,
            "entity_counts": dict(sorted(self.entity_counts.items())),
            "transmitted": ["rule schema", "output schema", "anonymized_examples", "generation instruction"],
            "not_transmitted": ["raw CSV", "file paths", "personal identifiers", "unapproved samples"],
        }


def mask_json(value: Any, summary: PiiMaskSummary) -> Any:
    if isinstance(value, str):
        return mask_text(value, summary)
    if isinstance(value, list):
        return [mask_json(item, summary) for item in value]
    if isinstance(value, dict):
        return {key: _mask_dict_value(key, item, summary) for key, item in value.items()}
    return value


def mask_text(value: str, summary: PiiMaskSummary) -> str:
    masked = value
    for entity_type, pattern, replacement in PATTERNS:
        masked = pattern.sub(lambda match: _replace(match, entity_type, replacement, summary), masked)
    return masked


def _mask_dict_value(key: str, value: Any, summary: PiiMaskSummary) -> Any:
    if key.lower() in PATH_KEYS:
        summary.record("file_path")
        return "<FILE_PATH>"
    return mask_json(value, summary)


def _replace(match: re.Match[str], entity_type: str, replacement: str, summary: PiiMaskSummary) -> str:
    if entity_type == "card" and not _looks_like_card(match.group(0)):
        return match.group(0)
    if entity_type == "ip" and not _looks_like_ip(match.group(0)):
        return match.group(0)
    summary.record(entity_type)
    return replacement


def _looks_like_card(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return 13 <= len(digits) <= 19


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
