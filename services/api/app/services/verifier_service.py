from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.shared.db.models import AgentPackage


REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_VERIFIER_PATH = REPO_ROOT / "packages" / "agent-runtime" / "core" / "verifier.py"


@lru_cache(maxsize=1)
def runtime_verifier_module() -> Any:
    spec = importlib.util.spec_from_file_location("mib_agent_runtime_core_verifier", CORE_VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime verifier module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VerifierService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def verify_package_output(
        self,
        *,
        agent_package_id: str,
        output: Any,
        approve_fallback: bool = False,
    ) -> dict[str, Any]:
        package = self.session.get(AgentPackage, agent_package_id)
        if package is None:
            raise APIError(
                "AGENT_PACKAGE_NOT_FOUND",
                "AgentPackage does not exist.",
                status_code=404,
                details={"agent_package_id": agent_package_id},
            )
        contract = yaml.safe_load(package.contract_yaml)
        result = runtime_verifier_module().verify_router_output(
            output=output,
            contract=contract,
            approve_fallback=approve_fallback,
        )
        return {
            "agent_package_id": package.id,
            "agent_id": package.agent_id,
            "contract_sha256": package.contract_sha256,
            "verifier_status": result.verifier_status,
            "verifier_errors": result.verifier_errors,
            "fallback_required": result.fallback_required,
            "fallback_used": result.fallback_used,
        }
