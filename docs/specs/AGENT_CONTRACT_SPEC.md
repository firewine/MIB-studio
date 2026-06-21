# Agent Package / Contract 명세 (AGENT_CONTRACT_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [ARCHITECTURE](./ARCHITECTURE.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [SECURITY_SPEC](./SECURITY_SPEC.md)

---

## 18. Agent Package

최종 산출물은 모델 파일이 아니라 agent package다.

```yaml
agent_id: support_router.v1
agent_type: router
base_model: google/gemma-2b-it
adapter:
  path: adapter/
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  format: lora_adapter
input_schema: schemas/router_input.schema.json
output_schema: schemas/router_output.schema.json

route_catalog:
  schema_version: route_catalog.v1
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  routes:
    - route_id: finance_income
      description: Income report requests
      is_unsafe: false
      order: 0
    - route_id: human_review
      description: Escalate to a human reviewer
      is_unsafe: true
      order: 1

runtime:
  engine: transformers
  quantization: q4
  max_tokens: 256
  temperature: 0
  deterministic: true
  compatible_backends: [cuda]

verifiers:
  - name: json_parse
    config: {}
  - name: output_schema
    config: {}
  - name: route_allowed
    config:
      route_catalog_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  - name: confidence_threshold
    config:
      threshold: 0.65

fallback:
  enabled: true
  provider: openai_compatible
  model: gpt-4o-mini
  condition:
    type: confidence_lt
    threshold: 0.65

audit:
  log_input: false
  log_input_hash: true
  log_output: redacted
  redaction_policy: SECURITY_SPEC_19_6
  retention_days: 365

benchmark_report:
  path: benchmark/report.json
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

export_compatibility:
  supported_formats: [zip, docker]
  runtime_entrypoint: agents.run:app
```

Agent Package 구성:

```text
model adapter
input/output schema
route catalog snapshot
runtime config
verifiers
fallback policy
audit policy
benchmark report
export compatibility
M6 export manifest metadata
```

> **fallback 포지셔닝:** fallback(confidence<임계 → 대형 LLM)은 결함이 아니라 비용 최적화 기능이다. 벤치마크의 cost 비교는 fallback 호출 비용을 포함한 effective cost/task로 보고한다([EVAL_SPEC §17.1](./EVAL_SPEC.md)).
> **audit 보안(v0):** `log_output`은 **PII 마스킹 적용 후 저장**한다([SECURITY_SPEC §19.6](./SECURITY_SPEC.md) 정책 통과 필수). `log_input_hash`는 원문 미저장(해시만). v0 audit 저장소는 로컬 SQLite `audit_event`이며, OS 사용자 권한 + redaction + retention으로 보호한다. 별도 DB 암호화-at-rest, 중앙 접근통제, 컴플라이언스 audit은 [SECURITY_SPEC §19.8](./SECURITY_SPEC.md)의 Enterprise/v0.2+ 범위다.

---

