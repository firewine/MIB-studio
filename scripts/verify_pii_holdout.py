#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ENTITY_TYPES = {"email", "phone", "rrn", "card", "account", "ip", "name", "address"}
LOCALES = {"ko-KR", "en-US", "mixed"}
SOURCES = {"synthetic", "red_team", "regression"}
FULL_CORPUS_MINIMUMS = {
    "email": 40,
    "phone": 40,
    "name": 40,
    "address": 40,
    "rrn": 25,
    "card": 25,
    "account": 25,
    "ip": 25,
}


def validate_row(row: dict, line_no: int) -> list[str]:
    errors: list[str] = []
    for key in ["id", "locale", "text", "entities", "source"]:
        if key not in row:
            errors.append(f"line {line_no}: missing {key}")
    if not isinstance(row.get("id"), str) or not row["id"].startswith("pii_"):
        errors.append(f"line {line_no}: id must start with pii_")
    if row.get("locale") not in LOCALES:
        errors.append(f"line {line_no}: invalid locale")
    if row.get("source") not in SOURCES:
        errors.append(f"line {line_no}: invalid source")
    text = row.get("text")
    if not isinstance(text, str) or not text:
        errors.append(f"line {line_no}: text must be non-empty")
        text = ""
    entities = row.get("entities")
    if not isinstance(entities, list) or not entities:
        errors.append(f"line {line_no}: entities must be a non-empty list")
        return errors
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            errors.append(f"line {line_no}: entities[{index}] must be object")
            continue
        entity_type = entity.get("type")
        start = entity.get("start")
        end = entity.get("end")
        entity_text = entity.get("text")
        if entity_type not in ENTITY_TYPES:
            errors.append(f"line {line_no}: entities[{index}].type invalid")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(text):
            errors.append(f"line {line_no}: entities[{index}] span invalid")
            continue
        if text[start:end] != entity_text:
            errors.append(f"line {line_no}: entities[{index}].text does not match span")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="examples/security/pii_holdout.v1.jsonl")
    parser.add_argument("--phase", default="scaffold")
    parser.add_argument("--json-output", default="artifacts/security/pii_holdout_report.json")
    args = parser.parse_args()

    path = Path(args.path)
    errors: list[str] = []
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc}")
            continue
        rows.append(row)
        errors.extend(validate_row(row, line_no))

    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for row in rows:
        source_counts[row.get("source", "")] += 1
        for entity in row.get("entities", []):
            if isinstance(entity, dict):
                type_counts[entity.get("type", "")] += 1

    full_gate = args.phase not in {"scaffold", "m0", "m1", "m1-smoke"}
    if full_gate:
        if len(rows) < 300:
            errors.append(f"full PII holdout requires >=300 rows, got {len(rows)}")
        for entity_type, minimum in FULL_CORPUS_MINIMUMS.items():
            if type_counts[entity_type] < minimum:
                errors.append(f"full PII holdout requires >={minimum} {entity_type} entities, got {type_counts[entity_type]}")
        if source_counts["red_team"] < 60:
            errors.append(f"full PII holdout requires >=60 red_team rows, got {source_counts['red_team']}")
    elif len(rows) < 1:
        errors.append("scaffold PII holdout requires at least one schema sample row")

    report = {
        "path": str(path),
        "phase": args.phase,
        "full_gate": full_gate,
        "row_count": len(rows),
        "entity_counts": dict(sorted(type_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "errors": errors,
    }
    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
