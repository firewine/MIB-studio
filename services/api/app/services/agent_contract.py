from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator, ValidationError

from services.api.app.schemas.agent_package import FallbackConfigInput
from services.shared.db.models import Benchmark, Dataset, ModelRun
from services.shared.db.repositories.dataset_store import canonical_json, sha256_text


REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_SCHEMA_PATH = REPO_ROOT / "schemas" / "agent_contract.schema.json"


class AgentContractError(ValueError):
    pass


def slugify_agent(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:48] or "router_agent"


def contract_sha256(contract_yaml: str) -> str:
    parsed = yaml.safe_load(contract_yaml)
    validate_contract(parsed)
    return sha256_text(canonical_json(parsed))


def validate_contract(contract: Any) -> None:
    schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        Draft7Validator(schema).validate(contract)
    except ValidationError as exc:
        raise AgentContractError(f"agent contract schema validation failed: {exc.message}") from exc


def build_contract_yaml(
    *,
    agent_id: str,
    model_run: ModelRun,
    dataset: Dataset,
    benchmark: Benchmark,
    fallback: FallbackConfigInput,
) -> tuple[str, str]:
    contract = _contract_object(
        agent_id=agent_id,
        model_run=model_run,
        dataset=dataset,
        benchmark=benchmark,
        fallback=fallback,
    )
    validate_contract(contract)
    contract_yaml = yaml.safe_dump(contract, sort_keys=False, allow_unicode=False)
    return contract_yaml, contract_sha256(contract_yaml)


def _contract_object(
    *,
    agent_id: str,
    model_run: ModelRun,
    dataset: Dataset,
    benchmark: Benchmark,
    fallback: FallbackConfigInput,
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "agent_type": "router",
        "base_model": model_run.base_model,
        "adapter": {
            "path": f"adapter/{model_run.id}",
            "sha256": model_run.adapter_sha256,
            "format": "mlx_lora_adapter" if model_run.backend == "mlx" else "lora_adapter",
        },
        "input_schema": "schemas/router_input.schema.json",
        "output_schema": "schemas/router_output.schema.json",
        "route_catalog": _route_catalog(dataset),
        "runtime": _runtime(model_run),
        "verifiers": _verifiers(dataset.route_snapshot_sha256),
        "fallback": fallback.model_dump(exclude_none=True),
        "audit": {
            "log_input": False,
            "log_input_hash": True,
            "log_output": "redacted",
            "redaction_policy": "SECURITY_SPEC_19_6",
            "retention_days": 365,
        },
        "benchmark_report": {
            "path": f"benchmark/{benchmark.id}/benchmark_report.json",
            "sha256": benchmark.report_sha256,
        },
        "export_compatibility": {
            "supported_formats": ["zip"] if model_run.backend == "mlx" else ["zip", "docker"],
            "runtime_entrypoint": "agents.run:app",
        },
    }


def _route_catalog(dataset: Dataset) -> dict[str, Any]:
    routes = []
    for index, route in enumerate(json.loads(dataset.route_snapshot_json)):
        routes.append(
            {
                "route_id": route["route_id"],
                "description": route["description"],
                "is_unsafe": bool(route["is_unsafe"]),
                "order": index,
            }
        )
    return {"schema_version": "route_catalog.v1", "sha256": dataset.route_snapshot_sha256, "routes": routes}


def _runtime(model_run: ModelRun) -> dict[str, Any]:
    engine = "mlx_lm" if model_run.backend == "mlx" else "transformers"
    return {
        "engine": engine,
        "quantization": "q4",
        "max_tokens": 512,
        "temperature": 0,
        "deterministic": True,
        "compatible_backends": [model_run.backend],
    }


def _verifiers(route_catalog_sha256: str) -> list[dict[str, Any]]:
    return [
        {"name": "json_parse", "config": {}},
        {"name": "output_schema", "config": {"schema": "schemas/router_output.schema.json"}},
        {"name": "route_allowed", "config": {"route_catalog_sha256": route_catalog_sha256}},
        {"name": "confidence_threshold", "config": {"threshold": 0.0}},
    ]
