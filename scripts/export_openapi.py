#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def main() -> int:
    seed = Path("schemas/openapi.json")
    data = json.loads(seed.read_text())
    if "openapi" not in data or "paths" not in data:
        raise SystemExit("schemas/openapi.json is not an OpenAPI seed")

    app_path = Path("services/api/app/main.py")
    if app_path.exists():
        sys.path.insert(0, str(Path.cwd()))
        from services.api.app.main import app  # type: ignore

        exported = app.openapi()
        if canonical_json(exported) != canonical_json(data):
            raise SystemExit(
                "OpenAPI drift detected: FastAPI app.openapi() differs from schemas/openapi.json. "
                "Regenerate schemas/openapi.json and apps/desktop/src/lib/generated.ts in the same patch."
            )
        source = "services.api.app.main:app.openapi"
    else:
        source = str(seed)

    print(json.dumps({"status": "ok", "source": source, "paths": len(data.get("paths", {}))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
