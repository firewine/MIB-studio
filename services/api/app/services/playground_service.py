from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.playground import PlaygroundRunRequest, PlaygroundRunResponse
from services.api.app.services.verifier_service import VerifierService
from services.shared.db.models import AgentPackage, AuditEvent, Credential, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, new_id, sha256_text


REPO_ROOT = Path(__file__).resolve().parents[4]
ROUTER_INFERENCE_PATH = REPO_ROOT / "packages" / "agent-runtime" / "core" / "router_inference.py"


@lru_cache(maxsize=1)
def runtime_router_module() -> Any:
    spec = importlib.util.spec_from_file_location("mib_agent_runtime_core_router_inference", ROUTER_INFERENCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime router inference module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PlaygroundService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run_playground(self, *, agent_package_id: str, payload: PlaygroundRunRequest) -> PlaygroundRunResponse:
        package = self.session.get(AgentPackage, agent_package_id)
        if package is None:
            raise APIError(
                "AGENT_PACKAGE_NOT_FOUND",
                "AgentPackage does not exist.",
                status_code=404,
                details={"agent_package_id": agent_package_id},
            )

        model_run = self.session.get(ModelRun, package.model_run_id)
        if model_run is None:
            raise APIError(
                "MODEL_RUN_NOT_FOUND",
                "AgentPackage model run does not exist.",
                status_code=409,
                details={"agent_package_id": package.id, "model_run_id": package.model_run_id},
            )

        contract = yaml.safe_load(package.contract_yaml)
        output = runtime_router_module().run_router_inference(
            input_payload=payload.input,
            contract=contract,
            adapter=_adapter_metadata(model_run),
        )
        verifier = VerifierService(self.session)
        verification = verifier.verify_package_output(
            agent_package_id=package.id,
            output=output,
            approve_fallback=False,
        )
        fallback_decision = _fallback_decision(verification, approve_fallback=payload.approve_fallback)

        if payload.approve_fallback and verification["fallback_required"]:
            credential = self._active_credential_for(contract)
            if credential is None:
                audit_id = self._audit_run(
                    package=package,
                    model_run=model_run,
                    contract=contract,
                    input_payload=payload.input,
                    output=output,
                    verification=verification,
                    fallback_decision="missing_credential",
                )
                self.session.commit()
                raise APIError(
                    "FALLBACK_CREDENTIAL_REQUIRED",
                    "Fallback credential is required before approved fallback can run.",
                    status_code=409,
                    details={
                        "agent_package_id": package.id,
                        "provider": _fallback_provider(contract),
                        "audit_event_id": audit_id,
                    },
                )
            verification = verifier.verify_package_output(
                agent_package_id=package.id,
                output=output,
                approve_fallback=True,
            )
            fallback_decision = "approved_credential_available"

        audit_id = self._audit_run(
            package=package,
            model_run=model_run,
            contract=contract,
            input_payload=payload.input,
            output=output,
            verification=verification,
            fallback_decision=fallback_decision,
        )
        return PlaygroundRunResponse(output=output, audit_event_id=audit_id, **_response_verification(verification))

    def _active_credential_for(self, contract: dict[str, Any]) -> Credential | None:
        provider = _fallback_provider(contract)
        if provider not in {"openai", "openai_compatible"}:
            return None
        return self.session.scalar(
            select(Credential).where(
                Credential.provider == provider,
                Credential.is_revoked == 0,
            )
        )

    def _audit_run(
        self,
        *,
        package: AgentPackage,
        model_run: ModelRun,
        contract: dict[str, Any],
        input_payload: dict[str, Any],
        output: dict[str, Any],
        verification: dict[str, Any],
        fallback_decision: str,
    ) -> str:
        now = utc_now()
        audit_id = new_id()
        details = {
            "agent_package_id": package.id,
            "agent_id": package.agent_id,
            "contract_sha256": package.contract_sha256,
            "model_run_id": model_run.id,
            "adapter_sha256": model_run.adapter_sha256,
            "runtime_engine": contract.get("runtime", {}).get("engine"),
            "input_sha256": sha256_text(canonical_json(input_payload)),
            "output_route": output.get("route"),
            "verifier_status": verification["verifier_status"],
            "verifier_errors_count": len(verification["verifier_errors"]),
            "fallback_decision": fallback_decision,
            "fallback_provider": _fallback_provider(contract),
            "fallback_required": verification["fallback_required"],
            "fallback_used": verification["fallback_used"],
        }
        retention_until = (datetime.now(UTC) + timedelta(days=365)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self.session.add(
            AuditEvent(
                id=audit_id,
                ts=now,
                event_type="agent_run",
                resource_type="agent_package",
                resource_id=package.id,
                action="playground_run",
                policy_version="agent_contract.v0.3",
                details_json=json.dumps(details, sort_keys=True, separators=(",", ":")),
                trace_id=None,
                retention_until=retention_until,
                contract_sha256=package.contract_sha256,
                created_at=now,
            )
        )
        self.session.flush()
        return audit_id


def _adapter_metadata(model_run: ModelRun) -> dict[str, Any]:
    return {
        "model_run_id": model_run.id,
        "adapter_path": model_run.adapter_path,
        "adapter_sha256": model_run.adapter_sha256,
        "backend": model_run.backend,
        "base_model": model_run.base_model,
    }


def _fallback_provider(contract: dict[str, Any]) -> str:
    fallback = contract.get("fallback", {})
    if not isinstance(fallback, dict):
        return "none"
    provider = fallback.get("provider")
    return provider if isinstance(provider, str) else "none"


def _fallback_decision(verification: dict[str, Any], *, approve_fallback: bool) -> str:
    if not verification["fallback_required"]:
        return "not_required"
    if approve_fallback:
        return "approved_pending_credential"
    return "requires_user_approval"


def _response_verification(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_status": verification["verifier_status"],
        "verifier_errors": verification["verifier_errors"],
        "fallback_required": verification["fallback_required"],
        "fallback_used": verification["fallback_used"],
    }


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
