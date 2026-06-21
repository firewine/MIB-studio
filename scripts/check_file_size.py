#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_ROOTS = ["services", "packages", "apps/desktop/src"]
GENERATED_MARKERS = ["@generated", "generated from schemas/openapi.json"]
BUDGETS = {
    "react_component": (180, 250),
    "react_page": (240, 320),
    "api_route": (220, 320),
    "service": (260, 400),
    "core_security": (220, 320),
    "worker_handler": (260, 400),
    "worker_loop_store": (240, 360),
    "runtime_adapter": (220, 320),
    "sqlalchemy_model": (400, 650),
    "test": (350, 600),
    "default": (260, 400),
}


def load_config(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists() or config_path.suffix != ".json":
        return {}
    return json.loads(config_path.read_text())


def is_generated(path: Path) -> bool:
    try:
        head = path.read_text(errors="ignore")[:1000]
    except OSError:
        return False
    return any(marker in head for marker in GENERATED_MARKERS)


def budget_for(path: Path) -> tuple[str, int, int]:
    value = str(path)
    name = path.name
    if "/tests/" in value or name.startswith("test_") or name.endswith(".test.tsx") or name.endswith(".test.ts"):
        kind = "test"
    elif value.startswith("apps/desktop/src") and name.endswith("Page.tsx"):
        kind = "react_page"
    elif value.startswith("apps/desktop/src") and path.suffix == ".tsx":
        kind = "react_component"
    elif value.startswith("services/api/app/routes/"):
        kind = "api_route"
    elif value.startswith("services/api/app/services/"):
        kind = "service"
    elif value.startswith("services/shared/security/"):
        kind = "core_security"
    elif value.startswith("services/worker") and "/handlers/" in value:
        kind = "worker_handler"
    elif value.startswith("services/worker") and (name in {"main.py", "loop.py", "job_loop.py", "job_store.py"}):
        kind = "worker_loop_store"
    elif value.startswith("services/worker") and "/runtime/" in value:
        kind = "runtime_adapter"
    elif value.startswith("services/shared/db/models/"):
        kind = "sqlalchemy_model"
    else:
        kind = "default"
    soft, hard = BUDGETS[kind]
    return kind, soft, hard


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--fail-on-hard-limit", action="store_true")
    parser.add_argument("--json-output")
    parser.add_argument("roots", nargs="*", default=DEFAULT_ROOTS)
    args = parser.parse_args()
    config = load_config(args.config)
    generated_markers = list(config.get("generated_markers", GENERATED_MARKERS))
    budgets_config = config.get("budgets", {})
    if isinstance(budgets_config, dict):
        for key, value in budgets_config.items():
            if isinstance(value, dict) and "soft" in value and "hard" in value:
                BUDGETS[key] = (int(value["soft"]), int(value["hard"]))
    roots = args.roots
    if args.roots == DEFAULT_ROOTS and isinstance(config.get("roots"), list):
        roots = list(config["roots"])

    files: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    for root_name in roots:
        root = Path(root_name)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx", ".rs"}:
                continue
            if any(marker in path.read_text(errors="ignore")[:1000] for marker in generated_markers):
                continue
            loc = len(path.read_text(errors="ignore").splitlines())
            kind, soft, hard = budget_for(path)
            record = {"path": str(path), "kind": kind, "loc": loc, "soft_limit": soft, "hard_limit": hard}
            files.append(record)
            if loc > hard:
                violations.append({**record, "severity": "hard"})
            elif loc > soft:
                violations.append({**record, "severity": "soft"})

    result = {
        "budgets": {key: {"soft": value[0], "hard": value[1]} for key, value in BUDGETS.items()},
        "files_checked": len(files),
        "violations": violations,
    }
    text = json.dumps(result, sort_keys=True, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(text + "\n")
    print(text)
    return 1 if any(v["severity"] == "hard" for v in violations) else 0


if __name__ == "__main__":
    raise SystemExit(main())