## 18.1 agent_contract JSON Schema (v0 LOCK · draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "agent_id",
    "agent_type",
    "base_model",
    "adapter",
    "input_schema",
    "output_schema",
    "route_catalog",
    "runtime",
    "verifiers",
    "fallback",
    "audit",
    "benchmark_report",
    "export_compatibility"
  ],
  "additionalProperties": false,
  "properties": {
    "agent_id": { "type": "string", "pattern": "^[a-z0-9_]+\\.v[0-9]+$" },
    "agent_type": { "enum": ["router"] },
    "base_model": { "enum": ["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"] },
    "adapter": {
      "type": "object",
      "required": ["path", "sha256", "format"],
      "additionalProperties": false,
      "properties": {
        "path": { "type": "string", "pattern": "^adapter/" },
        "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "format": { "enum": ["lora_adapter", "mlx_lora_adapter"] }
      }
    },
    "input_schema": { "enum": ["schemas/router_input.schema.json"] },
    "output_schema": { "enum": ["schemas/router_output.schema.json"] },
    "route_catalog": {
      "type": "object",
      "required": ["schema_version", "sha256", "routes"],
      "additionalProperties": false,
      "properties": {
        "schema_version": { "enum": ["route_catalog.v1"] },
        "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "routes": {
          "type": "array",
          "minItems": 2,
          "maxItems": 12,
          "items": {
            "type": "object",
            "required": ["route_id", "description", "is_unsafe", "order"],
            "additionalProperties": false,
            "properties": {
              "route_id": { "type": "string", "pattern": "^[a-z0-9_]{1,64}$" },
              "description": { "type": "string", "minLength": 1, "maxLength": 2000 },
              "is_unsafe": { "type": "boolean" },
              "order": { "type": "integer", "minimum": 0 }
            }
          }
        }
      }
    },
    "runtime": {
      "type": "object",
      "required": ["engine", "max_tokens", "temperature", "deterministic", "compatible_backends"],
      "additionalProperties": false,
      "properties": {
        "engine": { "enum": ["vllm", "ollama", "llama.cpp", "transformers", "mlx_lm"] },
        "quantization": { "enum": ["q4", "q8", "bf16", "none"] },
        "max_tokens": { "type": "integer", "minimum": 1, "maximum": 4096 },
        "temperature": { "type": "number", "minimum": 0, "maximum": 2 },
        "deterministic": { "type": "boolean" },
        "compatible_backends": {
          "type": "array",
          "minItems": 1,
          "items": { "enum": ["cuda", "mlx", "cpu"] },
          "uniqueItems": true
        }
      }
    },
    "verifiers": {
      "type": "array",
      "minItems": 3,
      "items": {
        "type": "object",
        "required": ["name", "config"],
        "additionalProperties": false,
        "properties": {
          "name": { "enum": ["json_parse", "output_schema", "route_allowed", "confidence_threshold"] },
          "config": { "type": "object" }
        }
      }
    },
    "fallback": {
      "type": "object",
      "required": ["enabled", "provider", "condition"],
      "additionalProperties": false,
      "properties": {
        "enabled": { "type": "boolean" },
        "provider": { "enum": ["openai", "openai_compatible", "none"] },
        "model": { "type": "string" },
        "condition": {
          "type": "object",
          "required": ["type"],
          "additionalProperties": false,
          "properties": {
            "type": { "enum": ["confidence_lt", "verifier_failed", "disabled"] },
            "threshold": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        }
      }
    },
    "audit": {
      "type": "object",
      "required": ["log_input", "log_input_hash", "log_output", "redaction_policy", "retention_days"],
      "additionalProperties": false,
      "properties": {
        "log_input": { "enum": [false] },
        "log_input_hash": { "enum": [true] },
        "log_output": { "enum": ["redacted"] },
        "redaction_policy": { "enum": ["SECURITY_SPEC_19_6"] },
        "retention_days": { "type": "integer", "minimum": 365, "maximum": 3650 }
      }
    },
    "benchmark_report": {
      "type": "object",
      "required": ["path", "sha256"],
      "additionalProperties": false,
      "properties": {
        "path": { "type": "string", "pattern": "^benchmark/" },
        "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    },
    "export_compatibility": {
      "type": "object",
      "required": ["supported_formats", "runtime_entrypoint"],
      "additionalProperties": false,
      "properties": {
        "supported_formats": {
          "type": "array",
          "minItems": 1,
          "items": { "enum": ["zip", "docker"] },
          "uniqueItems": true
        },
        "runtime_entrypoint": { "enum": ["agents.run:app"] }
      }
    }
  }
}
```

- v0 `agent_type`/`base_model`은 위 enum으로 제한(Router + 2 base models). v0.2+에서 확장.
- `input_schema`/`output_schema`는 [PRESET_SPEC §15.4](./PRESET_SPEC.md) Router 스키마 경로를 가리킨다.
- v0 runtime/package contract는 위 required field를 모두 채워야 한다. 누락된 `adapter`, `route_catalog`, `verifiers`, `fallback`, `audit`, `benchmark_report`, `export_compatibility`는 package build 실패다.
- `route_catalog`는 ModelRun이 사용한 Dataset.route_snapshot_json의 immutable copy다. `route_catalog.sha256`은 Dataset.route_snapshot_sha256 및 AgentPackage.route_catalog_sha256과 같아야 한다. OpenAI-compatible endpoint가 plain string content를 router input으로 변환할 때 `allowed_routes`는 이 catalog의 route_id 순서를 사용한다.
- `route_allowed` verifier는 output.route가 `route_catalog.routes[].route_id` 안에 있는지 검사한다.
- `fallback.enabled=false`이면 `provider="none"`과 `condition.type="disabled"`를 사용한다.
- `benchmark_report.sha256`은 [EVAL_SPEC §17.5](./EVAL_SPEC.md)의 canonical report hash와 같아야 한다.
- `contract_sha256` canonicalization: parse `contract_yaml` to a JSON-compatible object, validate it against `schemas/agent_contract.schema.json`, serialize the parsed object with `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, then SHA256 the UTF-8 bytes. Raw YAML byte hashing is forbidden.
- M6 export artifact manifest is separate from this contract. `manifest_sha256` is produced by the export job after zip/Docker files are written and is stored in `ExportArtifact.manifest_sha256`; the package row remains immutable.
- **불변성/버전:** AgentPackage는 배포 단위로 불변이다. 계약(verifiers/fallback 포함) 변경 시 `contract_version`을 올린 새 AgentPackage 행을 생성하고 `contract_sha256`을 기록한다([ARCHITECTURE §24](./ARCHITECTURE.md)). audit는 배포된 contract_sha256으로 결정적 재현.
- AgentContract identifies `base_model` and adapter format, but base-model file materialization is owned by the M6 export manifest. Exported runtimes must not infer cache paths from AgentContract alone.

Exported runtime API:

```text
- Local Daemon playground endpoint: `POST /agent-packages/{id}/playground-runs`.
- Exported zip/Docker runtime endpoint: `POST /agents/{agent_id}/run`.
- `/agents/{agent_id}/run` request body must validate `input_schema`.
- `/agents/{agent_id}/run` response body is `NativeRunResponse` (below). `response.output` must validate `output_schema` and pass all contract `verifiers` unless `fallback_required=true`.
- Exported runtime must not contain BYO teacher API keys or local Daemon bearer tokens.
```

Native run request:

```json
{
  "text": "Route this customer request...",
  "allowed_routes": ["finance_income", "human_review"]
}
```

Native run response:

```json
{
  "agent_id": "support_router.v1",
  "contract_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "output": {
    "route": "finance_income",
    "task_type": "provide_advice",
    "requires_calculation": false,
    "requires_human_review": false,
    "confidence": 0.91
  },
  "verifier_status": "PASS",
  "verifier_errors": [],
  "fallback_required": false,
  "fallback_used": false
}
```

Native response rules:

```text
- `output` is the only field validated against `output_schema`.
- `verifier_status=PASS` requires `output_schema`, `route_allowed`, and `confidence_threshold` to pass.
- If a verifier fails and fallback is disabled or not approved/configured, return `fallback_required=true`, `fallback_used=false`, and 409 `FALLBACK_CREDENTIAL_REQUIRED` when fallback env is missing.
- Native response must never expose prompt text, raw model logits, API keys, local model cache paths, or local daemon tokens.
```

Base model materialization:

```text
- Exported zip/Docker runtimes do not bundle base-model weights in v0.
- Exported runtimes do not download HF files at startup or request time.
- `manifest.json.base_model` points to an external strict model cache via `MIB_MODEL_CACHE_DIR` and lists every required base-model file hash.
- Startup fails before serving requests if the required cache subdir or any required file hash is missing.
- Docker images mount the cache read-only; zip runtimes receive the same path through `MIB_MODEL_CACHE_DIR`.
```

### 18.2 OpenAI-compatible exported endpoint (v0 LOCK)

The exported zip/Docker runtime must expose both the native endpoint and a non-streaming OpenAI-compatible Chat Completions endpoint. This endpoint exists only in exported runtime, never in the Local Daemon.

```text
POST /v1/chat/completions
Authorization: Bearer $MIB_RUNTIME_BEARER_TOKEN
Content-Type: application/json
```

Runtime bearer rules:

```text
- Exported runtime has no dev-auth bypass.
- Process startup must fail before binding a port if `MIB_RUNTIME_BEARER_TOKEN` is missing, empty, or shorter than 32 characters.
- Token comparison uses constant-time comparison.
- Missing Authorization header returns 401 `AUTH_REQUIRED`.
- Invalid bearer token returns 401 `AUTH_INVALID`.
- Required tests: `test_exported_runtime_refuses_missing_token_env`, `test_exported_runtime_rejects_short_token_env`, `test_exported_runtime_auth_required`, `test_exported_runtime_auth_invalid`.
```

Request contract:

```json
{
  "model": "support_router.v1",
  "messages": [
    { "role": "user", "content": "Route this customer request..." }
  ],
  "temperature": 0,
  "stream": false
}
```

Mapping rules:

```text
- `stream=true` returns 400 `STREAMING_NOT_SUPPORTED_V0`.
- `model` must equal `agent_id` or `agent_id:*`; unknown model returns 404 `AGENT_NOT_FOUND`.
- The last user message is the only input source.
- If the last user content parses as JSON with `text` and optional `allowed_routes`, use it as router_input.
- Otherwise map string content to `{text: content, allowed_routes: contract route ids}`.
- The native `output` object, not the full `NativeRunResponse` wrapper, is serialized as a compact JSON string in `choices[0].message.content`.
- `temperature` is accepted for client compatibility but v0 runtime remains deterministic and uses contract.runtime.temperature.
```

Response contract:

```json
{
  "id": "chatcmpl_01J...",
  "object": "chat.completion",
  "created": 1782000000,
  "model": "support_router.v1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\"route\":\"billing\",\"task_type\":\"provide_advice\",\"requires_calculation\":false,\"requires_human_review\":false,\"confidence\":0.91}"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

Fallback credential behavior:

```text
- Local Playground resolves fallback credentials from OS keychain by contract.fallback.provider after explicit user approval.
- Exported runtime never stores API keys in the package.
- If fallback.enabled=true and fallback is triggered, exported runtime reads `MIB_FALLBACK_API_KEY` and `MIB_FALLBACK_BASE_URL` at process start or request time.
- Missing fallback env returns 409 `FALLBACK_CREDENTIAL_REQUIRED`; it must not silently call the local daemon or disable verifiers.
- Fallback egress must use the same SECURITY_SPEC §19.10 allowlist, DNS rebinding defense, private-IP denial, redirect denial, `trust_env=false`, timeout, and redaction rules as teacher egress.
- Native `/agents/{agent_id}/run` and `/v1/chat/completions` share the same verifier/fallback/audit implementation.
- Required tests: `test_fallback_redirect_to_private_ip_denied`, `test_fallback_uses_trust_env_false`, `test_fallback_missing_env_returns_409`, `test_fallback_no_secret_in_audit`.
```
