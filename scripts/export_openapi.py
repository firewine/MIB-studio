#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-app-import",
        action="store_true",
        help="Fail when optional runtime dependencies are unavailable instead of falling back to schema-only validation.",
    )
    args = parser.parse_args()

    seed = Path("schemas/openapi.json")
    data = json.loads(seed.read_text())
    if "openapi" not in data or "paths" not in data:
        raise SystemExit("schemas/openapi.json is not an OpenAPI seed")

    source = str(seed)
    app_path = Path("services/api/app/main.py")
    if app_path.exists():
        sys.path.insert(0, str(Path.cwd()))
        try:
            from services.api.app.main import app  # type: ignore
        except ModuleNotFoundError as exc:
            missing_name = exc.name or ""
            if args.strict_app_import or missing_name.startswith("services"):
                raise
            source = f"{seed}:schema-only-missing-dependency:{missing_name}"
        else:
            exported = app.openapi()
            if canonical_json(exported) != canonical_json(data):
                raise SystemExit(
                    "OpenAPI drift detected: FastAPI app.openapi() differs from schemas/openapi.json. "
                    "Regenerate schemas/openapi.json and apps/desktop/src/lib/generated.ts in the same patch."
                )
            source = "services.api.app.main:app.openapi"

    print(json.dumps({"status": "ok", "source": source, "paths": len(data.get("paths", {}))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
