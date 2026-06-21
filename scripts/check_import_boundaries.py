#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RULES = [
    ("services/api/app/routes", "services.worker"),
    ("services/api/app/routes", "services.shared.db.models"),
    ("services/api/app/routes", "services.shared.db.repositories"),
    ("services/api/app/routes", "services.shared.db.session"),
    ("services/api/app/routes", "packages"),
    ("services/api/app/services", "services.api.app.routes"),
    ("services/api/app/services", "services.worker"),
    ("services/api/app/services", "fastapi"),
    ("services/api/app/services", "starlette"),
    ("services/worker", "services.api.app.services"),
    ("services/worker", "services.api.app.routes"),
    ("services/shared/db/models", "services.api"),
    ("services/shared/db/models", "services.worker"),
    ("services/shared/db/models", "fastapi"),
    ("services/shared/db/models", "tauri"),
    ("services/shared", "services.api"),
    ("services/shared", "services.worker"),
    ("packages", "services.api"),
    ("packages", "services.worker"),
    ("packages", "fastapi"),
    ("packages", "tauri"),
]

TS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:type\s+)?(?:[^'\"]+\s+from\s+)?|export\s+(?:type\s+)?[^'\"]+\s+from\s+|import\()\s*['\"]([^'\"]+)['\"]"
)


def load_rules(path: str | None) -> list[tuple[str, str]]:
    if not path:
        return RULES
    rules_path = Path(path)
    if not rules_path.exists() or rules_path.suffix != ".json":
        return RULES
    data = json.loads(rules_path.read_text())
    return [(str(a), str(b)) for a, b in data.get("import_boundaries", RULES)]


def imports_for(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return {"<syntax-error>"}
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
            if node.level:
                found.add("." * node.level + (node.module or ""))
    return found


def ts_imports_for(path: Path) -> set[str]:
    return set(TS_IMPORT_RE.findall(path.read_text(errors="ignore")))


def feature_name(path: Path) -> str | None:
    parts = path.parts
    if "features" not in parts:
        return None
    index = parts.index("features")
    if index + 1 >= len(parts):
        return None
    return parts[index + 1]


def frontend_layer(path: Path) -> str | None:
    parts = path.parts
    if "pages" in parts:
        return "pages"
    if "components" in parts:
        return "components"
    if "hooks" in parts:
        return "hooks"
    if "schemas" in parts:
        return "schemas"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules")
    parser.add_argument("--json-output")
    args = parser.parse_args()
    rules = load_rules(args.rules)

    violations: list[dict[str, str]] = []
    for root_text, forbidden in rules:
        root = Path(root_text)
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            for module in imports_for(path):
                if str(path).startswith("packages/agent-runtime/templates/") and forbidden == "fastapi":
                    continue
                if module == forbidden or module.startswith(forbidden + "."):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": f"{root_text} must not import {forbidden}",
                    })

    frontend_root = Path("apps/desktop/src/features")
    if frontend_root.exists():
        for path in frontend_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            owner = feature_name(path)
            layer = frontend_layer(path)
            for module in ts_imports_for(path):
                if module.startswith("../"):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": "feature modules must import through feature-local paths or src/lib aliases, not cross-feature relative parents",
                    })
                if "/features/" in module:
                    imported = module.split("/features/", 1)[1].split("/", 1)[0]
                    if owner and imported != owner and imported != "shell":
                        violations.append({
                            "path": str(path),
                            "forbidden_import": module,
                            "rule": "frontend features must not import another feature directly except shell",
                        })
                if layer == "components" and ("/lib/api" in module or "/pages" in module or module.endswith("/api")):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": "feature components must not import pages or API clients directly",
                    })
                if layer == "hooks" and ("/components" in module or "/pages" in module):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": "feature hooks must not import pages/components",
                    })
                if layer == "schemas" and ("/components" in module or "/pages" in module or "/hooks" in module):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": "feature schemas must not import UI or hooks",
                    })

    lib_api_root = Path("apps/desktop/src/lib")
    if lib_api_root.exists():
        for path in lib_api_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            for module in ts_imports_for(path):
                if "/features/" in module or module.startswith("../features"):
                    violations.append({
                        "path": str(path),
                        "forbidden_import": module,
                        "rule": "lib/api and shared lib code must not import feature modules",
                    })

    result = {"rules": [f"{a} !-> {b}" for a, b in rules], "violations": violations}
    text = json.dumps(result, sort_keys=True, indent=2)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(text + "\n")
    print(text)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
