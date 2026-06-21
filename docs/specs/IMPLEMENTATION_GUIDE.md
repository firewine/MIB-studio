# 구현 가이드 (IMPLEMENTATION_GUIDE) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)  
> 상태: v0.3 · Junior-buildable Implementation Guide  
> 목적: 이 문서는 주니어 개발자가 Dev Plan과 specs만 보고 v0 앱을 구현할 수 있도록 **작업 순서, 파일 책임, DTO, 테스트, 완료 기준**을 한곳에 모은다.  
> 관련: [ARCHITECTURE](./ARCHITECTURE.md) · [DEV_ENVIRONMENT_SPEC](./DEV_ENVIRONMENT_SPEC.md) · [PRESET_SPEC](./PRESET_SPEC.md) · [SECURITY_SPEC](./SECURITY_SPEC.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md)

---

## 0. 이 문서를 읽는 순서

구현자는 아래 순서로만 진행한다.

```text
1. Dev Plan §22/§33/§34로 현재 phase와 acceptance criteria 확인
2. IMPLEMENTATION_GUIDE에서 해당 phase의 작업 티켓 확인
3. 관련 spec으로 세부 계약 확인
4. 테스트를 먼저 작성하거나 최소 smoke script를 만든 뒤 구현
5. phase acceptance criteria를 모두 통과해야 Done
```

절대 해석으로 때우지 않는다. 명세가 비어 있으면 구현을 시작하지 말고 `docs/`를 먼저 보강한다.

---

## 0.1 바이브 코딩 핸드오프 규칙

코딩 에이전트 또는 주니어 개발자에게 작업을 넘길 때는 아래 입력 묶음만 기준으로 구현한다.

```text
1. docs/foundation/MIB_Studio_Dev_Plan_v0.3.md §22, §33, §34
2. docs/specs/IMPLEMENTATION_GUIDE.md의 현재 phase 티켓
3. docs/specs/ARCHITECTURE.md의 DB/API/Job/Artifact 계약
4. schemas/openapi.json과 apps/desktop/src/lib/generated.ts
5. 현재 phase에서 직접 참조된 spec, fixture, schema
```

핸드오프 프롬프트에는 반드시 다음 제약을 포함한다.

```text
- v0는 Router만 구현한다. Extractor, Rule Selector, Summarizer, QA는 disabled reference 외에 구현하지 않는다.
- base model은 presets/model_catalog.yaml의 locked strict catalog만 사용한다.
- benchmark 숫자는 eval runner가 만든 report artifact만 표시한다. mockup/example 숫자를 claim으로 쓰지 않는다.
- API/DTO/DB 변경은 OpenAPI, generated.ts, Alembic 모델, repository, test fixture를 같은 ticket에서 함께 갱신한다.
- 파일 책임은 이 문서 §3/§4/§13을 따른다. god file, cross-layer import, 임의 전역 상태를 만들지 않는다.
- 문서가 충돌하면 코드를 작성하지 말고 docs/spec/schema를 먼저 패치한 뒤 다시 구현한다.
- 개발 환경은 .venv + pinned requirements + pnpm 9 + Rust toolchain 파일을 기준으로 재현한다.
```

작업 완료 보고는 아래 형식으로 남긴다.

```text
Implemented:
- 변경 파일
- 계약 변경 여부(API/DB/schema/env)
- 실행한 검증 명령
- 남은 blocker 또는 없음
```

---

## 1. v0 앱의 완성된 사용자 흐름

v0에서 사용자가 실제로 할 수 있어야 하는 최소 흐름은 아래 하나다.

```text
1. 앱 실행
2. Hardware Doctor 실행
3. Router 프로젝트 생성
4. route taxonomy 2~12개 입력
5. 예시 20개 입력 또는 JSONL import
6. training dataset JSONL 생성
7. BYO OpenAI-compatible key 저장
8. Teacher Packet Preview 확인 후 synthetic data 생성
9. generated examples 검수/승인
10. CUDA 또는 MLX training job 실행
11. adapter 생성
12. frozen eval set으로 benchmark 실행
13. benchmark report 확인
14. Playground에서 Router 입력 테스트
15. agent package zip 또는 Docker export
```

이 흐름 중 현재 phase 범위 밖인 단계는 UI에 disabled 상태로 표시하고, 실제 동작은 구현하지 않는다.

---

## 2. 구현 원칙

```text
- 문서가 계약이고 코드는 그 구현이다.
- v0는 Router만 구현한다. Extractor/Rule Selector 화면이나 API는 만들지 않는다.
- Summarizer/QA는 v0 범위가 아니다. 해당 preset, screen, API, metric은 v0.2+ ADR이 생기기 전까지 구현하지 않는다.
- 모든 장시간 작업은 Job으로 실행한다. HTTP 요청 안에서 training/eval을 직접 돌리지 않는다.
- DB는 SQLite + Alembic 기준이다. 임의 JSON 파일만으로 상태를 관리하지 않는다.
- 파일 artifact는 temp write → fsync → rename 후 DB 성공 상태를 기록한다.
- API 키와 bearer token은 DB/로그에 저장하지 않는다.
- 로컬 Project DB는 사용자 예시를 저장할 수 있으므로 민감 데이터가 포함될 수 있다.
- raw examples/PII는 JobEvent, AuditEvent, crash log, teacher egress에 마스킹/승인 없이 노출하지 않는다.
- benchmark 숫자는 eval runner 산출물만 신뢰한다. 수기 입력 금지.
```

---

## 3. 저장소 구조와 파일 책임

아래 구조를 기준으로 만든다. 이름은 변경하지 않는다.

```text
mib-studio/
  apps/
    desktop/
      src/
        app/
        components/
        features/
          shell/
          dashboard/
          projects/
          presets/
          datasets/
          hardware/
          jobs/
          teacher/
          training/
          benchmark/
          playground/
          export/
          settings/
        lib/
          api.ts
          sse.ts
          errors.ts
          generated.ts
          types.ts
  services/
    shared/
      db/
        base.py
        session.py
        seed.py
        migrations/
        models/
          __init__.py
          preset.py
          project.py
          dataset.py
          eval.py
          hardware.py
          credential.py
          job.py
          training.py
          package.py
          audit.py
        repositories/
          idempotency_store.py
          job_store.py
          dataset_store.py
          training_store.py
          benchmark_store.py
          export_store.py
          hardware_store.py
      security/
        auth.py
        origin.py
        redaction.py
        egress_policy.py
        teacher_client.py
        credentials.py
      utils/
        hashing.py
        json_canonical.py
        ids.py
        time.py
    api/
      app/
        main.py
        core/
          config.py
          errors.py
        routes/
          projects.py
          presets.py
          datasets.py
          jobs.py
          hardware.py
          credentials.py
          eval_runs.py
          export.py
        schemas/
          common.py
          projects.py
          datasets.py
          jobs.py
          hardware.py
          credentials.py
        services/
          project_service.py
          preset_service.py
          dataset_service.py
          job_service.py
          hardware_service.py
          credential_service.py
          artifact_store.py
    worker/
      worker/
        main.py
        job_loop.py
        events.py
        cancellation.py
        handlers/
          dataset_gen.py
          hardware_scan.py
          train_cuda.py
          train_mlx.py
          eval_run.py
          benchmark.py
          export.py
        runtime/
          llamafactory.py
          mlx_lm.py
          local_inference.py
        utils/
          artifacts.py
          jsonl.py
  packages/
    preset-engine/
    agent-contract/
    eval-metrics/
    dataset-builder/
    hardware-doctor/
  presets/
    router.basic.v1.yaml
    model_catalog.yaml
  schemas/
    agent_contract.schema.json
    router_input.schema.json
    router_output.schema.json
    routing_rules.schema.json
    benchmark_report.schema.json
    export_manifest.schema.json
    openapi.json
  scripts/
    bootstrap_dev.sh
    bootstrap_dev.ps1
    verify_model_catalog.py
    fill_model_catalog.py
    export_openapi.py
    check_file_size.py
    check_import_boundaries.py
    scan_export_artifact.py
  prompts/
    router.prompt_only.v1.txt
  rules/
    router.routing_rules.v1.yaml
    code_shape.json
  package.json
  pnpm-lock.yaml
  requirements.txt
  requirements-mlx.txt
  requirements-dev.txt
  .python-version
  .node-version
  rust-toolchain.toml
  .env.example
  .vscode/
    settings.json
    extensions.json
    tasks.json
    launch.json
```

책임 분리:

| 경로 | 책임 |
|---|---|
| `apps/desktop` | UI, API client, SSE 구독, form validation |
| `services/api` | FastAPI, auth, DB transaction, route handlers |
| `services/shared/db` | SQLAlchemy models, migrations, DB session, repositories. API와 Worker가 함께 사용하되 FastAPI/Tauri에 의존하지 않음 |
| `services/shared/security` | auth, host/origin, egress policy, redaction, credential storage. 단일 `security.py` 금지 |
| `services/worker` | Job claim loop, long-running work, artifact write. API route/service import 금지 |
| `packages/*` | 순수 로직. UI/API/DB에 직접 의존하지 않는다 |
| `presets/` | 제품 자산. versioned immutable |
| `schemas/` | JSON Schema 계약. verifier와 UI validation에서 같이 사용 |

### 3.1 Code Generation Guardrails (God File 금지)

Codex, 주니어 개발자, sub-agent 모두 코드 생성 시 아래 규칙을 따른다.

```text
- 새 코드를 만들기 전에 반드시 layer와 owner file을 정한다.
- 기존 패턴이 있으면 그 패턴을 따른다. 새 패턴은 ADR 또는 spec 변경 없이 만들지 않는다.
- 한 파일은 한 책임만 가진다. 여러 책임이 섞이면 파일을 나눈다.
- "helpers.py", "utils.ts", "common.py" 같은 dumping ground를 만들지 않는다.
- route/component/model 파일에 business logic을 몰아넣지 않는다.
- 생성 파일이 커질 조짐이 보이면 먼저 하위 module을 설계한다.
```

God file 기준:

| 파일 유형 | Soft limit | Hard limit | 분리 기준 |
|---|---:|---:|---|
| React component | 180 LOC | 250 LOC | form/state/API/subcomponent 분리 |
| React feature page | 240 LOC | 320 LOC | `components/`, `hooks/`, `schemas/`로 분리 |
| API route module | 220 LOC | 320 LOC | service/schema/dependency로 분리 |
| Service module | 260 LOC | 400 LOC | command/query/helper service로 분리 |
| Core/security module | 220 LOC | 320 LOC | auth/origin/egress/redaction/credential 분리 |
| Worker handler | 260 LOC | 400 LOC | parser/artifact/runtime adapter 분리 |
| Worker loop/store | 240 LOC | 360 LOC | claim/reconcile/event writer 분리 |
| Runtime adapter | 220 LOC | 320 LOC | config builder/log parser/process runner 분리 |
| SQLAlchemy model file | 400 LOC | 650 LOC | domain별 model module 분리 |
| Test file | 350 LOC | 600 LOC | fixture/helper/feature별 분리 |
| Alembic migration | 예외 | 예외 | generated DDL이라 god-file 규칙 제외 |
| generated OpenAPI/types | 예외 | 예외 | generated marker 필요 |

Hard limit 초과 파일은 PR에서 P1 blocking issue다. 예외는 `generated` 또는 migration 파일만 허용한다.

### 3.2 Layer Pattern Contract

Backend import 방향:

```text
routes -> schemas + services
services -> services/shared/db + services/shared/security + packages
worker job_loop/handlers -> services/shared/db/repositories/{job_store,dataset_store,training_store,benchmark_store,export_store,hardware_store} + worker runtime/utils + packages
packages -> no dependency on services/api, services/worker, FastAPI, Tauri
packages/agent-runtime/templates -> exported runtime template may import FastAPI, but must not import local services/api, services/worker, or Tauri
services/shared/db/models -> no dependency on routes/services/worker/FastAPI/Tauri
services/shared/security -> no dependency on routes/services/worker
```

Frontend import 방향:

```text
features/{feature}/pages -> feature components/hooks + lib/api
features/{feature}/components -> feature hooks/types only
features/{feature}/hooks -> lib/api + feature schemas
lib/api -> generated/shared DTO types only
components/ -> design-system-level reusable UI only
```

Frontend import path 규칙:

```text
- features 내부에서는 `../` parent-relative import를 쓰지 않는다.
- 같은 폴더의 sibling만 `./...`로 import한다.
- feature 내부 하위 폴더 이동은 `@/features/{feature}/...` alias를 사용한다.
- feature 간 import는 `@/features/shell/...` 예외만 허용한다.
- `apps/desktop/src/lib/*`는 `features/*`를 import하지 않는다.
```

Pattern per layer:

| Layer | Pattern | 금지 |
|---|---|---|
| FastAPI route | thin controller: parse DTO → call service → map response | DB query, file IO, training logic |
| Service | transaction boundary + business invariant | HTTP request/response objects |
| Worker handler | orchestration + JobEvent + artifact handoff | FastAPI dependency, UI concern |
| Runtime adapter | one backend wrapper per file | direct DB writes |
| React page | data composition + layout | raw fetch, large inline form logic |
| React hook | API/SSE state | rendering large JSX |
| Package | pure domain logic | DB/session/global app config |

Allowed shared names:

```text
- `schemas/common.py` may contain only DTO base classes, pagination, and error response types.
- `worker/utils/` may contain only worker-local artifact/jsonl helpers.
- `services/shared/utils/` may contain pure hashing, canonical JSON, ids, and time helpers.
- Any new `common`, `utils`, or `helpers` file must list its allowed symbol categories at the top of the file.
```

### 3.3 Code Review Checks for Pattern Consistency

Every non-trivial PR must answer:

```text
1. Which existing pattern does this follow?
2. Which layer owns this logic?
3. Are any files over the soft limit? If yes, why is it acceptable?
4. Are there new cross-layer imports? If yes, why are they allowed?
5. Could this be split into route/service/schema/handler/hook/component?
6. Did tests land next to the owning layer?
```

---

## 4. Day-0 Bootstrap

M1 구현 전에 반드시 끝낸다.

개발환경은 [DEV_ENVIRONMENT_SPEC §36](./DEV_ENVIRONMENT_SPEC.md)을 따른다. M1~M5 기본 개발은 Docker가 아니라 repo-local `.venv`다.

### 4.1 생성 파일

```text
presets/router.basic.v1.yaml
presets/model_catalog.yaml
prompts/router.prompt_only.v1.txt
rules/router.routing_rules.v1.yaml
schemas/router_input.schema.json
schemas/router_output.schema.json
schemas/routing_rules.schema.json
schemas/agent_contract.schema.json
schemas/benchmark_report.schema.json
schemas/export_manifest.schema.json
schemas/openapi.json
apps/desktop/src/lib/generated.ts
services/shared/db/migrations/env.py
services/shared/db/migrations/versions/0001_initial.py
.python-version
.node-version
rust-toolchain.toml
requirements.txt
requirements-mlx.txt
requirements-dev.txt
package.json
pnpm-lock.yaml
.env.example
.vscode/settings.json
.vscode/extensions.json
.vscode/tasks.json
.vscode/launch.json
.github/workflows/security.yml
scripts/verify_model_catalog.py
scripts/fill_model_catalog.py
scripts/export_openapi.py
scripts/check_file_size.py
scripts/check_import_boundaries.py
scripts/scan_export_artifact.py
scripts/bootstrap_dev.sh
scripts/bootstrap_dev.ps1
rules/code_shape.json
examples/fixtures/router_20.jsonl
examples/fixtures/gold_eval.finance.v1.jsonl
examples/fixtures/llamafactory_config.golden.yaml
examples/fixtures/mlx_config.golden.json
```

`examples/fixtures/*` are Day-0 smoke/golden fixtures, not final benchmark claim data. `router_20.jsonl` and `gold_eval.finance.v1.jsonl` each contain at least 20 schema-valid rows to pin converters, validators, and snapshot tests. M4 production EvalSet still follows EVAL_SPEC §17.2 size n=200~300.

Benchmark baseline artifacts:

```text
- `prompts/router.prompt_only.v1.txt`
  - UTF-8 LF text file.
  - Required placeholders: `{route_catalog_json}`, `{input_json}`, `{output_schema_json}`.
  - No hidden network/tool instructions. Prompt hash = SHA256 of exact UTF-8 bytes.
- `schemas/routing_rules.schema.json`
  - JSON Schema for YAML parsed as a JSON-compatible object.
  - Required fields: `schema_version="routing_rules.v1"`, `default_route_id`, `rules`.
- `rules/router.routing_rules.v1.yaml`
  - Must validate against `schemas/routing_rules.schema.json`.
  - `rules[]` item fields: `rule_id`, `priority`, `route_id`, `when`.
  - `when` supports deterministic predicates only: `contains`, `equals`, `in`, `regex`, `exists`, `gt`, `lt`.
  - `field` uses JSON Pointer over router input, e.g. `/description` or `/metadata/source`.
  - Rules are evaluated by ascending `priority`; first match wins; no match returns `default_route_id`.
  - File hash = SHA256 of canonical YAML bytes committed in repo.
```

### 4.2 Day-0 scaffold 성공 기준

```text
- repo-local `.venv` 생성과 dependency install 명령이 문서화되어 있다.
- requirements*.txt, package.json, pnpm-lock.yaml, .python-version, .node-version, rust-toolchain.toml 파일이 존재한다.
- Alembic 초기 리비전 파일 skeleton이 존재하고 ARCHITECTURE §24.2 canonical DDL을 참조한다. 전체 `upgrade/downgrade` ops는 M1-002에서 이 DDL을 Alembic operations로 변환한다.
- seed preset/model catalog/schema fixture 파일과 benchmark baseline prompt/rule artifacts가 존재한다.
- markdown link check와 SQLite schema extraction test가 통과한다.
- trainer config snapshot tests가 golden fixtures와 일치한다.
- OpenAPI/TS type generation은 M1-001 API scaffold 후 `m1-smoke`에서 검증한다.
- security workflow가 `requirements*.txt` audit, model manifest validation, secret scan을 수행한다. `openapi-drift` job은 M1-001 후 활성화한다.
- `.venv` interpreter로 scaffold verification command가 실행되고 Docker 없이 M1 smoke command를 실행할 수 있는 경로가 문서화되어 있다.
```

M1 smoke 성공 기준은 M1-001/M1-002/M1-004/M1-006 구현 후 확인한다. Day-0 자체가 `/healthz`, `/presets`, `/hardware-doctor/scan` 구현을 요구하지 않는다.

```text
M1 smoke:
- API 서버가 `/healthz` 200을 반환한다.
- OpenAPI 생성 결과가 `schemas/openapi.json`과 일치하고, generated TS type이 최신이다.
- Alembic upgrade head가 성공한다.
- seed preset 삽입 후 `/presets`가 `router.basic.v1`을 반환한다.
- `/hardware-doctor/scan`이 hardware_scan Job을 생성한다.
- `pytest`가 DB migration smoke test를 통과한다.
- `scripts/bootstrap_dev.sh --phase m1-smoke --skip-install` and `scripts/bootstrap_dev.ps1 -Phase m1-smoke -SkipInstall` fail with exit code 5 if required M1 smoke files are missing, and otherwise run `tests/smoke/test_m1_smoke.py`.
```

### 4.3 seed 파일 최소 내용

`presets/model_catalog.yaml`:

```yaml
models:
  - id: google/gemma-2b-it
    license: Gemma Terms of Use
    trust_remote_code: false
    context_length: 8192
    train_seq_len: 1024
    chat_template: tokenizer.apply_chat_template
    system_role: unsupported_prepend_to_user
    allowed_backends: [cuda, mlx]
    lora_target: [all]
    hf_commit_sha: M1_DAY0_FILL
    files:
      - path: config.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: tokenizer.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: tokenizer_config.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: model.safetensors.index.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: false
  - id: microsoft/Phi-3.5-mini-instruct
    license: MIT
    trust_remote_code: false
    context_length: 131072
    train_seq_len: 1024
    chat_template: tokenizer.apply_chat_template
    system_role: supported
    allowed_backends: [cuda, mlx]
    lora_target: [all]
    hf_commit_sha: M1_DAY0_FILL
    files:
      - path: config.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: tokenizer.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: tokenizer_config.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: true
      - path: model.safetensors.index.json
        sha256: M1_DAY0_FILL
        size_bytes: 0
        required: false
```

Day-0 model catalog fill:

- The scaffold template may contain `M1_DAY0_FILL` only before the networked fill step.
- M1 Day-0 must run `python scripts/fill_model_catalog.py --catalog presets/model_catalog.yaml --models google/gemma-2b-it microsoft/Phi-3.5-mini-instruct`.
- Gated HF repos require `HF_TOKEN` (or `HUGGING_FACE_HUB_TOKEN`/`HUGGINGFACE_TOKEN`) with accepted model terms before running the fill command. `scripts/fill_model_catalog.py` also loads these token names from local ignored `.env` when the variables are not already exported.
- Gated HF runbook:
  1. Do not paste tokens into docs, Git, issue comments, chat, or logs.
  2. Put the token in local `.env` as `HF_TOKEN=<read-token>` or export one of the supported token variables in the same shell. Never put a real token in `.env.example`.
  3. Verify only the token identity without putting the token in command argv:
     ```bash
     python3 - <<'PY'
     import json, os, sys, urllib.request
     from pathlib import Path

     for raw_line in Path(".env").read_text().splitlines() if Path(".env").exists() else []:
         line = raw_line.strip()
         if not line or line.startswith("#") or "=" not in line:
             continue
         if line.startswith("export "):
             line = line[len("export "):].strip()
         key, value = line.split("=", 1)
         key = key.strip()
         if key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN") and key not in os.environ:
             os.environ[key] = value.strip().strip("'\"")

     token = next(
         (os.getenv(name) for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN") if os.getenv(name)),
         None,
     )
     if not token:
         sys.exit("missing HF_TOKEN, HUGGING_FACE_HUB_TOKEN, or HUGGINGFACE_TOKEN")
     req = urllib.request.Request("https://huggingface.co/api/whoami-v2")
     req.add_header("Authorization", f"Bearer {token}")
     with urllib.request.urlopen(req, timeout=30) as response:
         identity = json.loads(response.read().decode("utf-8"))
     print(json.dumps({
         "type": identity.get("type"),
         "name": identity.get("name"),
         "emailVerified": identity.get("emailVerified"),
         "tokenRole": identity.get("auth", {}).get("accessToken", {}).get("role"),
     }, indent=2))
     PY
     ```
  4. Confirm that this exact HF account accepted the `google/gemma-2b-it` terms and can view the repo files in the browser.
  5. Rerun `python scripts/fill_model_catalog.py --catalog presets/model_catalog.yaml --models google/gemma-2b-it microsoft/Phi-3.5-mini-instruct`.
  6. Run strict verification: `python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json`.
  7. If HF still returns 401/403, wait for access propagation or create a fresh read token for the same account; fine-grained tokens must include read access to the gated model repo.
- The fill script resolves HF commit SHA, config/tokenizer metadata, and all required model weight shard SHA256/size metadata, then rewrites `presets/model_catalog.yaml`.
- Local pre-M0 template experiments may run `verify_model_catalog.py --no-download --allow-day0-placeholders` explicitly, outside PR CI and outside bootstrap.
- M0/M1 bootstrap and CI run strict `verify_model_catalog.py --no-download` and reject any remaining placeholder.
- Strict verification fails if a model has no required weight shard (`model.safetensors`, `model-*.safetensors`, `pytorch_model.bin`, or `pytorch_model-*.bin`).
- If any selected v0 base model cannot be filled because of 401/403/license/token failure, M0/M1 signoff remains NO_GO; do not hide the model as available in UI.

### 4.4 Supply-chain CI contract

`.github/workflows/security.yml` must contain these jobs from Day-0:

```text
phase:
  source: workflow_dispatch input `phase` or repository variable `MIB_CI_PHASE`
  default: scaffold
python-audit:
  cuda command: pip-audit -r requirements.txt -r requirements-dev.txt
  mlx command: pip-audit -r requirements-mlx.txt -r requirements-dev.txt
  rule: run profile-specific jobs separately; never resolve requirements.txt and requirements-mlx.txt in one environment
model-manifest:
  CI command: python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_verification.json
  local pre-M0 template-only command: add --allow-day0-placeholders explicitly; never use this in PR CI after M0 GO
  checks: exact two locked model IDs, canonical metadata, trust_remote_code=false, positive file sizes, safe relative paths, required config/tokenizer files, complete required weight shard set, 40-hex hf_commit_sha, and 64-hex sha256
secret-scan:
  command: detect-secrets scan --all-files
openapi-drift:
  command: python scripts/export_openapi.py && git diff --exit-code schemas/openapi.json
  M0 behavior: validates the Day-0 seed; after M1-001 creates FastAPI scaffold, the script compares app.openapi() with schemas/openapi.json
code-shape:
  command: python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  command: python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
m1-security-smoke:
  scaffold: skip with explicit log
  MIB_CI_PHASE != scaffold: require tests/security and run pytest tests/security
m6-export-security:
  MIB_CI_PHASE=m6 only: require tests/export and run pytest tests/export
```

`verify_model_catalog.py` behavior:

```text
1. Parse `presets/model_catalog.yaml`.
2. Reject missing `hf_commit_sha`, non-40-hex commit SHA, `trust_remote_code=true`, duplicate model id, or non-64-hex file SHA256 after strict fill. Only explicit local pre-M0 template experiments may pass `--allow-day0-placeholders`.
2a. In strict mode, recursively reject `M1_DAY0_FILL` anywhere in the parsed catalog, including optional files or future metadata fields.
3. Reject strict catalogs that do not list at least one required model weight shard per model.
4. For cached local files, recompute SHA256 and compare with manifest.
5. In `--no-download` CI mode, do not access the network. Missing local model weights are allowed, but required metadata hashes must be present.
6. Print a JSON summary to `artifacts/security/model_manifest_verification.json`.
```

`presets/router.basic.v1.yaml`:

```yaml
id: router.basic.v1
name: Basic Router
preset_type: router
version: 1
base_model_options:
  - google/gemma-2b-it
  - microsoft/Phi-3.5-mini-instruct
route_rules:
  min_routes: 2
  max_routes: 12
  route_id_pattern: "^[a-z0-9_]+$"
  reserved_routes:
    - human_review
    - blocked
dataset:
  format: jsonl
  min_user_examples: 20
  output_schema: schemas/router_output.schema.json
training_defaults:
  quick: { epochs: 1, lora_rank: 8, max_seq_length: 1024 }
  balanced: { epochs: 3, lora_rank: 8, max_seq_length: 1024 }
  production: { epochs: 3, lora_rank: 16, max_seq_length: 1024 }
eval_options:
  metrics:
    - route_accuracy
    - task_type_accuracy
    - unsafe_recall
    - json_valid_rate
    - latency_p50
    - cost_per_task
export_options:
  - zip
  - docker
```

---

## 5. Backend 공통 계약

### 5.1 ID / 시간 / 오류

```text
ID: ULID 또는 UUIDv7 TEXT.
시간: UTC ISO-8601, 예: 2026-06-20T12:34:56.789Z.
JSON naming: snake_case.
trace_id: 요청마다 생성하고 응답, Job, JobEvent, AuditEvent에 전파.
```

오류 응답:

```json
{
  "error_code": "DATASET_NOT_APPROVED",
  "message": "Dataset must be approved before training.",
  "details": {
    "dataset_id": "01JZ..."
  },
  "trace_id": "01JZ..."
}
```

### 5.2 FastAPI middleware

구현 순서:

```text
1. trace_id 생성/전파 middleware
2. Host/Origin allowlist + CORS preflight middleware
3. request size limit
4. bearer token auth middleware
5. exception handler → 표준 오류 응답
```

로컬 API는 반드시 `127.0.0.1`에만 bind한다.

CORS/preflight contract:

```text
- CORS preflight는 `OPTIONS` + `Origin` + `Access-Control-Request-Method`가 모두 있는 요청이다.
- Preflight는 route handler까지 전달하지 않는 middleware 응답이며, Bearer token을 요구하지 않는다.
- 단, Host/Origin allowlist는 preflight에도 먼저 적용한다. 불허 Host/Origin은 403.
- 허용 method: GET, POST, PATCH, PUT, DELETE, OPTIONS.
- 허용 request headers: Authorization, Content-Type, Idempotency-Key, Last-Event-ID, X-Trace-Id.
- 허용 Origin이면 204 no content를 반환하고 `Access-Control-Allow-Origin`은 요청 Origin을 echo한다.
- `Access-Control-Allow-Credentials`는 사용하지 않는다(cookie/session 미사용). 토큰은 Authorization header만 허용한다.
- 응답은 `Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers`를 포함한다.
- Preflight는 DB write, Job 생성, AuditEvent 생성, request body parsing을 하지 않는다.
- Preflight가 아닌 `OPTIONS`는 404/405 표준 오류로 처리한다.
```

### 5.3 Pydantic DTO 기본형

All DTOs live under `services/api/app/schemas/*.py`. `schemas/openapi.json` is generated from FastAPI and is the FE source of truth. It must include typed `components.schemas`, path parameters, request bodies, and response schemas for every endpoint in §5.4. `apps/desktop/src/lib/generated.ts` is generated from `schemas/openapi.json` and must expose DTO interfaces plus operation-level client types: `ApiOperationMap`, `ApiParams`, `ApiRequest`, `ApiResponse`, `ApiError`, and `TypedApiClient`. The file must start with:

Request/response DTOs use Pydantic `model_config = ConfigDict(extra="forbid")` and OpenAPI `additionalProperties: false` by default. Only explicit JSON bag fields named `*_json`, `payload`, `details`, `packet_preview`, `pii_summary`, or `local_large_config` may allow additional properties.

```text
// @generated from schemas/openapi.json; do not edit by hand.
```

```python
Id = Annotated[str, Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]
IsoDatetime = str
T = TypeVar("T")

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    trace_id: str

class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None

class JobAcceptedResponse(BaseModel):
    job_id: Id
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
    type: str
    events_url: str
    created_resource_type: Literal["model_run", "benchmark", "export", "hardware_scan", "dataset", "none"] = "none"
    created_resource_id: Id | None = None
    idempotency_replayed: bool = False

class JobControlResponse(BaseModel):
    job_id: Id
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
    cancel_requested: bool = False
    child_job_id: Id | None = None
    events_url: str

class RouteRead(BaseModel):
    id: Id
    route_id: str
    description: str
    is_unsafe: bool
    created_at: IsoDatetime

class ProjectRead(BaseModel):
    id: Id
    name: str
    preset_id: str
    archived_at: IsoDatetime | None = None
    created_at: IsoDatetime
    updated_at: IsoDatetime
    routes: list[RouteRead]

class PresetRead(BaseModel):
    id: str
    name: str
    preset_type: Literal["router"]
    version: int
    schema_refs: dict[str, str]
    config_json: dict[str, Any]
    created_at: IsoDatetime

class RowValidationError(BaseModel):
    field: str
    code: str
    message: str

class ExampleRead(BaseModel):
    id: Id
    dataset_id: Id
    source: Literal["user", "teacher", "import", "hard_negative", "eval_gold"]
    review_status: Literal["PENDING", "APPROVED", "REJECTED", "EDITED"] = "PENDING"
    input: dict[str, Any]
    output: dict[str, Any]
    approved: bool
    validation_errors: list[RowValidationError] = Field(default_factory=list)
    created_at: IsoDatetime

class DatasetRead(BaseModel):
    id: Id
    project_id: Id
    version: int
    status: Literal["DRAFT", "BUILT", "REVIEWED", "APPROVED", "ARCHIVED"]
    path: str
    sample_count: int
    sha256: str
    schema_version: str
    route_snapshot_sha256: str
    created_at: IsoDatetime
    frozen_at: IsoDatetime | None = None

class DatasetWithExamples(DatasetRead):
    examples: list[ExampleRead]
    next_cursor: str | None = None

class JobRead(BaseModel):
    id: Id
    project_id: Id | None
    parent_job_id: Id | None = None
    type: Literal["dataset_gen", "train", "eval", "benchmark", "export", "hardware_scan"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
    resource_class: Literal["cpu_shared", "gpu_exclusive"]
    priority: int
    params_json: dict[str, Any]
    progress_json: dict[str, Any]  # derived from latest JobEvent + terminal status, not a DB column
    error_class: str | None = None
    error_message: str | None = None
    cancel_requested_at: IsoDatetime | None = None
    attempt_count: int
    events_url: str
    created_at: IsoDatetime
    started_at: IsoDatetime | None = None
    ended_at: IsoDatetime | None = None

class HardwareProfileRead(BaseModel):
    id: Id
    machine_id: str
    os: str
    cpu: str | None
    gpu_vendor: Literal["nvidia", "apple", "amd", "intel", "none", "unknown"]
    gpu_name: str | None
    vram_gb: float | None
    unified_ram_gb: float | None
    ram_gb: float
    cuda_status: Literal["ok", "missing", "unsupported", "na"] | None = None
    mlx_status: Literal["ok", "missing", "unsupported", "na"] | None = None
    capability_gate: Literal["G0", "G1", "G2"]
    backend_recommendation: Literal["cuda", "mlx", "cpu", "unsupported"]
    training_enabled: bool
    training_disabled_reason_code: Literal["NO_GPU", "LOW_VRAM", "UNSUPPORTED_VENDOR", "MISSING_DRIVER", "PYTHON_UNSUPPORTED", "NONE"]
    training_disabled_reason_message: str
    allowed_backends: list[Literal["cuda", "mlx"]]
    unlock_requirements: list[str] = Field(default_factory=list)
    dry_run_result_json: dict[str, Any]
    created_at: IsoDatetime

class ModelCatalogWeightFileRead(BaseModel):
    path: str
    sha256: str
    size_bytes: int
    present_in_cache: bool

class ModelCatalogEntryRead(BaseModel):
    id: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"]
    license: str
    trust_remote_code: bool
    context_length: int
    train_seq_len: int
    chat_template: str
    system_role: str
    allowed_backends: list[Literal["cuda", "mlx"]]
    lora_target: list[str]
    hf_commit_sha: str | None
    strict_manifest_ready: bool
    available: bool
    disabled_reason_code: Literal["NONE", "STRICT_MANIFEST_MISSING", "LICENSE_NOT_ACCEPTED", "BACKEND_UNSUPPORTED", "LOCAL_CACHE_MISSING"]
    disabled_reason_message: str
    terms_required: bool = False
    required_weight_files: list[ModelCatalogWeightFileRead]

class ModelCatalogRead(BaseModel):
    items: list[ModelCatalogEntryRead]
    strict_ready: bool

class CredentialRead(BaseModel):
    id: Id
    provider: Literal["openai", "openai_compatible"]
    base_url_origin: str
    keychain_ref: str
    is_revoked: bool
    expires_at: IsoDatetime | None = None
    created_at: IsoDatetime
    last_used_at: IsoDatetime | None = None

class TeacherPacketPreviewRead(BaseModel):
    id: Id
    project_id: Id
    packet_sha256: str
    packet_preview: dict[str, Any]
    pii_summary: dict[str, Any]
    expires_at: IsoDatetime
    approved_at: IsoDatetime | None = None

class TeacherPacketApprovalRead(BaseModel):
    approval_id: Id
    project_id: Id
    packet_sha256: str
    approved_at: IsoDatetime
    expires_at: IsoDatetime

class ModelRunRead(BaseModel):
    id: Id
    job_id: Id | None = None  # current controlling job from JobResource(resource_type='model_run')
    project_id: Id
    dataset_id: Id
    base_model: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"]
    backend: Literal["cuda", "mlx"]
    method: Literal["qlora", "mlx_lora"]
    adapter_path: str | None = None
    adapter_sha256: str | None = None
    artifact_manifest_sha256: str | None = None
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
    seed: int
    config_hash: str
    best_checkpoint_id: Id | None = None
    resumable: bool
    started_at: IsoDatetime | None = None
    ended_at: IsoDatetime | None = None
    created_at: IsoDatetime

class CheckpointRead(BaseModel):
    id: Id
    job_id: Id
    model_run_id: Id
    dataset_id: Id
    dataset_version: int
    step: int
    path: str
    training_config_hash: str
    weights_sha256: str
    resume_enabled: bool
    resume_disabled_reason_code: Literal["NONE", "DATASET_VERSION_MISMATCH", "CONFIG_HASH_MISMATCH", "MISSING_ARTIFACT", "JOB_NOT_RESUMABLE"]
    resume_disabled_reason_message: str
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    created_at: IsoDatetime

class EvalSetRead(BaseModel):
    id: Id
    project_id: Id
    dataset_id: Id
    purpose: Literal["teacher_guard", "benchmark_gold", "finance_reference"]
    version: int
    path: str
    sha256: str
    sample_count: int
    route_snapshot_sha256: str
    labeler_ids_json: list[str]
    kappa: float | None
    frozen_at: IsoDatetime
    created_at: IsoDatetime

class EvalRunRead(BaseModel):
    id: Id
    benchmark_id: Id
    model_run_id: Id | None = None
    target_key: str
    target_type: Literal["prompt_only", "fine_tuned", "teacher", "local_large", "rule_based"]
    backend: Literal["cuda", "mlx", "teacher", "rule_based", "prompt_only", "local_large"]
    target_status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "SKIPPED_OPTIONAL"]
    target_config_json: dict[str, Any]
    seed: int
    credential_id: Id | None = None
    metrics_json: dict[str, Any]
    created_at: IsoDatetime
```

### 5.4 Endpoint implementation matrix

| Endpoint | Request DTO | Response DTO | Service | Tests |
|---|---|---|---|---|
| `GET /healthz` | none | `{status, version}` | none | `test_healthz` |
| `POST /projects` | `ProjectCreate` | `ProjectRead` | `project_service.create_project` | preset FK, route count |
| `GET /projects` | cursor params | `PageResponse[ProjectRead]` | `project_service.list_projects` | pagination |
| `GET /projects/{id}` | path id | `ProjectRead` | `project_service.get_project` | 404 |
| `PATCH /projects/{id}` | `ProjectPatch` | `ProjectRead` | `project_service.patch_project` | archived guard |
| `DELETE /projects/{id}` | path id | 204 | `project_service.archive_project` | archived_at set |
| `GET /presets` | none | `list[PresetRead]` | `preset_service.list_presets` | router only |
| `GET /presets/{id}` | path id | `PresetRead` | `preset_service.get_preset` | 404 |
| `GET /model-catalog` | none | `ModelCatalogRead` | `model_catalog_service.read_availability` | strict manifest, disabled reason |
| `POST /projects/{id}/datasets` | `DatasetBuildRequest` | `DatasetRead` | `dataset_service.build_dataset` | JSONL/schema/sha |
| `GET /projects/{id}/datasets` | cursor params | `PageResponse[DatasetRead]` | `dataset_service.list_datasets` | project scope |
| `GET /datasets/{id}` | cursor params | `DatasetWithExamples` | `dataset_service.get_dataset` | page examples |
| `PATCH /datasets/{id}` | `DatasetPatch` | `DatasetRead` | `dataset_service.patch_dataset` | approve transition |
| `PATCH /examples/{id}` | `ExamplePatch` | `ExampleRead` | `dataset_service.patch_example` | edit/reject guard |
| `POST /projects/{id}/jobs` | `JobSubmitRequest` | `JobAcceptedResponse` | `job_service.submit_project_job` | idempotency, excludes export/hardware_scan |
| `GET /jobs` | filters | `PageResponse[JobRead]` | `job_service.list_global_jobs` | global queue, hardware scan included |
| `GET /projects/{id}/jobs` | filters | `PageResponse[JobRead]` | `job_service.list_jobs` | status filter |
| `GET /jobs/{id}` | path id | `JobRead` | `job_service.get_job` | 404 |
| `DELETE /jobs/{id}` | path id | `JobControlResponse` | `job_service.cancel_job` | cancel_requested_at |
| `POST /jobs/{id}/retry` | `JobRetryRequest` | `JobControlResponse` | `job_service.retry_job` | child job, teacher reapproval |
| `POST /jobs/{id}/resume` | `ResumeJobRequest` | `JobControlResponse` | `job_service.resume_job` | checkpoint guard |
| `GET /jobs/{id}/events` | SSE | event stream | `job_service.stream_events` | Last-Event-ID |
| `POST /hardware-doctor/scan` | `HardwareScanRequest` | `JobAcceptedResponse` | `job_service.submit_job` | type=hardware_scan |
| `GET /hardware-doctor/result` | none | `HardwareProfileRead` | `hardware_service.latest` | empty state |
| `GET /projects/{id}/model-runs` | filters | `PageResponse[ModelRunRead]` | `training_service.list_model_runs` | status/backend filter |
| `GET /model-runs/{id}` | path id | `ModelRunRead` | `training_service.get_model_run` | adapter/checkpoint summary |
| `GET /model-runs/{id}/checkpoints` | cursor params | `PageResponse[CheckpointRead]` | `training_service.list_checkpoints` | stale flags |
| `GET /credentials` | none | `{items: list[CredentialRead]}` | `credential_service.list` | no key leak |
| `PUT /credentials/{provider}` | `CredentialUpsert` | 204 | `credential_service.upsert` | keyring called |
| `DELETE /credentials/{provider}` | path provider | 204 | `credential_service.revoke` | is_revoked |
| `POST /projects/{id}/teacher-packets/preview` | `TeacherPacketPreviewRequest` | `TeacherPacketPreviewRead` | `teacher_service.preview_packet` | PII/schema |
| `POST /teacher-packets/{id}/approve` | none | `TeacherPacketApprovalRead` | `teacher_service.approve_packet` | approval record |
| `POST /projects/{id}/eval-sets` | `EvalSetCreate` | `EvalSetRead` | `eval_service.create_eval_set` | frozen_at, sha, overlap guard |
| `GET /projects/{id}/eval-sets` | cursor params | `PageResponse[EvalSetRead]` | `eval_service.list_eval_sets` | frozen filter |
| `GET /eval-sets/{id}` | path id | `EvalSetRead` | `eval_service.get_eval_set` | sha/kappa visible |
| `GET /projects/{id}/eval-runs` | filters | `PageResponse[EvalRunRead]` | `eval_service.list_eval_runs` | benchmark/target filter |
| `GET /eval-runs/{id}` | path id | `EvalRunRead` | `eval_service.get_eval_run` | metrics_json returned |
| `GET /projects/{id}/benchmarks` | cursor params | `PageResponse[BenchmarkRead]` | `benchmark_service.list_benchmarks` | project scope |
| `GET /benchmarks/{id}` | path id | `BenchmarkRead` | `benchmark_service.get_benchmark` | report metadata |
| `GET /benchmarks/{id}/report` | path id | `BenchmarkReportRead` | `benchmark_service.get_report` | recompute hash, mismatch flag |
| `POST /projects/{id}/agent-packages` | `AgentPackageCreate` | `AgentPackageRead` | `package_service.create_package` | immutable contract hash |
| `GET /projects/{id}/agent-packages` | cursor params | `PageResponse[AgentPackageRead]` | `package_service.list_packages` | newest first |
| `GET /agent-packages/{id}` | path id | `AgentPackageRead` | `package_service.get_package` | 404 |
| `POST /agent-packages/{id}/playground-runs` | `PlaygroundRunRequest` | `PlaygroundRunResponse` | `playground_service.run_local` | verifier, fallback approval |
| `POST /projects/{id}/export` | `ExportParams` | `JobAcceptedResponse` | `job_service.submit_job` | idempotency, type=export |
| `GET /exports/{job_id}` | path job_id | `ExportRead` | `export_service.get_export` | artifact hash, no key leak |
| `GET /exports/{job_id}/artifact` | path job_id | binary stream | `export_service.download_artifact` | recompute artifact hash before stream |
| `POST /exports/{job_id}/reveal` | path job_id | `{artifact_path, revealed}` | `export_service.reveal_artifact` | desktop shell reveal |

OpenAPI parity rule:

```text
- `schemas/openapi.json` is the implementation lock for this endpoint table and DTO sketch.
- `apps/desktop/src/lib/generated.ts` must expose the same operationIds, request DTOs, response DTOs, and disabled-reason fields.
- A DTO field may be optional in generated TypeScript only when the OpenAPI schema marks it nullable/optional.
- FE/BE must not introduce alternate field names such as `text` for `PlaygroundRunRequest.input` or `verifier_passed` for `PlaygroundRunResponse.verifier_status`.
```

### 5.5 DTO sketches

```python
class RouteInput(BaseModel):
    route_id: str = Field(pattern=r"^[a-z0-9_]+$", max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    is_unsafe: bool = False

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    preset_id: str = "router.basic.v1"
    routes: list[RouteInput] = Field(min_length=2, max_length=12)

class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    routes: list[RouteInput] | None = None

class ExampleInput(BaseModel):
    input: dict[str, Any]
    output: dict[str, Any]
    source: Literal["user", "import"] = "user"

class DatasetBuildRequest(BaseModel):
    examples: list[ExampleInput] = Field(min_length=20)
    status: Literal["DRAFT", "BUILT"] = "BUILT"

class DatasetPatch(BaseModel):
    status: Literal["DRAFT", "BUILT", "REVIEWED", "APPROVED", "ARCHIVED"] | None = None
    approved_example_ids: list[str] | None = None

class ExamplePatch(BaseModel):
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    review_status: Literal["PENDING", "APPROVED", "REJECTED", "EDITED"] | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.input is None and self.output is None and self.review_status is None:
            raise ValueError("at least one example field must change")
        return self

class EvalSetCreate(BaseModel):
    purpose: Literal["teacher_guard", "benchmark_gold", "finance_reference"] = "benchmark_gold"
    dataset_id: str
    example_ids: list[str] = Field(min_length=20, max_length=300)
    labeler_ids: list[str] = Field(min_length=1)
    kappa: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def require_eval_quality(self) -> Self:
        if self.purpose == "teacher_guard":
            if not 20 <= len(self.example_ids) <= 50:
                raise ValueError("teacher_guard eval set requires 20..50 approved examples")
            return self
        if not 200 <= len(self.example_ids) <= 300:
            raise ValueError("benchmark eval set requires 200..300 approved examples")
        if len(self.labeler_ids) < 3 or self.kappa is None or self.kappa < 0.70:
            raise ValueError("benchmark eval set requires >=3 labelers and Cohen kappa >= 0.70")
        return self

class JobSubmitRequest(BaseModel):
    type: Literal["dataset_gen", "train", "eval", "benchmark"]
    params: DatasetGenParams | TrainParams | EvalParams | BenchmarkParams

    @model_validator(mode="after")
    def validate_type_params(self) -> Self:
        expected = {
            "dataset_gen": DatasetGenParams,
            "train": TrainParams,
            "eval": EvalParams,
            "benchmark": BenchmarkParams,
        }
        if not isinstance(self.params, expected[self.type]):
            raise ValueError(f"type={self.type} requires params={expected[self.type].__name__}")
        return self

class HardwareScanRequest(BaseModel):
    dry_run: bool = True
    target_backend: Literal["cuda", "mlx", "auto"] = "auto"

class ResumeJobRequest(BaseModel):
    checkpoint_id: str

class JobRetryRequest(BaseModel):
    teacher_packet_approval_id: str | None = None

class CredentialUpsert(BaseModel):
    base_url: AnyUrl
    api_key: SecretStr
    expires_at: str | None = None

class TeacherPacketPreviewRequest(BaseModel):
    dataset_id: str
    example_ids: list[str] = Field(min_length=20, max_length=50)
    instruction: str = Field(min_length=1, max_length=8000)

class BenchmarkRead(BaseModel):
    id: Id
    project_id: Id
    job_id: Id
    eval_set_id: Id
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"]
    report_sha256: str | None = None
    hash_status: Literal["VALID", "MISMATCH", "MISSING"] = "MISSING"
    parity_status: Literal["PASS", "FAIL", "NA"]
    created_at: IsoDatetime
    completed_at: IsoDatetime | None = None

class BenchmarkReportRead(BaseModel):
    benchmark_id: Id
    report_sha256: str | None
    hash_status: Literal["VALID", "MISMATCH", "MISSING"]
    report: dict[str, Any] | None

class AgentPackageRead(BaseModel):
    id: Id
    agent_id: str
    project_id: Id
    model_run_id: Id
    benchmark_id: Id
    route_catalog_sha256: str
    contract_version: int
    contract_yaml: str
    contract_sha256: str
    created_at: IsoDatetime
```

### 5.6 Typed Job Params

```python
class DatasetGenParams(BaseModel):
    dataset_id: str | None = None
    generation_mode: Literal["build_from_user_examples", "teacher_synthetic"]
    teacher_packet_approval_id: str | None = None
    packet_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")  # server-copied snapshot hash
    target_count: int = Field(default=200, ge=20, le=5000)

    @model_validator(mode="after")
    def require_approval_for_teacher(self) -> Self:
        if self.generation_mode == "teacher_synthetic" and not self.teacher_packet_approval_id:
            raise ValueError("teacher_packet_approval_id is required for teacher_synthetic")
        return self

class TrainParams(BaseModel):
    preset_id: str = "router.basic.v1"
    dataset_id: str
    base_model: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"]
    backend: Literal["cuda", "mlx"]
    training_preset: Literal["quick", "balanced", "production"] = "balanced"
    seed: int = 42

class BenchmarkTargetConfig(BaseModel):
    target_key: str = Field(pattern=r"^[a-z0-9_:-]{1,80}$")
    target_type: Literal["prompt_only", "fine_tuned", "teacher", "rule_based", "local_large"]
    backend: Literal["cuda", "mlx", "teacher", "rule_based", "prompt_only", "local_large"]
    model_run_id: str | None = None
    base_model: Literal["google/gemma-2b-it", "microsoft/Phi-3.5-mini-instruct"] | None = None
    prompt_template_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    credential_id: str | None = None
    teacher_base_url_origin: str | None = None
    routing_rules_path: str | None = None
    routing_rules_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    local_large_config: dict[str, Any] | None = None
    required: bool = True

    @model_validator(mode="after")
    def validate_target_config(self) -> Self:
        expected_backend = {
            "prompt_only": "prompt_only",
            "teacher": "teacher",
            "rule_based": "rule_based",
            "local_large": "local_large",
        }
        if self.target_type in expected_backend and self.backend != expected_backend[self.target_type]:
            raise ValueError(f"{self.target_type} target requires backend={expected_backend[self.target_type]}")
        if self.target_type == "fine_tuned" and self.backend not in {"cuda", "mlx"}:
            raise ValueError("fine_tuned target requires backend cuda or mlx")
        if self.target_type == "prompt_only" and (self.base_model is None or self.prompt_template_sha256 is None):
            raise ValueError("prompt_only requires base_model and prompt_template_sha256")
        if self.target_type == "fine_tuned" and self.model_run_id is None:
            raise ValueError("fine_tuned requires model_run_id")
        if self.target_type == "teacher" and (self.credential_id is None or self.teacher_base_url_origin is None):
            raise ValueError("teacher requires credential_id and teacher_base_url_origin")
        if self.target_type == "rule_based" and (self.routing_rules_path is None or self.routing_rules_sha256 is None):
            raise ValueError("rule_based requires routing_rules_path and routing_rules_sha256")
        return self

class EvalParams(BaseModel):
    eval_set_id: str
    target: BenchmarkTargetConfig
    seed: int

class BenchmarkParams(BaseModel):
    eval_set_id: str
    targets: list[BenchmarkTargetConfig]
    seeds: list[int] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_targets(self) -> Self:
        target_types = [target.target_type for target in self.targets]
        target_keys = [target.target_key for target in self.targets]
        for target_type in ["prompt_only", "teacher", "rule_based"]:
            if target_types.count(target_type) != 1:
                raise ValueError(f"{target_type} target must appear exactly once")
        if target_types.count("fine_tuned") not in {1, 2}:
            raise ValueError("fine_tuned target count must be one, or two for CUDA/MLX parity")
        if target_types.count("local_large") > 1:
            raise ValueError("local_large target may appear at most once")
        if "local_large" not in target_types:
            self.targets.append(BenchmarkTargetConfig(
                target_key="local_large_optional",
                target_type="local_large",
                backend="local_large",
                required=False,
            ))
            target_types.append("local_large")
            target_keys.append("local_large_optional")
        fine_tuned_backends = {target.backend for target in self.targets if target.target_type == "fine_tuned"}
        if target_types.count("fine_tuned") == 2 and fine_tuned_backends != {"cuda", "mlx"}:
            raise ValueError("CUDA/MLX parity requires exactly one cuda and one mlx fine_tuned target")
        if len(set(target_keys)) != len(target_keys):
            raise ValueError("duplicate benchmark target_key")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("benchmark seeds must be distinct")
        for target in self.targets:
            if target.target_type == "local_large":
                target.required = False
        return self

class ExportParams(BaseModel):
    agent_package_id: str
    export_type: Literal["zip", "docker"]

class FallbackConditionInput(BaseModel):
    type: Literal["confidence_lt", "verifier_failed", "disabled"] = "disabled"
    threshold: float | None = Field(default=None, ge=0, le=1)

class FallbackConfigInput(BaseModel):
    enabled: bool = False
    provider: Literal["openai", "openai_compatible", "none"] = "none"
    model: str | None = None
    condition: FallbackConditionInput = Field(default_factory=FallbackConditionInput)

    @model_validator(mode="after")
    def validate_fallback(self) -> Self:
        if not self.enabled:
            if self.provider != "none" or self.condition.type != "disabled":
                raise ValueError("disabled fallback must use provider=none and condition.type=disabled")
            return self
        if self.provider == "none" or not self.model:
            raise ValueError("enabled fallback requires provider and model")
        if self.condition.type == "confidence_lt" and self.condition.threshold is None:
            raise ValueError("confidence_lt fallback requires threshold")
        return self

class AgentPackageCreate(BaseModel):
    agent_slug: str | None = Field(default=None, pattern=r"^[a-z0-9_]{1,48}$")
    model_run_id: str
    benchmark_id: str
    fallback: FallbackConfigInput = Field(default_factory=FallbackConfigInput)

class PlaygroundRunRequest(BaseModel):
    input: dict[str, Any]
    approve_fallback: bool = False

class PlaygroundRunResponse(BaseModel):
    output: dict[str, Any]
    verifier_status: Literal["PASS", "FAIL"]
    verifier_errors: list[str] = []
    fallback_required: bool = False
    fallback_used: bool = False
    audit_event_id: Id | None = None

class ExportRead(BaseModel):
    id: Id
    job_id: Id
    agent_package_id: Id
    export_type: Literal["zip", "docker"]
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"]
    manifest_path: str | None = None
    manifest_sha256: str | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    artifact_url: str | None = None
    reveal_url: str | None = None
    error_message: str | None = None
    created_at: IsoDatetime
    completed_at: IsoDatetime | None = None

class HardwareScanParams(BaseModel):
    dry_run: bool = True
    target_backend: Literal["cuda", "mlx", "auto"] = "auto"
```

Benchmark service validation beyond DTO shape:

```text
- Load EvalSet and require purpose in {'benchmark_gold','finance_reference'}, frozen_at not null, kappa >= 0.70, sample_count 200..300.
- Load each fine_tuned target ModelRun and require project_id matches, status='SUCCEEDED', adapter hashes exist, and Dataset.route_snapshot_sha256 == EvalSet.route_snapshot_sha256.
- If there are two fine_tuned targets, their backends must be cuda/mlx and their base_model values must be the same base model family. Different base models require separate Benchmark rows.
- prompt_only target base_model must match the selected fine_tuned base_model family for release comparison.
- teacher and rule_based targets are exactly one each and are included in every release benchmark report.
```

`POST /hardware-doctor/scan` mapping:

```text
- Request body: `HardwareScanRequest`.
- Service maps it to Job row:
  - type = `hardware_scan`
  - project_id = NULL
  - resource_class = `cpu_shared`
  - params_json = HardwareScanParams.model_dump()
- Canonical idempotency body hash is computed from `HardwareScanRequest`, not a synthetic `JobSubmitRequest`.
- Replayed request returns the existing `JobAcceptedResponse` with `idempotency_replayed=true`.
```

`POST /projects/{id}/export` mapping:

```text
- Request body: `ExportParams`.
- Service validates AgentPackage.project_id == path project id.
- In one transaction, insert Job(type='export', project_id=:id, resource_class='cpu_shared') and ExportArtifact(status='QUEUED', job_id=:job_id).
- Job.params_json stores `agent_package_id`, `export_type`, and server-owned `export_artifact_id`.
- Response: JobAcceptedResponse(created_resource_type='export', created_resource_id=export_artifact.id).
- `GET /exports/{job_id}` reads ExportArtifact by job_id. Missing export_artifact for an export job is 500 `EXPORT_ARTIFACT_MISSING`.
- When status='SUCCEEDED', ExportRead includes `artifact_url='/exports/{job_id}/artifact'` and `reveal_url='/exports/{job_id}/reveal'`.
- `GET /exports/{job_id}/artifact` recomputes artifact_sha256 before streaming. Mismatch returns 409 `EXPORT_HASH_MISMATCH` and does not stream bytes.
- `POST /exports/{job_id}/reveal` verifies status/hash, then reveals the artifact in the OS file manager and returns `{artifact_path, revealed:true}`.
```

Project job resource creation:

```text
train:
  - Client submits TrainParams without model_run_id.
  - Daemon validates Dataset.status='APPROVED' and HardwareProfile gate.
  - In one transaction, create ModelRun(status='QUEUED'), Job(type='train', resource_class='gpu_exclusive'), and JobResource(job_id=job.id, resource_type='model_run', resource_id=model_run.id, is_current=1).
  - Job.params_json is the validated TrainParams plus server-owned `model_run_id`.
  - Response: JobAcceptedResponse(created_resource_type='model_run', created_resource_id=model_run.id).
  - `training_store.py` is the only writer for ModelRun.status after claim; SUCCEEDED requires adapter_path, adapter_sha256, artifact_manifest_sha256.

benchmark:
  - Client submits BenchmarkParams.
  - Daemon validates EvalSet frozen state, route_snapshot_sha256, target cardinality, target_key uniqueness, and fine_tuned ModelRun ownership/base_model-family compatibility.
  - In one transaction, preallocate `job_id` and `benchmark_id`, create Job(type='benchmark', resource_class='gpu_exclusive'), then create Benchmark(id=benchmark_id, job_id=job_id, status='QUEUED').
  - Benchmark is `gpu_exclusive` even though it is an orchestrator job because v0 benchmark execution may load fine-tuned/local targets in-process; the DB partial unique index must prevent concurrent train/eval/benchmark GPU occupancy.
  - Job.params_json is the validated BenchmarkParams plus server-owned `benchmark_id`.
  - Response: JobAcceptedResponse(created_resource_type='benchmark', created_resource_id=benchmark.id).
  - `benchmark_store.py` is the only writer for Benchmark.status after claim. It creates EvalRun rows for each target_key x seed in the parent benchmark job, runs them sequentially, and then writes report_path/report_sha256.

dataset_gen:
  - `build_from_user_examples` may be created from `POST /projects/{id}/datasets` synchronously for M1 seed data.
  - Teacher synthetic enrichment is always async through Job(type='dataset_gen').
  - For teacher_synthetic, Daemon loads the fresh TeacherPacketApproval, copies packet_sha256 into Job.params_json, sets used_job_id atomically, and rejects retry without a new approval.
```

Secondary resource status mapping:

| Job.type | Resource table | Store owner | On job claim | On success | On failure/interrupted/cancel |
|---|---|---|---|---|---|
| `train` | `model_run` | `training_store.py` | ModelRun `QUEUED`→`RUNNING` in same transaction as Job claim event | write adapter paths/hashes/checkpoint summary, then ModelRun `SUCCEEDED` and Job `SUCCEEDED` in one short transaction | write sanitized error_message, mirror terminal Job status |
| `benchmark` | `benchmark` | `benchmark_store.py` | Benchmark `QUEUED`→`RUNNING`, create planned EvalRun rows | verify report schema/hash, write report_path/report_sha256, then Benchmark `COMPLETED` and Job `SUCCEEDED` | Benchmark `FAILED|CANCELLED|INTERRUPTED` mirrors Job terminal failure class |
| `eval` | `eval_run` | `benchmark_store.py` | EvalRun `QUEUED`→`RUNNING` for target_key+seed | write metrics_json and EvalRun `COMPLETED` | write sanitized error_message and set `FAILED|CANCELLED|INTERRUPTED`; optional local_large hardware miss is `SKIPPED_OPTIONAL`, not Job failure |
| `export` | `export_artifact` | `export_store.py` | ExportArtifact `QUEUED`→`RUNNING` | verify manifest/artifact hashes, write paths/hashes, then ExportArtifact `SUCCEEDED` and Job `SUCCEEDED` | write sanitized error_message, mirror terminal Job status |
| `dataset_gen` | `dataset`/`example` | `dataset_store.py` | DatasetGen progress only; existing approved datasets are immutable | create new Dataset/Example rows or mark generated draft set complete | no partial Dataset approval; rejected rows stay draft with reason |
| `hardware_scan` | `hardware_profile` | `hardware_store.py` | no secondary RUNNING row required | upsert latest HardwareProfile and Job `SUCCEEDED` | Job terminal only; keep previous HardwareProfile |

Mirror rule: API services create secondary resources only in initial `QUEUED` state. After claim, worker handlers update both Job and secondary resource through the owner store in one transaction. Domain success names may differ from Job success (`Benchmark/EvalRun=COMPLETED`, `Job=SUCCEEDED`); failure/cancel/interrupted names mirror Job terminal states. Daemon reconcile may move Job `RUNNING`→`INTERRUPTED`; the matching owner store must mirror the secondary resource to `INTERRUPTED` during the same reconcile transaction.

### 5.7 Idempotency and Job Control Tests

Canonical body hash:

```python
def canonical_request_body_hash(dto: BaseModel) -> str:
    data = dto.model_dump(mode="json", by_alias=True, exclude_none=True)
    body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
```

Rules:

```text
- Hash the validated Pydantic DTO, not raw request bytes.
- Pydantic defaults are included unless their value is None.
- Object keys are sorted. List order is preserved.
- Backend hash is authoritative; FE does not compute idempotency hashes.
```

Submit transaction:

```text
1. Validate DTO and compute canonical_request_body_hash.
2. BEGIN IMMEDIATE.
3. Release expired terminal keys:
   UPDATE job
   SET idempotency_key=NULL,
       idempotency_body_sha256=NULL
   WHERE idempotency_key=:key
     AND ((project_id=:project_id) OR (:project_id IS NULL AND project_id IS NULL))
     AND idempotency_expires_at <= :now
     AND status IN ('SUCCEEDED','FAILED','CANCELLED','INTERRUPTED');
4. SELECT existing unexpired row by scope+key.
5. If existing row has same body hash, COMMIT and return existing job with idempotency_replayed=true.
6. If existing row has different body hash, ROLLBACK and return 409 IDEMPOTENCY_BODY_MISMATCH.
7. INSERT new Job with idempotency_key, idempotency_body_sha256, idempotency_expires_at=now+24h.
8. INSERT first JobEvent(status_change) with seq=1.
9. COMMIT.
```

Expired QUEUED/RUNNING jobs do not release their idempotency key. They must complete, fail, cancel, or be reconciled to INTERRUPTED first.

```text
test_idempotency_replay_same_body_returns_same_job
test_idempotency_body_mismatch_409
test_hardware_scan_idempotency_null_project_unique
test_idempotency_expired_terminal_key_reusable
test_idempotency_expired_running_key_not_reusable
test_cancel_queued_marks_cancelled
test_cancel_running_sets_cancel_requested
test_retry_failed_creates_child_job_and_increments_attempt
test_retry_teacher_synthetic_requires_new_approval
test_retry_teacher_synthetic_copies_new_packet_sha
test_resume_rejects_dataset_mismatch
test_sse_replay_after_last_event_id
test_sse_event_gap_409
test_worker_crash_reconcile_interrupted
test_gpu_busy_claim_does_not_starve_cpu_job
```

Retry rules:

```text
- Retry is allowed only for FAILED, INTERRUPTED, or CANCELLED jobs.
- Child job copies the parent job type/resource_class/project_id/preset_version unless the type-specific rule below says otherwise.
- Retry that owns a secondary resource must rebind that resource to the child job in the same transaction that creates the child Job. API reads always return the current controlling job id from the secondary resource, not the original failed job.
- For teacher_synthetic dataset_gen, the request body must provide `teacher_packet_approval_id`; the original approval is not reusable because SECURITY_SPEC §19 requires a fresh user approval for retry/resume.
- Daemon loads the new approval, recomputes packet_sha256, writes `params_json.teacher_packet_approval_id` and `params_json.packet_sha256`, and sets TeacherPacketApproval.used_job_id to the child job id in the same transaction.
- Retry writes AuditEvent(event_type='job_control', action='retry', resource_type='job', resource_id=child_job_id, details_json={parent_job_id, reason, approval_id?}).
- Generic retry without a required approval returns 409 `TEACHER_PACKET_APPROVAL_REQUIRED`.
- Resume writes AuditEvent(event_type='job_control', action='resume', resource_type='job', resource_id=child_job_id, details_json={parent_job_id, checkpoint_id, model_run_id}).
```

Retry secondary-resource rebinding:

| Parent Job.type | Rebinding rule |
|---|---|
| `benchmark` | In the retry transaction, update `Benchmark.job_id=child_job_id`, `status='QUEUED'`, `report_path=NULL`, `report_sha256=NULL`, `parity_status='NA'`, `completed_at=NULL`; delete previous derived EvalRun rows for the benchmark before the child job replans target×seed rows. |
| `export` | Update `ExportArtifact.job_id=child_job_id`, `status='QUEUED'`, `manifest_path=NULL`, `manifest_sha256=NULL`, `artifact_path=NULL`, `artifact_sha256=NULL`, `error_message=NULL`, `completed_at=NULL`. |
| `train` | Keep the same ModelRun row; in the retry/resume transaction set previous JobResource(`resource_type='model_run'`, `resource_id=model_run_id`).is_current=0 and insert child JobResource.is_current=1. `ModelRunRead.job_id` reads the current JobResource, never `Job.params_json`. |
| `dataset_gen` | No approved Dataset row is reused. Teacher synthetic retry requires a new approval and writes a new generated draft output set. |
| `hardware_scan` | No secondary row is rebound; successful retry upserts the latest HardwareProfile. |

`test_retry_benchmark_rebinds_job_id`, `test_retry_benchmark_clears_report_and_eval_runs`, and `test_retry_export_rebinds_artifact_job_id` are required.

### 5.7.1 Error Code Registry

All API errors use `ErrorResponse`. `details` must match the schema below for each code; extra fields are forbidden in tests.

| Domain | Code | HTTP | Retryable | details schema | FE mapping |
|---|---|---:|---|---|---|
| Auth | `AUTH_REQUIRED` | 401 | after config fix | `{}` | show reconnect/auth banner |
| Auth | `AUTH_INVALID` | 401 | after config fix | `{}` | show reconnect/auth banner |
| Origin | `HOST_NOT_ALLOWED` | 403 | no | `{host}` | daemon security error |
| Origin | `ORIGIN_NOT_ALLOWED` | 403 | no | `{origin}` | daemon security error |
| Validation | `VALIDATION_FAILED` | 422 | after user edit | `{field?, row_index?, reason}` | inline field/row error |
| Project | `PROJECT_ARCHIVED` | 409 | no | `{project_id}` | read-only archived banner |
| Project | `ROUTE_TAXONOMY_LOCKED` | 409 | no | `{project_id,locked_by_resource_type,locked_by_resource_id}` | route editor locked state |
| Idempotency | `IDEMPOTENCY_BODY_MISMATCH` | 409 | no | `{idempotency_key}` | block duplicate submit |
| Job | `JOB_NOT_RETRYABLE` | 409 | no | `{job_id,status}` | retry button disabled |
| Job | `JOB_NOT_RESUMABLE` | 409 | no | `{job_id,reason_code}` | resume button disabled |
| SSE | `EVENT_GAP` | 409 | yes | `{job_id,last_event_id,next_available_seq}` | refetch job + show stream gap |
| Dataset | `DATASET_NOT_APPROVED` | 409 | after review | `{dataset_id,status}` | training locked reason |
| Dataset | `TRAIN_EVAL_OVERLAP` | 409 | after split edit | `{dataset_id,eval_set_id,overlap_count}` | eval freeze blocked |
| Teacher | `TEACHER_PACKET_APPROVAL_REQUIRED` | 409 | after approval | `{dataset_id,reason_code}` | open packet approval modal |
| Teacher | `TEACHER_PACKET_APPROVAL_EXPIRED` | 409 | after new approval | `{approval_id,expired_at}` | refresh packet preview |
| Teacher | `TEACHER_PACKET_ALREADY_USED` | 409 | after new approval | `{approval_id,used_job_id}` | force new approval |
| Teacher | `TEACHER_PACKET_SHA_MISMATCH` | 409 | after preview refresh | `{approval_id}` | force new preview |
| Credential | `CREDENTIAL_REQUIRED` | 409 | after key save | `{provider}` | settings CTA |
| Credential | `CREDENTIAL_REVOKED` | 409 | after key save | `{provider}` | settings CTA |
| Credential | `KEYCHAIN_UNAVAILABLE` | 503 | after OS/keychain fix | `{provider,platform}` | settings error banner |
| Fallback | `FALLBACK_CREDENTIAL_REQUIRED` | 409 | after runtime env/keychain setup | `{provider,runtime}` | fallback approval blocked |
| Hardware | `HARDWARE_UNSUPPORTED` | 409 | after hardware change | `{gate,reason_code,allowed_backends}` | disabled training CTA |
| Model cache | `MODEL_CACHE_MISS_OFFLINE` | 409 | after network/cache fix | `{model_id,hf_commit_sha,missing_files}` | model download required state |
| Model cache | `MODEL_CACHE_HASH_MISMATCH` | 409 | after redownload | `{model_id,hf_commit_sha,path}` | corrupted cache warning |
| Checkpoint | `CHECKPOINT_DATASET_MISMATCH` | 409 | no | `{checkpoint_id,expected_dataset_id,actual_dataset_id}` | resume disabled reason |
| Checkpoint | `CHECKPOINT_CONFIG_MISMATCH` | 409 | no | `{checkpoint_id,expected_config_hash,actual_config_hash}` | resume disabled reason |
| Checkpoint | `CHECKPOINT_ARTIFACT_MISSING` | 409 | after artifact repair/retrain | `{checkpoint_id,path}` | resume disabled reason |
| Benchmark | `BENCHMARK_TARGET_INVALID` | 422 | after config edit | `{target_key,field,reason}` | target config inline error |
| Benchmark | `BENCHMARK_REPORT_MISSING` | 404 | after job rerun | `{benchmark_id}` | report unavailable state |
| Benchmark | `BENCHMARK_REPORT_HASH_MISMATCH` | 409 | after artifact repair | `{benchmark_id,expected_sha256,actual_sha256}` | hash_mismatch state |
| Export | `EXPORT_ARTIFACT_MISSING` | 500 | yes | `{job_id}` | export failed/retry |
| Export | `EXPORT_HASH_MISMATCH` | 409 | after artifact repair | `{job_id,expected_sha256,actual_sha256}` | export hash_mismatch state |
| Export | `DOCKER_UNAVAILABLE` | 409 | after Docker install | `{export_type}` | disable docker, keep zip enabled |
| Runtime | `AGENT_NOT_FOUND` | 404 | after model/agent id fix | `{agent_id}` | OpenAI-compatible client error |
| Runtime | `STREAMING_NOT_SUPPORTED_V0` | 400 | no | `{endpoint}` | OpenAI-compatible client error |
| Runtime | `SCHEMA_VALIDATION_FAILED` | 422 | after input edit | `{field?, reason}` | playground/output verifier error |
| Artifact | `ARTIFACT_HASH_MISMATCH` | 409 | after rebuild | `{resource_type,resource_id}` | integrity warning |

Any unregistered code is a P1 review issue. Security-sensitive details are redacted before writing both `ErrorResponse.details` and `JobEvent.payload_json`.

### 5.8 Security Implementation Recipes

Security code is split under `services/shared/security/`. A single `core/security.py` is forbidden.

```python
# services/shared/security/auth.py
def validate_bearer_token(request: Request, expected_token: str) -> None:
    token = extract_authorization_bearer(request)
    if not token:
        raise ApiError("AUTH_REQUIRED", status_code=401)
    if not hmac.compare_digest(token, expected_token):
        raise ApiError("AUTH_INVALID", status_code=401)

# services/shared/security/origin.py
def validate_host_origin(request: Request, settings: Settings) -> None:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin")
    if not is_allowed_host(host, settings):
        raise ApiError("HOST_NOT_ALLOWED", status_code=403)
    if origin and not is_allowed_origin(origin, settings):
        raise ApiError("ORIGIN_NOT_ALLOWED", status_code=403)

# services/shared/security/redaction.py
def redact_for_log(value: Any) -> Any:
    # Redact API keys, bearer tokens, known PII entities, file paths when sending to logs/events.
    ...

# services/shared/security/teacher_client.py
def build_teacher_client(base_url: str) -> httpx.Client:
    validated = normalize_and_validate_teacher_origin(base_url)
    transport = PinnedDNSHTTPTransport(validated_origin=validated)
    return httpx.Client(
        base_url=validated.origin,
        transport=transport,
        follow_redirects=False,
        trust_env=False,
        timeout=...,
    )
```

`PinnedDNSHTTPTransport` contract:

```text
- Resolve A/AAAA immediately before opening a socket.
- Reject if any candidate IP is private, loopback, link-local, multicast, unspecified, or metadata range unless the approved origin is explicit localhost self-host.
- Connect only to an IP from the validated candidate set.
- Preserve the original hostname for TLS SNI and the HTTP Host header.
- On DNS set change, re-run SECURITY_SPEC §19.10 steps before connecting.
- Unit tests must monkeypatch DNS so a host validates public first and rebinds to private before connect; the request must fail before socket open.
```

Egress wrapper obligations:

```text
- validate packet against SECURITY_SPEC §19.10 JSON Schema.
- hash packet before sending.
- when creating a `dataset_gen` job with `params.generation_mode='teacher_synthetic'`, require an unexpired TeacherPacketApproval row whose packet_sha256 matches the packet snapshot.
- atomically set TeacherPacketApproval.used_job_id when the `dataset_gen`/`generation_mode=teacher_synthetic` Job row is inserted.
- before egress, require TeacherPacketApproval.used_job_id == current job_id and packet_sha256 == Job.params_json.packet_sha256; do not re-check expiry after reservation.
- write AuditEvent(teacher_egress) before network call with approved_by_user=true and approval_id.
- egress must use `PinnedDNSHTTPTransport`; raw `httpx.Client(base_url=origin)` is forbidden.
- reject redirect responses unless redirect target passes allowlist; v0 default is no redirects.
- sanitize exception messages before JobEvent/error response.
```

Security tests:

```text
test_sse_requires_bearer_with_fetch_stream_client
test_eventsource_without_auth_rejected
test_teacher_redirect_to_private_ip_denied
test_redact_for_log_removes_key_token_pii
test_teacher_packet_schema_rejects_extra_fields
test_teacher_synthetic_requires_packet_approval
test_teacher_packet_sha_mismatch_rejected
test_export_contains_no_credentials
```

---

## 6. DB 구현 순서

DB는 [ARCHITECTURE §24.2](./ARCHITECTURE.md)의 DDL을 기준으로 만든다.

### 6.1 SQLAlchemy model 작성 순서

```text
services/shared/db/models/preset.py: Preset
services/shared/db/models/project.py: Project, ProjectRoute
services/shared/db/models/dataset.py: Dataset, Example
services/shared/db/models/eval.py: EvalSet, Benchmark, EvalRun
services/shared/db/models/hardware.py: HardwareProfile
services/shared/db/models/credential.py: Credential
services/shared/db/models/job.py: Job, JobEvent, JobResource, TeacherPacketApproval
services/shared/db/models/training.py: ModelRun, Checkpoint
services/shared/db/models/package.py: AgentPackage, ExportArtifact
services/shared/db/models/audit.py: AuditEvent
```

`services/shared/db/models/__init__.py` exports all ORM classes for Alembic metadata discovery only. New relationships must be declared in the owning domain file; do not move domain logic into `__init__.py`.

Repository ownership:

| Module | Writers |
|---|---|
| `repositories/job_store.py` | `submit_job`, `claim_next_job`, `emit_event`, `cancel_job`, `retry_job`, `resume_job`, `reconcile_interrupted`, JobResource current-link helpers |
| `repositories/idempotency_store.py` | canonical body hash, expired-key release, replay/mismatch decision |
| `repositories/dataset_store.py` | Worker-owned dataset_gen output rows, Example review status, Dataset approval invariants |
| `repositories/training_store.py` | Worker-owned ModelRun/Checkpoint status, adapter paths, checkpoint resume flags |
| `repositories/benchmark_store.py` | Worker-owned Benchmark/EvalRun target rows, metrics, report hash/status |
| `repositories/export_store.py` | Worker-owned ExportArtifact manifest/artifact hashes and status |
| `repositories/hardware_store.py` | Worker-owned HardwareProfile upsert from hardware_scan result |

API services may call repositories for submit/read orchestration. Worker job loop/handlers may call only the shared repositories listed above. Worker code must not import `services/api/app/services/*`.

### 6.2 필수 테스트

```text
test_migration_upgrade_downgrade
test_foreign_key_check_clean
test_seed_router_preset
test_project_route_unique_per_project
test_job_idempotency_partial_unique
test_job_idempotency_system_scope_for_null_project
test_job_resource_current_unique
test_train_submit_creates_model_run_job_resource
test_retry_resume_rebinds_model_run_job_resource
test_only_one_running_gpu_job
test_job_event_seq_unique_per_job
test_dataset_approved_required_for_train
test_checkpoint_resume_hash_match
test_invariant_eval_set_frozen_before_teacher_job
test_invariant_backend_matches_hardware_gate
test_invariant_method_matches_backend
test_invariant_agent_package_immutable
test_no_plaintext_credential_in_db
```

### 6.3 SQLAlchemy model template

모든 모델은 naming convention과 explicit constraint 이름을 사용한다.

```python
metadata = MetaData(naming_convention={
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})

class Base(DeclarativeBase):
    metadata = metadata

class Job(Base):
    __tablename__ = "job"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    idempotency_body_sha256: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("json_valid(params_json)", name="job_params_json_valid"),
        CheckConstraint("status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')", name="job_status"),
        Index(
            "ux_job_idempotency_project",
            "project_id", "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL AND project_id IS NOT NULL"),
        ),
        Index(
            "ux_job_idempotency_system",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL AND project_id IS NULL"),
        ),
    )
```

### 6.4 SQLite engine setup

```python
engine = create_engine(settings.database_url, future=True)

@event.listens_for(engine, "connect")
def set_sqlite_pragmas(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
```

### 6.5 Alembic initial revision skeleton

```python
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None

def upgrade() -> None:
    op.create_table(...)
    op.create_index(...)
    op.execute("PRAGMA foreign_key_check")

def downgrade() -> None:
    op.drop_index(...)
    op.drop_table(...)
```

`schema_migration`은 앱 내부 감사용 테이블이고, Alembic의 `alembic_version`을 대체하지 않는다.

### 6.6 트랜잭션 규칙

```text
- route handler는 짧은 DB transaction만 사용한다.
- Worker handler는 긴 학습 작업 중 DB transaction을 열어두지 않는다.
- artifact write는 DB transaction 밖에서 수행하고, 성공 후 짧은 transaction으로 상태를 갱신한다.
- Job claim/reconcile은 BEGIN IMMEDIATE를 사용한다.
```

---

## 7. Job/Worker 구현

### 7.1 Worker loop pseudocode

```python
def run_worker():
    worker_id = load_or_create_worker_id()
    while True:
        job = claim_next_job(worker_id)
        if job is None:
            sleep(1.0)
            continue

        emit(job, "status_change", {"status": "RUNNING"})
        try:
            handler = get_handler(job.type)
            handler(job, WorkerContext(worker_id=worker_id))
            # Handler/store owns terminal success. It must update Job,
            # secondary resource row, and terminal JobEvent together.
        except Cancelled:
            terminal_store_for(job.type).mark_cancelled(job)
        except KnownJobError as exc:
            terminal_store_for(job.type).mark_failed(job, exc.error_class, str(exc))
        except Exception as exc:
            terminal_store_for(job.type).mark_failed(job, "UNKNOWN", safe_message(exc))
```

### 7.2 Handler 책임

| Job type | Handler | Phase | 책임 |
|---|---|---|---|
| `hardware_scan` | `hardware_scan.py` | M1 | OS/GPU/RAM 탐지, dry-run stub 또는 real scan |
| `dataset_gen` | `dataset_gen.py` | M1/M2 | user examples → dataset JSONL, later teacher synthetic |
| `train` | `train_cuda.py`, `train_mlx.py` | M3 | backend별 LoRA 학습, checkpoint, adapter |
| `eval` | `eval_run.py` | M4 | ad-hoc one target x seed 평가; benchmark handler may import evaluator function but does not enqueue child eval jobs |
| `benchmark` | `benchmark.py` | M4 | parent benchmark job owns target×seed loop, EvalRun status updates, aggregation, report 생성 |
| `export` | `export.py` | M6 | zip/Docker artifact 생성 |

### 7.3 JobEvent payload schemas

`JobEvent.payload_json` is discriminated by `job.type` and `event_type`. `JobRead.progress_json` is derived from the latest valid payload plus terminal job status.

Common fields:

```json
{
  "schema_version": "job_event.v1",
  "phase": "queued|preflight|running|writing_artifact|verifying|completed|failed",
  "message": "user-safe summary",
  "percent": 0.0
}
```

Type-specific payloads:

| Job.type | Required payload keys | Notes |
|---|---|---|
| `hardware_scan` | `phase`, `gate`, `backend_recommendation`, `training_enabled`, `reason_code`, `dry_run` | `gate` is G0/G1/G2. |
| `dataset_gen` | `phase`, `generation_mode`, `validated_count`, `generated_count`, `rejected_count`, `packet_sha256` | raw examples and source file paths are forbidden. |
| `train` | `phase`, `model_run_id`, `step`, `total_steps`, `loss`, `vram_gb`, `tokens_per_sec`, `checkpoint_id` | `checkpoint_id` nullable except artifact events. |
| `eval` | `phase`, `eval_set_id`, `target_key`, `target_type`, `backend`, `seed`, `completed_examples`, `total_examples` | no raw prompt/input text. |
| `benchmark` | `phase`, `benchmark_id`, `target_key`, `seed`, `completed_runs`, `total_runs`, `parity_status` | report path is emitted only after hash verification. |
| `export` | `phase`, `export_artifact_id`, `agent_package_id`, `export_type`, `manifest_sha256`, `artifact_sha256` | manifest/artifact hashes nullable until verification. |

Example training event:

```json
{
  "schema_version": "job_event.v1",
  "phase": "running",
  "message": "training step",
  "percent": 13.33,
  "model_run_id": "01J...",
  "step": 120,
  "total_steps": 900,
  "loss": 0.8123,
  "vram_gb": 10.4,
  "tokens_per_sec": 115.2,
  "checkpoint_id": null
}
```

`payload_json`에는 API key, raw PII, full input text를 넣지 않는다.

### 7.4 Job Store Contract

| Method | Preconditions | Transaction | Postconditions |
|---|---|---|---|
| `submit_job` | DTO valid, idempotency checked | short write | Job QUEUED, first JobEvent(status_change) |
| `claim_next_job` | worker alive | `BEGIN IMMEDIATE` | one Job RUNNING or none |
| `emit_event` | job exists | short write | JobEvent seq increments by 1; if event_type=`heartbeat`, Job.heartbeat_at is updated in the same transaction |
| `complete_job_with_resource` | job RUNNING, artifact/resource verified | short write | owning store updates Job terminal status, secondary resource terminal status/hash, current JobResource, and terminal JobEvent in one transaction |
| `mark_failed` | job RUNNING | short write | status FAILED, error_class set |
| `cancel_job` | job QUEUED/RUNNING | short write | QUEUED→CANCELLED or cancel_requested_at set |
| `retry_job` | job FAILED/INTERRUPTED/CANCELLED | short write | child Job QUEUED, parent_job_id set |
| `resume_job` | train job has valid checkpoint | short write | child Job QUEUED with checkpoint_id param |
| `reconcile_interrupted` | heartbeat expired | `BEGIN IMMEDIATE` | RUNNING→INTERRUPTED |

`claim_next_job` must catch unique-index collisions from `ux_one_running_gpu_job`, rollback, sleep/backoff, and then try the next eligible CPU job before idling.

Heartbeat/reconcile contract:

```text
- Worker emits a heartbeat event at least every 10s while a job is RUNNING, and also emits heartbeat before and after any child process section expected to exceed 10s.
- Heartbeat payload contains only `{phase, percent?, resource_id?}`; raw prompts, credentials, and file contents are forbidden.
- `job_store.emit_event(event_type='heartbeat')` updates Job.heartbeat_at and inserts JobEvent in one transaction.
- Daemon reconcile runs at startup and every 15s. It selects RUNNING jobs where heartbeat_at is null or older than now()-60s.
- Reconcile uses `job_store.reconcile_interrupted` and the relevant owner store so Job.status and the secondary resource status become INTERRUPTED together.
- Reconcile writes one sanitized JobEvent(error/status_change) and one AuditEvent(event_type='job_reconcile', action='interrupt').
```

---

## 8. M1 Core 구현 티켓

M1은 전체 앱의 vertical slice다. 학습/teacher가 없어도 프로젝트와 데이터셋이 실제 DB와 파일에 남아야 한다.

### M1-001 API bootstrap

```text
Files:
- services/api/app/main.py
- services/api/app/core/config.py
- services/api/app/core/errors.py
- services/shared/security/auth.py
- services/shared/security/origin.py
- services/shared/security/redaction.py

Done:
- /healthz 200
- bootstrap token flow implemented end-to-end: daemon binds `127.0.0.1:0`, prints exactly one `MIB_BOOTSTRAP` line, Tauri exposes `get_api_bootstrap`, FE API client attaches `Authorization: Bearer`.
- `MIB_DEV_AUTH=bootstrap|token_file|bypass` rules enforced exactly as ARCHITECTURE §9.6.1/SECURITY_SPEC §19; production accepts only `bootstrap`.
- Host/Origin middleware runs before route handlers, CORS preflight returns 204 without auth only after allowlist validation, and request body size limit applies before handler code.
- `/healthz` is the only unauthenticated production endpoint.
- missing/invalid token, disallowed Host, disallowed Origin, and dev-bypass-in-prod each have API tests.
- standard error handler
- trace_id response header
- app auth token is never written to log, DB, JobEvent, AuditEvent, keychain, `.env`, or `.mib-dev-token` except dev-only `token_file` mode. HF model-catalog tokens are allowed only in local ignored `.env` for Day-0 catalog fill and are never logged or persisted by the app.
```

### M1-002 DB migration + seed preset

```text
Files:
- services/shared/db/models/*.py
- services/shared/db/session.py
- services/shared/db/seed.py
- services/shared/db/migrations/versions/0001_initial.py

Done:
- ARCHITECTURE §24.2 schema 생성
- router.basic.v1 seed
- `presets/model_catalog.yaml` load 가능
```

### M1-003 Project API

```text
Endpoints:
- POST /projects
- GET /projects
- GET /projects/{id}
- PATCH /projects/{id}
- DELETE /projects/{id}

Done:
- Project 생성 시 preset_id가 존재해야 한다.
- `DELETE /projects/{id}`는 hard delete가 아니라 `archived_at=now` soft archive다.
- `GET /projects`는 기본적으로 archived project를 제외하고 `include_archived=true`일 때만 포함한다.
- archived project의 project-scoped mutation은 409 `PROJECT_ARCHIVED`를 반환한다.
- route taxonomy는 ProjectRoute에 저장한다.
```

### M1-004 Preset API

```text
Endpoints:
- GET /presets
- GET /presets/{preset_id}

Done:
- YAML preset → DB seed → API response 일치
- v0는 router만 반환
```

### M1-005 Dataset builder

```text
Input:
- route taxonomy
- user examples >= 20

Output:
- MIB_HOME/projects/{project_id}/datasets/{version}/dataset.jsonl
- Dataset row
- Example rows

Done:
- PRESET_SPEC §15.0 JSONL 형식 준수
- router_output.schema 검증
- sha256/row_count manifest 생성
```

### M1-006 Hardware Doctor v0

```text
Endpoints:
- POST /hardware-doctor/scan
- GET /hardware-doctor/result

Done:
- hardware_scan Job 생성
- HardwareProfile row 생성
- G0/G1/G2 반환
- unsupported GPU면 train button disabled reason 제공
```

### M1-007 Desktop shell + core screens

```text
Screens:
- ProjectList
- ProjectDashboardPage
- ProjectCreateWizard
- RouteTaxonomyEditor
- ExampleGrid
- DatasetBuildResult
- HardwareDoctorPanel
- JobMonitor

Done:
- API client가 bearer token을 붙인다.
- JobMonitor가 SSE 또는 polling으로 JobEvent를 보여준다.
- 앱 재시작 후 Project/Dataset/Job 상태가 유지된다.
```

---

## 9. M2 Teacher Data 구현 티켓

### M2-000 EvalSet freeze prework

Teacher synthetic generation must not start until a frozen pre-teacher holdout exists. v0 separates `teacher_guard` from release benchmark sets so a normal project can start with 20 approved examples without pretending it has a production benchmark.

```text
Endpoints:
- POST /projects/{id}/eval-sets
- GET /projects/{id}/eval-sets
- GET /eval-sets/{id}

Done:
- `purpose='teacher_guard'` EvalSet is created from 20..50 approved pre-teacher examples before any teacher_synthetic dataset_gen job.
- `teacher_guard` proves the pre-teacher holdout was frozen; it is not valid for release benchmark claims.
- `purpose='benchmark_gold'` EvalSet requires 200..300 approved examples, >=3 labelers, and kappa>=0.70. M4 benchmark jobs require this purpose for user-project claims.
- `purpose='finance_reference'` is the fixed finance 6-route acceptance profile used for v0 release/regression; it is separate from arbitrary user projects.
- `test_eval_train_no_overlap` blocks exact duplicate input_sha256 and embedding-similar leakage for benchmark_gold and finance_reference.
- EvalSet.frozen_at, sha256, purpose, labeler_ids, kappa, and route_snapshot_sha256 are recorded.
```

### M2-001 Credential storage

```text
Files:
- services/api/app/services/credential_service.py
- services/api/app/routes/credentials.py

Done:
- keyring에 API key 저장
- DB에는 keychain_ref만 저장
- GET /credentials는 key 값을 절대 반환하지 않음
```

### M2-002 Teacher Packet Preview

```text
Input:
- rules
- schema
- approved examples

Output:
- packet preview JSON
- TeacherPacketApproval row with `approved_at=NULL`
- pii_mask audit event

Done:
- SECURITY_SPEC §19.1 전송/비전송 항목을 UI에 표시
- 원본 파일 경로/원본 CSV 전체 전송 금지
- 사용자가 승인하면 `POST /teacher-packets/{id}/approve`가 `approved_at`, `packet_sha256`, `expires_at=now+30m`을 기록
- 승인 전 또는 만료 후 `dataset_gen` + `generation_mode=teacher_synthetic` job 생성은 409 `TEACHER_PACKET_APPROVAL_REQUIRED`
```

### M2-003 Synthetic generation

```text
Done:
- BYO OpenAI-compatible base_url allowlist 적용
- `DatasetGenParams.teacher_packet_approval_id`가 unexpired이고 packet_sha256이 재계산값과 일치해야 함
- response JSON schema validation
- generated examples는 approved=false로 저장
- 사용자가 approve/reject/edit 후 dataset v1 저장
```

---

## 10. M3 Training 구현 티켓

### M3-000 Model cache service

```text
Files:
- services/shared/model_catalog.py
- services/worker/model_cache.py
- tests/training/test_model_cache.py

Done:
- `model_catalog.py` loads `presets/model_catalog.yaml`, validates the strict manifest with no `M1_DAY0_FILL`, and exposes model metadata by id.
- `model_cache.py::ensure_model(base_model, backend, purpose)` downloads every required file into `.mib-home/model_cache/{model_id_sanitized}@{hf_commit_sha}/`.
- All downloads use pinned HF commit SHA, never branch names or floating tags.
- A per-model lock file prevents concurrent shard downloads from prompt_only/train/eval jobs.
- Existing cached files are SHA256-verified before use.
- Hash mismatch moves the bad file to `.mib-home/model_cache/quarantine/{timestamp}/` and returns `MODEL_CACHE_HASH_MISMATCH`.
- `MIB_OFFLINE=1` with missing files returns `MODEL_CACHE_MISS_OFFLINE`.
- Tests cover cache hit, cache miss download plan, strict manifest placeholder rejection, lock contention, offline miss, and quarantine on hash mismatch.
```

### M3-001 Training preflight

```text
Done:
- Dataset.status='APPROVED' 아니면 train job 거부
- HardwareProfile capability_gate 검사
- base_model이 `presets/model_catalog.yaml`에 있어야 함
- `model_cache_service.ensure_model(base_model, backend, purpose)` resolves `presets/model_catalog.yaml`, downloads every required file when absent, writes to `.mib-home/model_cache/{model_id_sanitized}@{hf_commit_sha}/`, and verifies SHA256 before returning a local path.
- `ensure_model` uses a per-model file lock so concurrent prompt_only/train/eval jobs do not download the same shard twice.
- `ensure_model` never uses floating HF refs; all downloads use the pinned `hf_commit_sha`.
- If `MIB_OFFLINE=1`, missing cache files return 409 `MODEL_CACHE_MISS_OFFLINE` with `{model_id, hf_commit_sha, missing_files}`.
- If a cached file hash mismatches, quarantine it under `.mib-home/model_cache/quarantine/` and return 409 `MODEL_CACHE_HASH_MISMATCH`.
- Dataset.route_snapshot_sha256 must match every approved Example input.allowed_routes order.
- submit transaction creates ModelRun(status='QUEUED'), Job(type='train'), current JobResource(resource_type='model_run'), and returns `created_resource_type='model_run'`
```

### M3-002 CUDA wrapper

```text
Backend:
- LLaMA-Factory
- torch 2.4.1/cu121
- QLoRA/bitsandbytes

Done:
- generated training config 저장
- stdout log → JobEvent(log)
- loss/vram/tokens_per_sec → JobEvent(metric)
- adapter artifact + adapter_sha256 + artifact_manifest_sha256 기록
```

### M3-003 MLX wrapper

```text
Backend:
- mlx-lm
- 4-bit LoRA

Done:
- CUDA path와 동일 dataset JSONL 사용
- backend='mlx', method='mlx_lora'
- M4 parity용 metadata 기록
```

### M3-004 Cancel/resume

```text
Files:
- services/worker/checkpoint_writer.py
- services/shared/db/repositories/training_store.py
- services/api/app/services/job_control_service.py
- tests/training/test_checkpoint_resume.py

Done:
- DELETE /jobs/{id}가 cancel_requested_at 설정
- Worker가 cooperative cancel 확인
- checkpoint artifact is written atomically with temp→fsync→rename and then recorded in Checkpoint.
- checkpoint metrics_json includes step, loss, adapter_sha256_at_step, optimizer_state_present, rng_state_present, and trainer_backend.
- resume allowed only when Checkpoint.dataset_id == ModelRun.dataset_id, Checkpoint.dataset_version == Dataset.version, and Checkpoint.training_config_hash == ModelRun.config_hash.
- missing checkpoint file returns 409 `CHECKPOINT_ARTIFACT_MISSING` and keeps original job terminal state unchanged.
- dataset mismatch returns `CHECKPOINT_DATASET_MISMATCH`; config mismatch returns `CHECKPOINT_CONFIG_MISMATCH`.
- if optimizer/RNG state is unavailable, resume may continue only with explicit UI warning and a new eval seed group; audit event records `optimizer_rng_missing=true`.
- resumed child job copies parent model_run_id, checkpoint_id, and increments attempt_count.
- tests cover dataset mismatch, config mismatch, missing artifact, optimizer/RNG warning, and successful resume from checkpoint.
```

---

## 11. M4 Eval / Benchmark 구현 티켓

### M4-001 Eval set freeze

```text
Done:
- M2-000 EvalSet API/service/tests are reused.
- M4 verifies EvalSet.purpose in {'benchmark_gold','finance_reference'}, frozen_at, sha256, labeler_ids, kappa, and route_snapshot_sha256 before creating benchmark jobs.
- teacher synthetic 생성 이후 eval set 수정 금지
```

### M4-002 Eval runner

```text
Targets:
- prompt_only
- fine_tuned
- teacher
- rule_based
- optional local_large

Done:
- required target_key x seed 별 EvalRun row 생성
- CUDA/MLX parity는 `target_type='fine_tuned'` target_key 두 개 이상(`backend='cuda'`, `backend='mlx'`)으로 저장한다.
- EvalParams.target은 BenchmarkTargetConfig와 동일 검증을 사용한다.
- local_large는 하드웨어가 가능하면 seed별 EvalRun 생성, 불가능하면 seed=0 `SKIPPED_OPTIONAL` EvalRun 1행 생성 + `metrics_json.skip_reason` 기록
- metrics_json에 Router metrics 기록
- latency p50/p95/p99 기록
```

### M4-003 Benchmark report

```text
Done:
- >=3 seed 평균/SD/95% CI
- fallback 포함 effective cost/task
- `benchmark_report.json` 자동 생성
- report `eval_set` object includes `purpose`, `route_snapshot_sha256`, `sample_count`, `kappa`, and only accepts `benchmark_gold|finance_reference`
- completed report target object includes `target_key`, `target_type`, `target_status`, `backend`, `model_run_id`, `seeds`, `mean_metrics`, `std_metrics`, and `ci95`
- failed target object records `target_status='FAILED'`, `error_reason`, and no metric objects
- skipped optional local_large target object records `target_status='SKIPPED_OPTIONAL'`, `seeds=[0]`, `skip_reason`, and no metric objects
- `target_status=COMPLETED|FAILED|SKIPPED_OPTIONAL` 기록
- `report_sha256` 기록 및 `GET /benchmarks/{id}/report`에서 재계산 검증
- 수기 metric 입력 UI 없음
```

---

## 12. M5 Playground / Agent Package 구현 티켓

### M5-001 Agent contract builder

```text
Endpoints:
- POST /projects/{id}/agent-packages
- GET /projects/{id}/agent-packages
- GET /agent-packages/{id}

Done:
- AGENT_CONTRACT_SPEC §18.1 schema validation
- AgentPackageCreate.model_run_id and benchmark_id must belong to the same project, Benchmark.status must be `COMPLETED`, and Benchmark hash_status must be `VALID`; `report_sha256` existence alone is not enough
- Server allocates `contract_version = max(project contract_version)+1` and `agent_id = {agent_slug or slug(project.name)}.v{contract_version}`.
- Contract includes immutable `route_catalog` from the ModelRun Dataset.route_snapshot_json; route_catalog.sha256 equals Dataset.route_snapshot_sha256 and AgentPackage.route_catalog_sha256.
- AgentPackageCreate.fallback을 contract.fallback에 그대로 반영하고 enabled fallback은 provider/model/condition을 명시 검증
- contract_sha256 기록. Hash input is canonical parsed contract JSON, not raw YAML bytes: parse YAML, validate schema, serialize with sorted keys and compact separators, then SHA256 UTF-8 bytes.
- AgentPackage immutable row 생성
- contract_yaml contains adapter/hash, route_catalog, verifiers, fallback, audit, benchmark_report, export_compatibility
- AgentPackageRead returns `agent_id`, `benchmark_id`, `route_catalog_sha256`, and `contract_yaml` so FE can render contract confirmation without rebuilding it client-side
```

### M5-002 Verifier

```text
Checks:
- JSON parse
- router_output.schema
- route in contract.route_catalog.routes[].route_id
- confidence in [0,1]
- confidence threshold fallback condition
```

### M5-003 Playground

```text
Endpoint:
- POST /agent-packages/{id}/playground-runs

Done:
- user input → local runtime inference
- JSON response 표시
- verifier pass/fail 표시
- fallback은 사용자 승인 전 호출하지 않음
- enabled fallback resolves local credentials from OS keychain by provider; missing key returns 409 `FALLBACK_CREDENTIAL_REQUIRED`
- Local Daemon에는 `/agents/{agent_id}/run`을 만들지 않는다. 해당 route는 exported runtime 전용이다.
```

---

## 13. M6 Export 구현 티켓

### M6-001 Zip export

```text
Files:
- packages/agent-runtime/templates/zip_runtime/agents/run.py
- packages/agent-runtime/templates/zip_runtime/agents/verifier.py
- packages/agent-runtime/templates/zip_runtime/agents/fallback.py
- packages/agent-runtime/templates/zip_runtime/agents/security.py
- packages/agent-runtime/templates/zip_runtime/requirements-runtime.txt
- packages/agent-runtime/loaders/transformers_lora.py
- packages/agent-runtime/loaders/mlx_lora.py
- packages/agent-runtime/tests/test_exported_runtime_smoke.py
- services/worker/handlers/export.py

Local Daemon endpoints:
- POST /projects/{id}/export
- GET /exports/{job_id}
- GET /exports/{job_id}/artifact
- POST /exports/{job_id}/reveal

Contents:
- adapter/
- runtime/
  - agents/run.py              # ASGI app exposing exported endpoints
  - agents/verifier.py
  - agents/fallback.py
  - agents/security.py
- requirements-runtime.txt     # exact pins for exported runtime
- README_RUN.md                # local zip runtime command
- schemas/
- agent_contract.yaml
- route_catalog.json
- benchmark/report.json
- licenses/                   # Gemma Terms notice when base_model is Gemma
- manifest.json

M0 scaffold status:
- `packages/agent-runtime/*` files are contract placeholders. They are not M6 acceptance evidence until real adapter loading and inference are implemented.
- M0 contract status: these files may remain placeholders. M0 acceptance requires this section to define runtime behavior, loader contracts, manifest rules, security controls, and required tests. Real adapter loading/inference is implemented and proven in M6.

M6 acceptance criteria:
- Docker 미설치 환경에서도 zip export 성공
- Zip export is runnable with `MIB_MODEL_CACHE_DIR=<strict-cache> MIB_RUNTIME_BEARER_TOKEN=<32+ chars> python -m uvicorn agents.run:app --host 127.0.0.1 --port 8000` after installing `requirements-runtime.txt`.
- `agents.run:app` loads the exported adapter and base-model metadata through a backend-specific loader (`transformers_lora` for CUDA, `mlx_lora` for MLX) before serving requests.
- `/agents/{agent_id}/run` executes real adapter inference, then validates the response against `schemas/router_output.schema.json`.
- `/v1/chat/completions` converts the OpenAI-compatible request into the native router input, executes the same adapter path, and returns equivalent route/confidence JSON in the assistant message.
- Export artifacts do not bundle base-model weights and do not download from Hugging Face at runtime. The user must provide a read-only strict model cache via `MIB_MODEL_CACHE_DIR`.
- Startup validates every `base_model.required_files[]` entry in `MIB_MODEL_CACHE_DIR/{model_id_sanitized}@{hf_commit_sha}/` before binding a port; missing or hash-mismatched files fail startup with `MODEL_CACHE_MISSING` or `MODEL_CACHE_HASH_MISMATCH`.
- export job transaction creates ExportArtifact(status='QUEUED') and returns `created_resource_type='export'`
- manifest sha256 and artifact sha256 are stored in ExportArtifact after verification
- ExportParams.agent_package_id는 필수이며, export job params에 저장한다.
- `GET /exports/{job_id}` returns ExportRead from ExportArtifact, not AgentPackage mutable fields
- `GET /exports/{job_id}/artifact` and `POST /exports/{job_id}/reveal` require ExportArtifact.status='SUCCEEDED' and artifact hash recomputation success
- `tests/export/test_exported_runtime_smoke.py` starts the zip runtime with `uvicorn agents.run:app`, sends native and OpenAI-compatible requests, verifies bearer auth, verifies `NativeRunResponse.output` against output_schema, and checks route_allowed fallback behavior.
- `tests/export/test_exported_adapter_load.py` must fail if `run.py` returns hardcoded routes or if either loader only returns metadata without invoking the backend inference library.
```

Base model materialization:

```text
- `model_cache_service.ensure_model()` owns downloads before export. Exported runtimes are offline-by-default and never fetch HF files at process startup or request time.
- The export job writes `base_model_manifest.json` from the strict catalog subset for the AgentPackage base model.
- `manifest.json.base_model.cache_subdir` is `{model_id_sanitized}@{hf_commit_sha}` where `/` in the model id is replaced by `__`.
- Zip runtime command must set `MIB_MODEL_CACHE_DIR` to the directory containing `cache_subdir`.
- Docker runtime command must mount the same cache read-only, e.g. `-v ~/.mib-home/model_cache:/models:ro -e MIB_MODEL_CACHE_DIR=/models`.
- Runtime validation reads only files listed in `manifest.json.base_model.required_files`; extra files are ignored but never trusted for hash decisions.
- If `base_model.id` uses Gemma, `licenses/GEMMA_TERMS_NOTICE.txt` is required in the artifact, but Gemma terms acceptance is not stored in the package.
```

Adapter artifact shape:

```text
- `adapter.format='lora_adapter'` (CUDA/Transformers) requires `adapter/adapter.safetensors` and `adapter/adapter_config.json`.
- `adapter.format='mlx_lora_adapter'` (Apple Silicon/MLX) requires `adapter/adapters.npz` and `adapter/adapter_config.json`.
- Export worker must fail with 409 `EXPORT_ADAPTER_FORMAT_MISMATCH` if the ModelRun backend/method and adapter files do not match the AgentContract adapter.format.
- Zip export supports both formats. Docker export supports only `lora_adapter` in v0; `mlx_lora_adapter` returns 409 `DOCKER_UNAVAILABLE`.
```

Export `manifest.json` schema:

```json
{
  "schema_version": "export_manifest.v1",
  "agent_package_id": "01J...",
  "agent_id": "support_router.v1",
  "contract_sha256": "64hex",
  "route_catalog_sha256": "64hex",
  "benchmark_report_sha256": "64hex",
  "export_type": "zip",
  "created_at": "2026-06-21T00:00:00Z",
  "adapter": {
    "format": "lora_adapter",
    "required_paths": ["adapter/adapter.safetensors", "adapter/adapter_config.json"]
  },
  "base_model": {
    "id": "google/gemma-2b-it",
    "hf_commit_sha": "0123456789abcdef0123456789abcdef01234567",
    "materialization": "external_cache",
    "cache_env": "MIB_MODEL_CACHE_DIR",
    "cache_subdir": "google__gemma-2b-it@0123456789abcdef0123456789abcdef01234567",
    "required_files": [
      {"path": "config.json", "sha256": "64hex", "size_bytes": 1234},
      {"path": "tokenizer.json", "sha256": "64hex", "size_bytes": 1234},
      {"path": "tokenizer_config.json", "sha256": "64hex", "size_bytes": 1234},
      {"path": "model-00001-of-00002.safetensors", "sha256": "64hex", "size_bytes": 1234},
      {"path": "model-00002-of-00002.safetensors", "sha256": "64hex", "size_bytes": 1234}
    ]
  },
  "runtime": {
    "native_endpoint": "/agents/{agent_id}/run",
    "openai_endpoint": "/v1/chat/completions",
    "entrypoint": "agents.run:app",
    "run_command": "python -m uvicorn agents.run:app --host 127.0.0.1 --port 8000",
    "compatible_backends": ["cuda"],
    "requires_bearer_token_env": "MIB_RUNTIME_BEARER_TOKEN",
    "requires_bearer_token_min_length": 32
  },
  "files": [
    {"path": "agent_contract.yaml", "role": "agent_contract", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "route_catalog.json", "role": "route_catalog", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "benchmark/report.json", "role": "benchmark_report", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "base_model_manifest.json", "role": "model_manifest", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "schemas/router_input.schema.json", "role": "input_schema", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "schemas/router_output.schema.json", "role": "output_schema", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "adapter/adapter.safetensors", "role": "adapter", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "adapter/adapter_config.json", "role": "adapter_config", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "runtime/agents/run.py", "role": "runtime_entrypoint", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "runtime/agents/verifier.py", "role": "runtime_code", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "requirements-runtime.txt", "role": "runtime_requirements", "sha256": "64hex", "size_bytes": 1234, "required": true},
    {"path": "licenses/GEMMA_TERMS_NOTICE.txt", "role": "license_notice", "sha256": "64hex", "size_bytes": 1234, "required": false}
  ]
}
```

Manifest rules:

```text
- `schemas/export_manifest.schema.json` is the committed JSON Schema artifact.
- `manifest.json` must validate before writing ExportArtifact.manifest_path.
- Manifest files must include required roles: agent_contract, route_catalog, input_schema, output_schema, benchmark_report, model_manifest, adapter, adapter_config, runtime_entrypoint, runtime_code, runtime_requirements. Gemma packages must include a license_notice role.
- Manifest `base_model.required_files` must match the strict catalog for `base_model.id` and `hf_commit_sha`; runtime validates those files under `MIB_MODEL_CACHE_DIR`.
- File paths are relative to export artifact root and must not contain `..`, absolute paths, user home paths, or secrets.
- `files[].sha256` is computed from exact file bytes before archive/container build.
- `manifest_sha256` is computed by serializing manifest with `json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` and SHA256 hashing the UTF-8 bytes.
- Zip `artifact_sha256` is the final zip file SHA256. Docker `artifact_sha256` is the saved image tar SHA256. v0 has no registry push extension field.
- Tests: `test_export_manifest_schema`, `test_export_manifest_hash_canonical`, `test_export_manifest_rejects_absolute_path`, `test_export_contains_no_credentials`, `test_export_manifest_base_model_cache_contract`, `test_export_rejects_adapter_format_mismatch`.
```

### M6-002 Docker local API export

```text
Files:
- packages/agent-runtime/templates/docker/Dockerfile.cuda
- packages/agent-runtime/tests/test_docker_export_security.py
- services/worker/handlers/export_docker.py

Exported runtime endpoint, not Local Daemon:
- POST /agents/{agent_id}/run
- POST /v1/chat/completions

M6 acceptance criteria:
- /agents/{agent_id}/run endpoint
- OpenAI-compatible non-streaming `/v1/chat/completions` endpoint per AGENT_CONTRACT_SPEC §18.2
- Authorization bearer token uses `MIB_RUNTIME_BEARER_TOKEN`; package contains no Local Daemon token
- input_schema/output_schema 검증
- 동일 입력 deterministic response smoke test
- stream=true returns 400 `STREAMING_NOT_SUPPORTED_V0`
- missing fallback env returns 409 `FALLBACK_CREDENTIAL_REQUIRED`
- Docker export is required for CUDA/transformers packages only in v0. MLX packages are zip-runtime only on macOS; Docker export for `adapter.format='mlx_lora_adapter'` returns 409 `DOCKER_UNAVAILABLE` with `details.export_type='docker'`.
- Dockerfile uses a pinned base image digest, non-root user, explicit exposed port, healthcheck, no local daemon token, and `MIB_RUNTIME_BEARER_TOKEN`/fallback keys only via runtime env.
- Docker image must not contain base-model weights. Docker run documentation mounts `MIB_MODEL_CACHE_DIR` read-only and the runtime verifies strict hashes before serving.
- Docker smoke runs the saved image tar with a read-only model-cache mount, verifies `/agents/{agent_id}/run` and `/v1/chat/completions`, runs export secret scan on the build context and image tar/layers, and records SBOM/CVE evidence.
- M6 CI requires `tests/export` to cover manifest schema validation, required file roles, zip runtime smoke, real adapter load/inference, Dockerfile non-root/base digest checks, SBOM generation, CVE scan evidence, and `scripts/scan_export_artifact.py --artifact <artifact>`.
```

---

## 14. Frontend 구현 기준

### 14.1 화면 목록

| Screen | Phase | 주요 상태 |
|---|---|---|
| ProjectList | M1 | empty/loading/error/ready |
| ProjectDashboardPage | M1 | project summary, next step, recent jobs |
| ProjectCreateWizard | M1 | preset 선택, route 입력 |
| RouteTaxonomyEditor | M1 | 2~12 route, reserved route 안내 |
| ExampleGrid | M1/M2 | user/teacher examples, approve/reject/edit |
| HardwareDoctorPanel | M1 | G0/G1/G2, disabled reason |
| JobMonitor | M1+ | SSE events, cancel, retry |
| TeacherSettings | M2 | key 저장, base_url 설정 |
| TeacherPacketPreview | M2 | 전송 항목/마스킹 확인 |
| TrainingPanel | M3 | backend 선택, preflight, logs |
| BenchmarkReport | M4 | metric table, seeds, CI |
| Playground | M5 | input, output, verifier |
| ExportPanel | M6 | zip/docker export |

### 14.1.1 M1 route tree and shell scope

M1 must include the app shell even when later workflow steps are locked.

```text
/                         -> redirect /projects
/projects                 -> AppShell + ProjectListPage
/projects/new             -> AppShell + ProjectCreateWizard
/projects/:projectId      -> AppShell + ProjectDashboardPage
/projects/:projectId/define -> AppShell + RouteTaxonomyEditor
/projects/:projectId/datasets/new -> AppShell + ExampleGrid
/datasets/:datasetId      -> AppShell + DatasetDetailPage
/hardware                 -> AppShell + HardwareDoctorPanel
/jobs/:jobId              -> AppShell + JobMonitor
/settings                 -> AppShell + SettingsHome
/settings/teacher         -> AppShell + TeacherSettings locked until M2
```

### 14.1.2 Full v0 route tree additions

Later milestones unlock these routes without changing AppShell layout:

```text
/projects/:projectId/training       -> AppShell + TrainingPanel          (M3)
/projects/:projectId/model-runs     -> AppShell + ModelRunListPage       (M3)
/model-runs/:modelRunId             -> AppShell + ModelRunDetailPage     (M3)
/projects/:projectId/benchmarks/new -> AppShell + BenchmarkStartPage     (M4)
/benchmarks/:benchmarkId            -> AppShell + BenchmarkReportPage    (M4)
/projects/:projectId/packages       -> AppShell + AgentPackageListPage   (M5)
/packages/:agentPackageId/playground -> AppShell + PlaygroundPage        (M5)
/projects/:projectId/export         -> AppShell + ExportPanel            (M6)
```

Locked-route behavior:

```text
- Before its milestone prerequisite is satisfied, route access renders the same AppShell with a locked state panel, not a blank page.
- Deep links to locked routes must preserve the target route and show the unlock reason.
- Once prerequisite data exists, the sidebar stepper and route guard unlock in the same state transition.
```

Mandatory M1 shell components:

| Component | Path | M1 behavior |
|---|---|---|
| `AppShell` | `features/shell/AppShell.tsx` | top bar + sidebar + main outlet |
| `ProjectSwitcher` | `features/shell/ProjectSwitcher.tsx` | list projects, selected project, create shortcut |
| `WorkflowStepper` | `features/shell/WorkflowStepper.tsx` | 7 steps, done/current/locked states, locked click shows reason |
| `JobQueueIndicator` | `features/jobs/JobQueueIndicator.tsx` | running/queued count, latest progress, click latest job |
| `HardwareBadge` | `features/hardware/HardwareBadge.tsx` | G0/G1/G2 or unknown state |
| `ConnectionChip` | `features/shell/ConnectionChip.tsx` | local daemon online/offline, teacher connected/locked |

### 14.2 API client

```typescript
type ApiError = {
  error_code: string;
  message: string;
  details: Record<string, unknown>;
  trace_id: string;
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) throw await res.json() as ApiError;
  if (res.status === 204) return undefined as T;
  return await res.json() as T;
}
```

### 14.3 SSE hook

```typescript
function useJobEvents(jobId: string) {
  // Connect to /jobs/{jobId}/events.
  // Store last event id.
  // On EVENT_GAP, refetch /jobs/{jobId}.
  // Never assume event stream is complete without job.status.
}
```

### 14.4 Screen Contracts

| Screen | Route | Owner component | Inputs | API/SSE | Disabled/Error rules | Acceptance tests |
|---|---|---|---|---|---|---|
| ProjectList | `/projects` | `ProjectListPage` | none | `GET /projects` | empty state if no projects, retry on daemon unavailable | `fe_project_list_empty`, `fe_project_list_error` |
| ProjectDashboardPage | `/projects/:id` | `ProjectDashboardPage` | project id | `GET /projects/{id}`, `GET /projects/{id}/datasets`, `GET /projects/{id}/jobs` | archived project shows read-only banner, empty dataset state links to ExampleGrid | `fe_project_dashboard_summary` |
| ProjectCreateWizard | `/projects/new` | `ProjectCreateWizard` | name, preset, routes | `GET /presets`, `POST /projects` | submit disabled until 2~12 valid routes | `fe_create_project_validates_routes` |
| RouteTaxonomyEditor | `/projects/:id/define` | `RouteTaxonomyEditor` | route rows | `GET /projects/{id}`, `PATCH /projects/{id}` | duplicate route_id inline error, reserved route hint, archived/read-only/route-locked project read-only | `fe_route_duplicate_error` |
| ExampleGrid | `/projects/:id/datasets/new` | `ExampleGrid` | >=20 examples | `POST /projects/{id}/datasets` | build disabled until 20 schema-valid examples | `fe_example_grid_min20` |
| DatasetBuildResult | `/datasets/:id` | `DatasetDetailPage` | dataset id | `GET /datasets/{id}` | schema errors are row-level | `fe_dataset_result_rows` |
| HardwareDoctorPanel | `/hardware` | `HardwareDoctorPanel` | scan button | `POST /hardware-doctor/scan`, SSE, `GET /hardware-doctor/result` | train CTA disabled on G0 with reason | `fe_hardware_gates_train_button` |
| JobMonitor | `/jobs/:id` | `JobMonitor` | job id | SSE `/jobs/{id}/events`, `GET /jobs/{id}` | EVENT_GAP triggers refetch banner | `fe_sse_reconnect_event_gap` |
| TeacherSettings | `/settings/teacher` | `TeacherSettings` | provider, base_url, key | credentials API | key never echoed; revoked credential warning | `fe_credentials_masked` |
| TeacherPacketPreview | modal | `TeacherPacketPreview` | packet | preview/generate job | raw source file paths hidden | `fe_packet_preview_no_raw_path` |
| TrainingPanel | `/projects/:id/training` | `TrainingPanel` | backend, model, preset | job submit + SSE | backend disabled if HardwareProfile blocks | `fe_training_preflight_disabled` |
| ModelRunList | `/projects/:id/model-runs` | `ModelRunListPage` | project id | `GET /projects/{id}/model-runs` | empty state links to TrainingPanel | `fe_model_run_list_empty` |
| ModelRunDetail | `/model-runs/:id` | `ModelRunDetailPage` | model_run id | `GET /model-runs/{id}`, `GET /model-runs/{id}/checkpoints` | stale checkpoint resume disabled with reason | `fe_checkpoint_resume_guard` |
| BenchmarkStart | `/projects/:id/benchmarks/new` | `BenchmarkStartPage` | eval_set, targets, seeds | `POST /projects/{id}/jobs` type=benchmark | submit returns benchmark_id; navigate to `/benchmarks/:id` | `fe_benchmark_start_navigates` |
| BenchmarkReport | `/benchmarks/:id` | `BenchmarkReportPage` | benchmark id | `GET /benchmarks/{id}`, `GET /benchmarks/{id}/report`, SSE via job link | unverified parity shows warning | `fe_benchmark_parity_warning` |
| AgentPackageList | `/projects/:id/packages` | `AgentPackageListPage` | project id | `GET /projects/{id}/agent-packages`, `GET /projects/{id}/benchmarks`, `POST /projects/{id}/agent-packages` | create disabled until model_run SUCCEEDED and selected benchmark `hash_status='VALID'`; mismatch opens BenchmarkReport | `fe_package_create_guard` |
| Playground | `/packages/:id/playground` | `PlaygroundPage` | agent_package id, input text/routes | `GET /agent-packages/{id}`, `POST /agent-packages/{id}/playground-runs` | fallback button requires explicit approval and credential | `fe_playground_verifier_states` |
| ExportPanel | `/projects/:id/export` | `ExportPanel` | agent_package id, export type | `GET /projects/{id}/agent-packages`, `POST /projects/{id}/export`, `GET /exports/{job_id}`, SSE | docker disabled if unavailable, zip remains enabled; no package disables submit | `fe_export_zip_without_docker` |

State matrix required for every screen:

```text
loading | empty | ready | locked | validation_error | api_error | offline_daemon | unauthorized | retrying | cancelling | resuming | hash_mismatch | success
```

State entry and CTA rules:

| State | Entry condition | Primary CTA behavior | Exit condition |
|---|---|---|---|
| `loading` | first data request in flight | disabled, spinner only | response or timeout |
| `empty` | 200 with no rows/resource prerequisites | show create/import CTA if route unlocked | user creates prerequisite |
| `ready` | required data loaded and no blocking error | enabled if form-level validation passes | submit/job/hash change |
| `locked` | milestone/prerequisite/route taxonomy/project archive guard blocks action | disabled; show exact unlock reason and source resource id when available | prerequisite satisfied or user navigates |
| `validation_error` | local schema or 422 details field/row error | disabled until field/row fixed | all field/row errors cleared |
| `api_error` | non-auth non-validation API error | retry CTA enabled when retryable registry says yes | retry success or navigation |
| `offline_daemon` | bootstrap unavailable, fetch failed, or SSE unavailable >30s | blocking reconnect CTA; destructive CTAs disabled | `/healthz` and bootstrap recover |
| `unauthorized` | 401 AUTH_REQUIRED/AUTH_INVALID | reconnect/auth repair CTA; all mutations disabled | new bootstrap token accepted |
| `retrying` | `POST /jobs/{id}/retry` in flight | only cancel navigation enabled; duplicate retry disabled | child job accepted or API error |
| `cancelling` | `DELETE /jobs/{id}` in flight | cancel button disabled; monitor remains live | job status changes or API error |
| `resuming` | `POST /jobs/{id}/resume` in flight | resume button disabled; checkpoint selector locked | child job accepted or API error |
| `hash_mismatch` | Benchmark/Export hash recomputation returns mismatch | package/export/download CTAs disabled; repair/rerun CTA shown | rerun succeeds or artifact restored |
| `success` | mutation accepted or terminal success loaded | navigate to next workflow step when specified | next route loading |

Screen-specific hash rules:

```text
- BenchmarkReport enters `hash_mismatch` when BenchmarkRead.hash_status or BenchmarkReportRead.hash_status is MISMATCH.
- AgentPackageList disables create unless selected BenchmarkRead.hash_status == 'VALID'.
- ExportPanel disables download/reveal when ExportRead.status != 'SUCCEEDED' or `GET /exports/{job_id}/artifact` returns EXPORT_HASH_MISMATCH.
- Hash mismatch UI must show expected/actual sha256 from error details when provided and must never offer manual metric/hash editing.
```

Route taxonomy lock:

```text
- ProjectRoute rows are editable only while the project has no Dataset, EvalSet, Job, ModelRun, Benchmark, or AgentPackage rows.
- The first Dataset creation records `Dataset.route_snapshot_json` and locks the project route taxonomy for v0.
- A locked taxonomy renders read-only route rows with the exact lock reason and links to create a new project if a different taxonomy is needed.
- `PATCH /projects/{id}` rejects route edits after lock with 409 `ROUTE_TAXONOMY_LOCKED` and details `{project_id, locked_by_resource_type, locked_by_resource_id}`.
- Example import/build uses the locked ProjectRoute order; FE must not reorder allowed_routes client-side.
```

Full-v0 navigation handoffs:

```text
TrainingPanel:
  POST /projects/{id}/jobs type=train
  -> JobAcceptedResponse.created_resource_type='model_run'
  -> navigate /model-runs/{created_resource_id} or /jobs/{job_id}; both link to each other.

BenchmarkStart:
  POST /projects/{id}/jobs type=benchmark
  -> JobAcceptedResponse.created_resource_type='benchmark'
  -> navigate /benchmarks/{created_resource_id}; page polls GET /benchmarks/{id} and follows job events by job_id from route state or latest project job.

AgentPackageList:
  POST /projects/{id}/agent-packages with model_run_id + benchmark_id
  -> AgentPackageRead includes contract_yaml; show contract confirmation before enabling Playground/Export.

ExportPanel:
  user selects AgentPackageRead.id and export_type
  -> POST /projects/{id}/export
  -> JobAcceptedResponse.created_resource_type='export'
  -> track /jobs/{job_id}/events and GET /exports/{job_id}; completed ExportRead contains manifest_sha256 and artifact_sha256.
```

### 14.4.1 ExampleGrid / Router validation contract

`ExampleGrid` row shape:

```typescript
type RouterExampleRow = {
  client_id: string;
  source: "user" | "teacher" | "import" | "hard_negative" | "eval_gold";
  input_text: string;
  output_route: string;
  output_task_type: "generate_report" | "provide_advice" | "escalate" | "block";
  requires_calculation: boolean;
  requires_human_review: boolean;
  confidence: number;
  approved: boolean;
  errors: Array<{ field: string; code: string; message: string }>;
};
```

Grid columns:

```text
status | input_text | output_route | output_task_type | requires_calculation | requires_human_review | confidence | actions
```

Conversion to API `ExampleInput`:

```typescript
const exampleInput = {
  input: {
    text: row.input_text,
    allowed_routes: project.routes.map((r) => r.route_id)
  },
  output: {
    route: row.output_route,
    task_type: row.output_task_type,
    requires_calculation: row.requires_calculation,
    requires_human_review: row.requires_human_review,
    confidence: row.confidence
  },
  source: row.source === "teacher" ? "import" : row.source
};
```

Validation:

```text
- Zod schemas are generated from `schemas/router_input.schema.json` and `schemas/router_output.schema.json`.
- `output_route` must be one of the current project's route ids.
- `output_task_type` is required.
- `confidence` must be 0..1.
- Build button enabled only when >=20 rows have no errors.
- Import supports JSONL with {instruction,input,output}; CSV import is M2+ unless separately ticketed.
- API 422/409 errors with `details.row_index` and `details.field` map to row-level errors.
- After dataset creation, row approve/reject/edit uses `PATCH /examples/{id}`.
- `review_status='APPROVED'` sets approved=true server-side; `REJECTED` sets approved=false.
- Editing input/output validates router schemas before saving and returns updated ExampleRead with `review_status='EDITED'`.
- Dataset approval uses `PATCH /datasets/{id}` with `approved_example_ids`; server rejects APPROVED status unless at least 20 examples are approved and every approved row is schema-valid.
```

### 14.5 API/SSE Client Contract

Token/bootstrap:

```text
- Tauri starts the Python daemon as a child process and captures stdout.
- Daemon binds `127.0.0.1:0`, generates `secrets.token_urlsafe(32)`, then writes exactly one bootstrap line to stdout:
  MIB_BOOTSTRAP {"base_url":"http://127.0.0.1:{port}","token":"...","pid":1234}
- Daemon must never log the token after this bootstrap line.
- Tauri stores base_url/token in memory only and exposes command `get_api_bootstrap() -> {baseUrl:string, token:string}`.
- FE calls `get_api_bootstrap` once during app startup before creating the API client.
- `MIB_DEV_AUTH=bootstrap` is default and uses stdout bootstrap token.
- `MIB_DEV_AUTH=token_file` may read `.mib-dev-token` in dev only.
- `MIB_DEV_AUTH=bypass` may bypass auth in dev only when daemon binds 127.0.0.1.
- Production accepts only `MIB_DEV_AUTH=bootstrap`; any other value aborts startup.
- If daemon is unavailable, show blocking reconnect screen with retry.
```

HTTP client:

```text
- 204 returns undefined, not JSON parse.
- non-JSON error becomes `{error_code:"NON_JSON_ERROR", message, trace_id}`.
- request timeout default: 30s for normal API, no timeout for SSE.
- job creation requests generate Idempotency-Key unless caller provides one. Non-job POST/PATCH/PUT/DELETE do not send Idempotency-Key in v0.
- 409 validation/idempotency errors map to inline form errors when `details.field` exists.
- trace_id is shown in expandable error details with copy button.
```

SSE client:

```text
- store last seen seq per job.
- ignore duplicate seq.
- reconnect with backoff: 1s, 2s, 5s, 10s, max 30s.
- send Last-Event-ID on reconnect.
- on 409 EVENT_GAP, show banner and refetch `/jobs/{id}`.
- if SSE unavailable for >30s, fallback to polling `/jobs/{id}` every 5s.
- terminal job status from `/jobs/{id}` is the source of truth.
```

FE test stack:

```text
unit: Vitest + React Testing Library
API mock: MSW
e2e: Playwright
a11y: axe
visual smoke: Playwright screenshots for M1 happy path
```

---

## 15. Multi-Agent Peer Review Protocol

마일스톤 종료, 큰 PR, DB/API/LLM 변경 PR은 멀티에이전트 피어 리뷰를 수행한다. 사람 리뷰어가 있으면 사람 팀이 같은 역할을 맡고, 없으면 Codex sub-agent를 생성한다.

### 15.1 언제 실행하는가

```text
- M0/M1/M2/M3/M4/M5/M6 마일스톤 종료 전
- ARCHITECTURE §24 DB schema 변경
- public API/DTO 변경
- Job state machine/worker 변경
- training/eval metric 변경
- security/egress/credential 변경
- release candidate 생성 전
```

### 15.2 필수 리뷰 에이전트

| Agent | Must review | Must not decide alone |
|---|---|---|
| FE Agent | screens, state, form validation, SSE, API client, user-facing errors | DB schema, training metric correctness |
| DB Agent | schema, migration, indexes, FK/CHECK, data lifecycle, artifact references | UI design, model quality |
| BE/API Agent | FastAPI routes, auth, DTO, transaction boundary, Job queue, worker handoff | final benchmark claims |
| LLM/Training Agent | dataset format, chat template, CUDA/MLX wrapper, checkpoint, model artifact | UI layout, auth policy |
| Eval/QC Agent | acceptance criteria, test coverage, benchmark reproducibility, report hash | product positioning |
| Security Agent | keychain, bearer token, egress, PII masking, secret logging, supply chain | UX preference |
| Architecture/Code Quality Agent | layer boundaries, design pattern consistency, file size, god-file risk, dependency direction | product scope, benchmark truth |
| DevEx/Environment Agent | `.venv`, requirements files, IDE interpreter, Docker boundary, toolchain versions | product UX, model quality |
| CTO Integrator | final conflict resolution and GO/NO-GO | bypass blocking issues without written rationale |

### 15.3 Required Reviewers By Change Type

| Change type | Required agents |
|---|---|
| UI route/screen/state/API client/SSE | FE, BE/API, QC |
| SQLAlchemy/Alembic/query/index/job persistence | DB, BE/API, QC |
| FastAPI route/DTO/auth/error handling | BE/API, Security, QC |
| Worker/job state/cancel/retry/resume | BE/API, DB, QC |
| Dataset JSONL/preset/schema | LLM/Training, BE/API, Eval/QC |
| Training wrapper/model catalog/checkpoint | LLM/Training, DB, Security, QC |
| Eval metric/benchmark report/parity | Eval/QC, LLM/Training, Security |
| Credentials/PII/network/provider allowlist | Security, BE/API, FE |
| Requirements/toolchain/IDE/Docker policy | DevEx/Environment, BE/API, LLM/Training, Security |
| Export/package/runtime contract | BE/API, Security, FE, QC |
| New module, large file, refactor, cross-layer import | Architecture/Code Quality, owning layer agent |
| Release candidate | FE, DB, BE/API, LLM/Training, Eval/QC, Security, Architecture/Code Quality, DevEx/Environment, CTO |

### 15.4 Review prompt template

각 에이전트에는 아래 템플릿을 사용한다.

```text
Role: {FE|DB|BE/API|LLM/Training|Eval/QC|Security|Architecture/Code Quality|DevEx/Environment}
Task: Review the changed docs/code for MIB Studio v0.
Scope:
- Files/sections: {explicit paths}
- Phase: {M0|M1|M2|M3|M4|M5|M6}
Rules:
- Do not edit files.
- Judge whether a junior developer can implement this area using only the docs/specs.
- Mark any ambiguity that could cause incompatible implementations as blocking.
- Prefer concrete file/section references.
Return:
Decision: GO | GO_WITH_CONDITIONS | NO_GO
Blocking issues:
Non-blocking issues:
Missing tests:
Spec updates required:
Assumptions:
```

### 15.5 Severity rules

```text
P0: Security/data loss/incorrect benchmark claim/crash on core path. Blocks GO.
P1: Spec ambiguity that can produce incompatible FE/BE/DB/worker implementations. Blocks GO.
P2: Missing useful test, edge state, or DX detail. Does not block if owner/ticket exists.
P3: polish, wording, examples. Never blocks GO.
```

### 15.6 Integration workflow

```text
1. Spawn FE, DB, BE/API, LLM/Training, Eval/QC, Security, Architecture/Code Quality, DevEx/Environment agents in parallel.
2. Continue non-overlapping doc/code cleanup while they review.
3. Collect all reports.
4. Deduplicate issues by root cause.
5. If any P0/P1 exists, mark milestone NO_GO or keep NOT_GO.
6. Patch docs/code for accepted fixes.
7. Re-run targeted agents only for changed scopes.
8. CTO Integrator records final decision in Dev Plan §34.2 or milestone notes.
```

### 15.7 Review artifact format

Save review summaries under `docs/reviews/` when the review gates a milestone.

```text
docs/reviews/
  M0/
    FE_REVIEW.md
    DB_REVIEW.md
    BE_API_REVIEW.md
    LLM_TRAINING_REVIEW.md
    EVAL_QC_REVIEW.md
    SECURITY_REVIEW.md
    ARCH_CODE_QUALITY_REVIEW.md
    DEVEX_ENVIRONMENT_REVIEW.md
    SIGNOFF_MATRIX.md
    CTO_DECISION.md
```

Each review file:

```text
# {Milestone} {Role} Review

Decision:
Reviewer:
Date:
Scope:

## Blocking Issues
## Non-Blocking Issues
## Missing Tests
## Spec Updates Required
## Assumptions
```

### 15.8 Sign-Off Matrix

`SIGNOFF_MATRIX.md` must include:

```text
| Milestone | FE | DB | BE/API | LLM/Training | Eval/QC | Security | Arch/Code | DevEx | CTO | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| M{n} | GO/NO_GO/WAIVED | ... | ... | ... | ... | ... | ... | ... | ... | GO/NOT_GO |
```

Rules:

```text
- WAIVED requires CTO_DECISION.md rationale and owner.
- Any unresolved P0/P1 means milestone NO_GO.
- A spec change after sign-off reopens affected agents only.
- Release candidate requires all agents GO, not GO_WITH_CONDITIONS.
```

### 15.9 M0 peer validation checklist

M0 cannot become GO until these are true.

```text
- FE Agent: M1 screens, UI states, API client, SSE behavior are implementable from docs.
- DB Agent: canonical schema can generate Alembic migration; FK/check/index strategy is unambiguous.
- BE/API Agent: route handlers, DTOs, job claim/reconcile/cancel/event-gap flow are implementable.
- LLM Agent: dataset JSONL, tokenizer/chat template, CUDA/MLX wrapper inputs/outputs are unambiguous.
- Eval/QC Agent: acceptance criteria map to tests; benchmark report cannot be manually fabricated.
- Security Agent: keychain, bearer token, PII masking, egress allowlist are testable.
- Architecture/Code Quality Agent: layer pattern, import direction, file-size budgets, and god-file guardrails are enforceable.
- DevEx/Environment Agent: `.venv`, profile-specific requirements audit, IDE tasks/launch, bootstrap scripts, and Docker export-only boundary are reproducible.
- CTO Integrator: any cross-agent conflict has one documented resolution.
```

---

## 16. Definition of Done per PR

모든 PR은 아래를 만족해야 merge 가능하다.

```text
- 관련 spec link가 PR description에 포함됨
- unit tests 또는 smoke test 추가
- 필요한 경우 §15 멀티에이전트 리뷰 결과 첨부
- §3.1~§3.3 코드 생성/패턴/god-file 체크리스트 통과
- hard limit 초과 파일 없음(마이그레이션/generated 제외)
- 새 cross-layer import가 있으면 Architecture/Code Quality Agent 승인 필요
- FE 변경이면 `pnpm test`, MSW API contract test, Playwright happy path, axe/keyboard check 포함
- DB 변경이면 migration log, sqlite_master dump, `PRAGMA foreign_key_check`, downgrade test 포함
- BE/API 변경이면 `openapi.json` diff, endpoint matrix update, Job lifecycle replay transcript 포함
- LLM/training 변경이면 golden config/tokenizer snapshot, no-GPU config test, hardware-gated smoke plan 포함
- DB 변경이면 Alembic migration 포함
- public API 변경이면 DTO 문서 업데이트
- Job handler 변경이면 JobEvent payload 예시 업데이트
- 보안 관련 변경이면 SECURITY_SPEC 영향 확인 + Security Agent sign-off
- credential/egress/auth 변경이면 security test log, secret scan, egress transcript 첨부
- requirements/toolchain/IDE/Docker 정책 변경이면 DEV_ENVIRONMENT_SPEC 영향 확인 + DevEx Agent sign-off
- dependency 변경이면 `requirements*.txt` exact-pin audit, `.venv` smoke, pip-audit 결과 첨부
- release/export 변경이면 SBOM/CVE output, model manifest verification log, export secret scan 첨부
- benchmark metric 변경이면 EVAL_SPEC 영향 확인
```

Mandatory code-quality commands:

```bash
python scripts/check_file_size.py \
  --config rules/code_shape.json \
  --json-output artifacts/review/file_size_report.json \
  --fail-on-hard-limit

python scripts/check_import_boundaries.py \
  --rules rules/code_shape.json \
  --json-output artifacts/review/import_boundary_report.json
```

The scripts must emit JSON artifacts:

```text
artifacts/review/file_size_report.json
artifacts/review/import_boundary_report.json
```

---

## 17. 구현 금지 목록

주니어 개발자가 범위를 넓히지 않도록 아래는 v0에서 만들지 않는다.

```text
- Extractor/Rule Selector production flow
- multi-user/RBAC/workspace
- cloud GPU managed compute
- MCP/Dify/LangGraph/CrewAI export
- local 24B teacher 기본 경로
- arbitrary provider marketplace
- workflow canvas
- agent orchestration
```

필요해 보이면 코드를 만들지 말고 문서에 v0.2+ 후보로 추가한다.

---

## 18. Junior Debug Checklist

문제가 생기면 아래 순서대로 확인한다.

```text
1. API 응답 trace_id 확인
2. Job row status/error_class 확인
3. JobEvent 마지막 seq 확인
4. worker log에서 같은 trace_id 검색
5. artifact manifest sha256 확인
6. PRAGMA foreign_key_check 실행
7. SECURITY_SPEC 위반 가능성 확인
8. 관련 phase acceptance criteria로 돌아가 재현 테스트 작성
```
