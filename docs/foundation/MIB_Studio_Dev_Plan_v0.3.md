# MIB Studio 개발 계획서 (Dev Plan)

> **MIB Studio = MicroAgent Inventor Blocks**  
> 룰·데이터·모델·학습·평가·배포 블록을 조합해 v0 잠금 모델(`google/gemma-2b-it`, `microsoft/Phi-3.5-mini-instruct`)을 특수목적 Small Agent로 만들고, 대형 LLM 대비 성능·비용·속도를 벤치마킹하는 Local-first GUI 플랫폼.

작성일: 2026-06-20  
최종 개정: 2026-06-21  
문서 상태: Implementation-Ready v0.3 · M0 GO · M1 authorized  
범위: **이 문서는 개발 계획(원칙·페이즈·인수 기준·마일스톤·리스크)만 담는다.** 제품/아키텍처/보안/평가 등 상세 명세는 `docs/specs/`로 분리하고 여기서 링크한다.

> **v0.3 개정 요약**
>
> - 멀티에이전트 교차검증(BE/아키텍처·LLM/학습·보안·평가/벤치마크·제품) 지적사항 반영(벤치마크 프로토콜·보안 3종·아키텍처 보강·실측 VRAM·MVP 축소·학습 백엔드 확정).
> - **학습 백엔드 플랫폼 분기 확정:** NVIDIA=CUDA/LLaMA-Factory, **Apple Silicon=MLX**(통합 메모리, mlx-lm LoRA 4-bit). AMD/Intel은 v0 학습 비지원.
> - **문서 구조 변경:** 단일 계획서를 개발 계획 + `docs/specs/` 12종 명세로 분리. 본 문서는 계획·링크만 유지.

---

## 0. 문서 구성 / 인덱스

상세 명세는 아래 스펙 문서로 분리되어 있다. 본 계획서의 §참조(§N)는 다음 매핑으로 해당 문서에서 찾는다.

| 스펙 문서 | 담는 내용 | 원 계획서 섹션 |
|---|---|---|
| [IMPLEMENTATION_GUIDE](../specs/IMPLEMENTATION_GUIDE.md) | 주니어 개발자용 구현 순서·파일 책임·DTO·테스트·phase별 티켓 | 구현 실행 기준 |
| [PRODUCT_SPEC](../specs/PRODUCT_SPEC.md) | 제품 정의·포지션·네이밍·사용자·시나리오·수익모델·데모·스타트업 포지션 | §1–5, §20, §25, §26 |
| [PRESET_SPEC](../specs/PRESET_SPEC.md) | 프리셋/매크로 UX·학습 데이터 표준 포맷 | §6, §15 |
| [UX_SPEC](../specs/UX_SPEC.md) | 화면·정보구조(IA)·워크플로·UI 상태 규약·게이팅·접근성·캐넌 목업 참조 | §35 |
| [DEV_ENVIRONMENT_SPEC](../specs/DEV_ENVIRONMENT_SPEC.md) | IDE/venv/Docker 경계·requirements 파일·로컬 셋업·환경 변수 | §36 |
| [ARCHITECTURE](../specs/ARCHITECTURE.md) | 앱 형태·아키텍처·컴포넌트·기술스택·데이터흐름·폴더구조·DB·개발환경·스택 적합성 | §7–9, §13, §14, §23, §24, §31, §32 |
| [MVP_SCOPE](../specs/MVP_SCOPE.md) | v0 MVP 범위·연기 항목 | §21 |
| [EVAL_SPEC](../specs/EVAL_SPEC.md) | 평가 지표·벤치마크 UX·방법론(§17.1) | §16, §17 |
| [SECURITY_SPEC](../specs/SECURITY_SPEC.md) | 보안/프라이버시(egress·키체인·토큰·PII·공급망) | §19 |
| [HARDWARE_DOCTOR_SPEC](../specs/HARDWARE_DOCTOR_SPEC.md) | Teacher 전략·Hardware Doctor·최소/권장 사양 | §10, §11, §12 |
| [AGENT_CONTRACT_SPEC](../specs/AGENT_CONTRACT_SPEC.md) | Agent Package/Contract·verifier·fallback·audit | §18 |
| [COMPETITIVE_ANALYSIS](../specs/COMPETITIVE_ANALYSIS.md) | 벤치마킹/경쟁 프로젝트 분석 | §27 |

> 본 계획서에 남는 섹션: §22(페이즈), §28(리스크), §29(원칙), §30(방향), §33(인수 기준), §34(마일스톤).

---

## 29. 개발 원칙

```text
1. Local-first가 기본이다.
2. Cloud는 선택형 convenience layer다.
3. 학습엔진보다 UX가 중요하다.
4. 모델보다 agent contract가 중요하다.
5. 학습보다 평가가 중요하다.
6. 프리셋은 코드가 아니라 제품 자산이다.
7. large LLM은 teacher/judge/fallback이다.
8. small model은 좁은 specialist다.
9. 모든 출력은 schema와 verifier를 통과해야 한다.
10. benchmark가 제품 신뢰를 만든다.
```

---

## 22. 개발 페이즈

사용자 개발 방식에 맞춰 PABCD로 관리한다.

> PABCD = Plan → Audit → Build → Check → Done

### Phase 0. Product Lock

목표:

```text
MVP 범위 = Router 프리셋 1종 + route taxonomy 확정
base model 2종 LOCK = google/gemma-2b-it, microsoft/Phi-3.5-mini-instruct
학습 백엔드 LOCK = LLaMA-Factory(CUDA) + MLX(Apple Silicon) + 툴체인 호환성 라인
MLX v0 포함 = IN v0 (M4 parity 게이트, 실패 시 v0.2 fast-follow) — CTO 결정 완료
데이터 egress 정책 LOCK (BYO key=OpenAI 호환, 기본 schema+익명, provider allowlist)
벤치마크 LOCK = gold eval 구성·v0 비교 타깃·Router 지표·overlap·parity (EVAL_SPEC §16,§17,§17.3)
아키텍처 LOCK = API 계약·작업 큐 파라미터·DB 스키마·contract/preset JSON Schema·마이그레이션
```

산출물(스펙 문서 잠금):

```text
docs/specs/IMPLEMENTATION_GUIDE.md (주니어 구현 실행 기준)
docs/specs/PRODUCT_SPEC.md
docs/specs/ARCHITECTURE.md (작업 큐/IPC/GPU 격리/크래시 복구/개발환경 포함)
docs/specs/MVP_SCOPE.md
docs/specs/PRESET_SPEC.md (Router)
docs/specs/UX_SPEC.md (화면/IA/워크플로 · 캐넌 목업 docs/mockup/)
docs/specs/EVAL_SPEC.md (§17.1 방법론)
docs/specs/SECURITY_SPEC.md (키체인/토큰/PII)
docs/specs/HARDWARE_DOCTOR_SPEC.md (사양/티어/MLX·CUDA 분기)
docs/specs/AGENT_CONTRACT_SPEC.md
docs/specs/COMPETITIVE_ANALYSIS.md
```

#### CTO 결정 (M0 · Cycle 1)

- **MLX(Apple Silicon) = v0 포함, M4 parity 게이트 조건부.** M4에서 CUDA↔MLX parity([EVAL_SPEC §17.3](../specs/EVAL_SPEC.md)) 통과 시 v0 동시 출시, 실패 시 CUDA-only로 v0 출시 + MLX는 v0.2 fast-follow(IR11).
- **타깃 사용자(v0) = tech-savvy 업무 사용자.** "비전문가" 지향은 장기 비전([PRODUCT_SPEC §1](../specs/PRODUCT_SPEC.md)).
- **base model 2종 = `google/gemma-2b-it`(Gemma Terms of Use), `microsoft/Phi-3.5-mini-instruct`(MIT)** 확정([ARCHITECTURE §13.3.1](../specs/ARCHITECTURE.md)).
- **학습 백엔드 + 툴체인 호환성 라인 확정**([ARCHITECTURE §13.3, §31.2](../specs/ARCHITECTURE.md)).

#### M0 Definition-of-Done (Exit 체크리스트)

M0는 아래가 모두 충족·검증되어야 GO(멀티에이전트 재심사 §34.2 입력).

```text
M0-1 MVP=Router 1종 + route taxonomy 확정 (PRESET_SPEC §6.3, §15) ................. [x]
M0-2 base model 2종 LOCK (HF ID·license·chat template·context) (ARCH §13.3.1) ...... [x]
M0-3 학습 백엔드 LOCK (CUDA=LLaMA-Factory, AS=MLX) + 버전 라인 (ARCH §13.3, §31.2) .. [x]
M0-4 MLX v0 결정 = IN v0, M4 parity-gated (CTO 결정) ............................... [x]
M0-5 egress 정책 LOCK (BYO OpenAI 호환, 기본 schema+익명, allowlist) (SEC §19) ...... [x]
M0-6 벤치마크 LOCK (gold eval·비교 타깃·Router 지표·overlap·parity) (EVAL §16,17,17.3) [x]
M0-7 아키텍처 LOCK (API 계약·큐 파라미터·DB FK/인덱스/타입·JSON Schema·Alembic)
     (ARCH §9.6, §13.3.x, §24) .................................................... [x]
M0-8 스펙 12종 상호 일관성 (모순 0·dangling §ref 0) ................................ [x]
M0-9 멀티에이전트 재심사 GO (FE·DB·BE/API·LLM·Eval/QC·Security·Arch/Code·DevEx 전원 GO + CTO 종합) [x]
```

> **M0 = GO.** 2026-06-21 멀티에이전트 재검토와 보강 패치 후 OpenAPI/generated DTO parity, retry/resume request body, cursor/filter params, strict verifier enforcement, phase-aware scaffold validation, M6 export contract scope, strict model catalog fill이 모두 통과했다. `presets/model_catalog.yaml`은 `google/gemma-2b-it`와 `microsoft/Phi-3.5-mini-instruct` 모두 40-hex HF commit, SHA256, size, required weight shard metadata를 포함하며 `python3 scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json` 결과는 `errors: []`이다. M0는 앱 기능 완성이 아니라 **문서/스캐폴드 계약 잠금 마일스톤**이며, 실제 UI/API/worker/training/export runtime 구현은 M1~M6 acceptance에서 검증한다.

#### M0 Evidence / Traceability Matrix

M0는 "좋은 아이디어"가 아니라 구현팀이 바로 작업을 쪼갤 수 있는 **잠긴 계약 묶음**이어야 한다. 아래 표가 M0 재심사와 M1 킥오프의 단일 진실 소스다.

| Gate | 잠긴 결정 | 근거 문서 | 검증 방식 | M1 인계 산출물 |
|---|---|---|---|---|
| M0-1 Router MVP | v0 Agent Type = Router 1종, 사용자 정의 route 2~12개, finance 6-route는 벤치마크 전용 고정 taxonomy | [MVP_SCOPE §21](../specs/MVP_SCOPE.md), [PRESET_SPEC §6.3](../specs/PRESET_SPEC.md) | `route_id` 규칙·예약 route·Router schema 상호 확인 | `presets/router.basic.v1.yaml`, `schemas/router_input.schema.json`, `schemas/router_output.schema.json` |
| M0-2 Base models | `google/gemma-2b-it`, `microsoft/Phi-3.5-mini-instruct` | [ARCHITECTURE §13.3.1](../specs/ARCHITECTURE.md) | HF ID·license·chat template·context·trust_remote_code 확인 | `presets/model_catalog.yaml` + HF commit SHA/SHA256 |
| M0-3 Training backend | NVIDIA=CUDA/LLaMA-Factory QLoRA, Apple Silicon=MLX 4-bit LoRA, AMD/Intel 학습 비지원 | [ARCHITECTURE §13.3](../specs/ARCHITECTURE.md), [HARDWARE_DOCTOR_SPEC §12](../specs/HARDWARE_DOCTOR_SPEC.md), [DEV_ENVIRONMENT_SPEC §36](../specs/DEV_ENVIRONMENT_SPEC.md) | 지원 OS/가속기 매트릭스와 Hardware Doctor G0/G1/G2 일치 | `requirements.txt`, `requirements-mlx.txt`, `requirements-dev.txt`, trainer wrapper skeleton |
| M0-4 MLX release policy | MLX는 v0 포함 개발, M4 parity 실패 시 CUDA-only v0 + MLX v0.2 fast-follow | [EVAL_SPEC §17.3](../specs/EVAL_SPEC.md), IR11 | parity metric·seed·fail decision rule 확인 | parity report schema + backend flag |
| M0-5 Egress/security | BYO OpenAI-compatible, 기본 schema+익명화 예시, provider allowlist, 키체인, localhost Bearer token, PII masking | [SECURITY_SPEC §19](../specs/SECURITY_SPEC.md) | raw data egress 금지·Preview 승인·Credential 평문 미저장 확인 | keychain adapter, egress policy constants, security CI |
| M0-6 Benchmark | frozen gold eval, train/eval overlap 0, >=3 seed, 95% CI, judge κ, latency/cost/fallback 포함 | [EVAL_SPEC §16-§17.4](../specs/EVAL_SPEC.md) | 수기 수치 금지, eval runner 생성 report hash 필수 | eval set manifest, `test_eval_train_no_overlap`, report JSON schema |
| M0-7 Architecture/API/DB | Tauri+React, FastAPI Daemon, Python Worker, SQLite WAL queue, API 계약, DB FK/CHECK/인덱스, Alembic | [ARCHITECTURE §8-§9.6, §24, §31](../specs/ARCHITECTURE.md), [IMPLEMENTATION_GUIDE §5-§8](../specs/IMPLEMENTATION_GUIDE.md) | API endpoint·Job state·DB constraint·crash recovery·migration 생성 가능성 상호 확인 | API route skeleton, Alembic initial revision, worker loop skeleton |
| M0-8 Spec integrity | 스펙 12종이 같은 v0 범위/용어/게이트를 사용 | 본 문서 §0 + 각 spec 헤더 | dangling link/ref 0, CUDA/MLX/parity/egress/DB/UX/DevEx entity 표현 일치 | `docs/` lint checklist |
| M0-9 Review gate | FE·DB·BE/API·LLM/Training·Eval/QC·Security·Architecture/Code Quality·DevEx/Environment 전원 GO + CTO 종합 | §34.2, [IMPLEMENTATION_GUIDE §15](../specs/IMPLEMENTATION_GUIDE.md) | 각 리뷰의 P0/P1 blocking issue 0 | M1 backlog 승인 |

#### M0 Scope Boundary

M0에서 **완료된 것**:

```text
- 제품 범위, base model, 학습 백엔드, 보안/egress, 평가 방법론의 문서 잠금.
- v0에 포함되는 것과 v0.2+로 미루는 것의 경계 확정.
- MLX 포함 정책과 실패 시 출시 정책 확정.
- API/DB/작업 큐 계약은 canonical DTO/DDL/job-store 수준으로 보강되었고 scoped OpenAPI/generated DTO 재심사는 GO다. M6 export contract는 M0 문서 범위로 잠그며 실제 runtime inference 구현은 M6에서 검증한다.
- Day-0 scaffold artifact: exact-pinned `requirements*.txt`, IDE 설정, bootstrap script, schema JSON, preset/rule/prompt, strict model catalog, OpenAPI seed/generated DTO, initial Alembic revision scaffold, security workflow, verification scripts.
```

M0에서 **아직 만들지 않는 것**:

```text
- 실제 앱 기능 코드, trainer wrapper 구현체, UI 화면 구현, FastAPI route 구현, worker handler 구현.
- `0001_initial.py`의 전체 Alembic `upgrade/downgrade` ops 구현은 M1-002에서 작성한다.
- 실제 benchmark 수치나 marketing claim.
- Enterprise/air-gapped/RBAC/managed GPU 구현.
```

M1 착수 전 **Day-0 canonical manifest**는 [DEV_ENVIRONMENT_SPEC §36.2](../specs/DEV_ENVIRONMENT_SPEC.md)와 [IMPLEMENTATION_GUIDE §4.1](../specs/IMPLEMENTATION_GUIDE.md)을 따른다. M0/M1 GO 전에는 `presets/model_catalog.yaml`에 `M1_DAY0_FILL`이 0개여야 하며, gated HF 모델은 [IMPLEMENTATION_GUIDE §4.3](../specs/IMPLEMENTATION_GUIDE.md)의 token runbook으로 terms-accepted `HF_TOKEN` 접근을 확인한 뒤 strict fill을 완료해야 한다. 최소 필수 파일:

```text
1. presets/model_catalog.yaml       # HF repo, license, chat_template, commit SHA, file SHA256
2. requirements.txt                 # CUDA/LLaMA-Factory path exact patch pins
3. requirements-mlx.txt             # Apple Silicon/MLX path exact patch pins
4. requirements-dev.txt             # shared dev/test/security tooling exact patch pins
5. .python-version / .node-version / rust-toolchain.toml
6. package.json / pnpm-lock.yaml
7. .env.example                     # secrets forbidden
8. .vscode/settings.json / extensions.json / tasks.json / launch.json
9. scripts/bootstrap_dev.sh / scripts/bootstrap_dev.ps1
10. schemas/*.schema.json           # Router input/output + routing_rules + agent_contract + benchmark_report + export_manifest
11. prompts/router.prompt_only.v1.txt / rules/router.routing_rules.v1.yaml
12. presets/router.basic.v1.yaml    # Router preset + route taxonomy template
13. services/shared/db/migrations/versions/0001_initial.py # ARCH §24 DB schema initial revision
14. .github/workflows/security.yml  # profile-specific pip-audit + model manifest verification
15. scripts/verify_model_catalog.py / scripts/fill_model_catalog.py
```

### Phase 1. Core Project System

목표:

```text
프로젝트 생성
프리셋 선택
룰/예시 입력
SQLite 저장
dataset JSONL 생성
```

개발 항목:

```text
React/Tauri UI
FastAPI backend
Project DB
Preset YAML loader
Dataset builder v0
Hardware Doctor v0
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §4 Day-0 Bootstrap 완료.
2. IMPLEMENTATION_GUIDE §8 M1-001~M1-007 순서대로 구현.
3. ARCHITECTURE §24.2 canonical schema를 Alembic 초기 리비전으로 생성.
4. PRESET_SPEC §15.0 JSONL 포맷과 §15.4 Router schema를 Dataset Builder에 적용.
5. Hardware Doctor는 HARDWARE_DOCTOR_SPEC §11의 G0/G1/G2만 UI에 노출.
```

완료 조건:

```text
사용자가 Router preset을 선택하고
예시 20개를 입력하면
training JSONL이 생성된다.
```

### Phase 2. Teacher Data Generator

목표:

```text
룰 기반 synthetic data 생성
hard negative 생성
review grid 제공
```

개발 항목:

```text
BYO OpenAI-compatible API key
teacher prompt templates
structured JSON output
hard negative generation (teacher-generated 200 total 중 >=40 hard_negative)
sample review UI
approve/reject/edit
teacher packet preview
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §9 M2-000~M2-004 순서대로 구현. M2-000은 모든 teacher_synthetic dataset_gen job의 선행 gate다.
2. SECURITY_SPEC §19.4 keyring 저장을 먼저 끝낸 뒤 teacher 호출을 붙인다.
3. SECURITY_SPEC §19.1 packet preview와 §19.6 PII masking audit를 UI/API에 연결한다.
4. EvalSet freeze는 synthetic data 생성 전 강제한다(EVAL_SPEC §17.1).
```

완료 조건:

```text
룰 5개 입력
→ synthetic 200개 생성
→ 사용자가 검수
→ dataset v1 저장
```

### Phase 3. Training Engine Wrapper

목표:

```text
locked v0 base model(`google/gemma-2b-it` 또는 `microsoft/Phi-3.5-mini-instruct`) LoRA/QLoRA/MLX LoRA 학습 job 실행
```

개발 항목:

```text
training job manager (Job 큐/상태머신, ARCHITECTURE §8.1)
LLaMA-Factory(CUDA) + MLX(Apple Silicon) wrapper
GPU/가속기 check (CUDA·MLX·미지원 분기 가드)
model download/check (SHA256 검증)
checkpoint 저장 + resume
adapter output
training log streaming (JobEvent)
dry-run training + 실시간 VRAM 가드
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §10 M3-000~M3-005 순서대로 구현. M3-001은 M3-000 model cache service 없이는 시작하지 않는다.
2. train job은 ARCHITECTURE §8.1.2 claim 트랜잭션으로만 실행한다.
3. CUDA wrapper와 MLX wrapper는 동일 Dataset JSONL을 입력으로 받는다.
4. artifact는 ARCHITECTURE §8.3.1 원자성 규칙으로 저장한다.
```

완료 조건:

```text
locked v0 base model 둘 중 하나를
Router dataset으로 fine-tune하고
adapter가 생성된다.
```

### Phase 4. Evaluation + Benchmark

목표:

```text
small agent 성능을 baseline/teacher/large model과 비교
```

개발 항목:

```text
eval runner
metric calculator
latency benchmark
JSON valid checker
cost estimator
benchmark report UI
failure case viewer
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §11 M4-001~M4-003 순서대로 구현.
2. EVAL_SPEC §17.4 overlap test를 CI에 넣는다.
3. benchmark report는 EvalRun rows에서 자동 생성하고 수기 입력을 금지한다.
4. CUDA/MLX 비교는 EVAL_SPEC §17.3 parity gate 통과 전 공동 리포트로 표기하지 않는다.
```

완료 조건:

```text
Prompt-only base model
Fine-tuned small model
Teacher model
Rule-only baseline
Optional Local-large는 hardware unavailable 시 `SKIPPED_OPTIONAL`
비교 리포트가 나온다.
```

### Phase 5. Agent Package + Playground

목표:

```text
학습된 모델을 agent package로 만들고 테스트
```

개발 항목:

```text
agent contract YAML
input/output schema validator
runtime config
local playground
fallback rule
audit log
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §12 M5-001~M5-003 순서대로 구현.
2. AGENT_CONTRACT_SPEC §18.1 schema를 validator에 연결한다.
3. Playground 응답은 PRESET_SPEC §15.4 router_output.schema와 verifier를 반드시 통과한다.
4. fallback은 조건 표시까지만 자동, 실제 외부 호출은 사용자 승인 뒤 실행한다.
```

완료 조건:

```text
사용자가 Playground에서 입력을 넣으면
fine-tuned agent가 JSON으로 응답하고
verifier 결과가 표시된다.
```

### Phase 6. Export

목표:

```text
외부에서 쓸 수 있는 형태로 내보내기
```

초기 export:

```text
JSON agent package zip
Exported Docker runtime API
OpenAI-compatible endpoint wrapper bundled inside zip/Docker runtime
```

후속 export:

```text
MCP server
Dify tool
LangGraph node
CrewAI tool
Ollama adapter
vLLM deployment config
```

구현 순서:

```text
1. IMPLEMENTATION_GUIDE §13 M6-001~M6-002 순서대로 구현.
2. agent package zip은 Docker 설치 여부와 무관하게 먼저 성공해야 한다.
3. Docker export는 zip export가 통과한 뒤 구현한다.
4. export artifact에는 manifest sha256과 benchmark report를 포함한다.
```

완료 조건:

```text
agent package zip이 Docker 설치 여부와 무관하게 native runtime smoke를 통과하고,
Docker가 있는 환경에서는 exported container가
/agents/{agent_id}/run API와 /v1/chat/completions API로 작동한다.
```

### 22.7 M1~M6 단계 목표 / KPI Gate

아래 KPI는 각 마일스톤의 CTO GO/NO-GO 판정 기준이다. 기능 구현 완료 선언은 금지하며, `증거` 컬럼의 자동화 로그·리뷰 산출물·스키마 검증 결과가 남아야 다음 단계로 넘어간다.

| Milestone | 단계 달성 목표 | Hard KPI (GO 기준) | 필수 증거 | 즉시 NO-GO 조건 |
|---|---|---|---|---|
| M1 Core | Router 프로젝트 생성부터 JSONL 생성, SQLite 영속화, Hardware Doctor, 기본 UI/API/SSE 골격을 완성한다. | Router preset 선택→룰/예시 20개 입력→training JSONL schema validation 100%; Project/Dataset/Example/Job 재시작 복원 100%; OpenAPI/generated operation parity 100%; Hardware Doctor G0/G1/G2 분기 테스트 100%; code-shape/import-boundary violation 0 | M1 API/FE smoke transcript, JSONL validation report, Alembic upgrade/downgrade log, `foreign_key_check`/`integrity_check`, Hardware Doctor fixture report, OpenAPI parity report | JSONL 스키마 불일치, DB 재시작 후 데이터 손실, unsupported hardware에서 학습 버튼 활성화, API/FE DTO drift |
| M2 Teacher Data | BYO teacher key, packet preview, PII masking, synthetic/hard-negative 생성, human review, dataset versioning을 완성한다. | OS keychain 저장 테스트 pass; raw API key/PII secret-log scan finding 0; teacher-generated record 200개 이상 schema-valid 100%; 그중 `source='hard_negative'` 40개 이상; 생성 샘플 100%가 approved/rejected/edited 상태를 거쳐 dataset v1 저장; EvalSet freeze가 synthetic 생성 전에 발생; teacher_guard와 teacher_synthetic dataset exact overlap 0 | keychain proof, packet preview vs outbound payload diff, PII masking audit, synthetic JSONL validation report, hard-negative validation report, review decision export, EvalSet SHA256/freeze log | 키 평문 저장, preview와 실제 outbound payload 불일치, review 없이 dataset version 생성, EvalSet freeze 누락 |
| M3 Training | 잠금 v0 base model을 CUDA QLoRA 또는 MLX LoRA로 학습하고, checkpoint/resume, worker isolation, adapter artifact lineage를 완성한다. | strict model catalog verification errors 0; backend별 가능 장비에서 adapter 생성 smoke pass; cancel/resume round-trip pass; CUDA OOM 또는 simulated OOM 시 Daemon/UI 생존 및 `error_class=CUDA_OOM` 기록; dry-run 예상 시간/VRAM 오차 ±30% 이내; ModelRun/JobResource/AdapterArtifact linkage 100% | trainer config golden snapshot, model cache SHA256 verification, JobEvent replay log, checkpoint resume transcript, OOM isolation transcript, dry-run vs short-run comparison, adapter manifest | catalog hash 미검증 다운로드, resume 불가, OOM이 Daemon/UI를 죽임, adapter와 dataset/model_run lineage 추적 불가 |
| M4 Benchmark | fine-tuned small agent를 prompt-only/teacher/rule-based/optional local-large와 재현 가능한 방식으로 비교하고 CUDA/MLX parity를 판정한다. | EvalSet sample 200~300, EvalSet labeler `kappa >= 0.70`; LLM judge metric을 쓰면 human-gold judge agreement를 기록하고 0.70 미만이면 judge metric을 release claim에서 제외하고 rule metric profile로 대체; overlap check `passed=true`; completed target은 seed 3개 이상, mean/SD/95% CI 포함; prompt_only/fine_tuned/teacher/rule_based target 모두 존재; local_large는 COMPLETED 또는 SKIPPED_OPTIONAL; report hash recompute VALID; CUDA/MLX parity PASS/FAIL 기록 | benchmark report JSON, overlap report, metric calculator test log, judge agreement note if judge is used, seed run artifacts, report hash verification, parity decision note | 수기 입력 benchmark 수치, train/eval 오염, seed/CI 누락, local_large unavailable을 FAILED로 처리, parity 판정 없이 공동 리포트 표시 |
| M5 Package+Playground | 검증된 ModelRun을 Agent Contract로 패키징하고 Playground에서 schema/verifier/fallback/audit UX를 완성한다. | Agent Contract schema validation 100%; benchmark `COMPLETED` + report hash VALID인 ModelRun만 package 가능; Playground canned input 20개 schema adherence 100%; confidence threshold/fallback 표시 테스트 pass; 사용자 승인 없는 외부 fallback call 0; playground audit/event record coverage 100% | contract YAML validation, package manifest, verifier golden tests, Playwright playground transcript, fallback approval test, audit log sample | benchmark 미완료 모델 패키징, schema-invalid 응답 표시, fallback 자동 외부 호출, audit 누락 |
| M6 Export / v0 RC | agent package zip과 Docker runtime export를 만들고, zip 단독 smoke와 Docker/OpenAI-compatible runtime smoke를 통과시킨다. | Docker 미설치 환경 zip export + native runtime smoke pass; export manifest file hash validation 100%; CUDA/lora_adapter package는 Docker 가능 환경에서 `/agents/{agent_id}/run` 200 + schema-valid, `/v1/chat/completions` compatibility smoke pass; MLX/mlx_lora_adapter package는 zip-native smoke가 필수이고 Docker export는 409 `DOCKER_UNAVAILABLE`이 기대 동작; temperature=0 고정 입력에 package/playground/export output parity pass; export secret scan finding 0; §33.7 v0 출시 게이트 전부 pass | zip native smoke log, Docker smoke log for CUDA package, MLX Docker-unavailable check when applicable, OpenAI-compatible request/response transcript, manifest hash report, export secret scan, v0 RC sign-off matrix | Docker 없으면 zip도 실패, export artifact에 secret 포함, OpenAI-compatible wrapper 미동작, package와 export 출력 불일치, v0 release gate 미충족 |

KPI 운영 규칙:

```text
1. Hard KPI는 "최선 노력"이 아니라 GO/NO-GO 기준이다.
2. 장비 의존 KPI(CUDA/MLX/Docker)는 해당 장비 lane의 evidence artifact로 증명한다. 장비가 없는 로컬 verify-only 결과는 wiring 증거일 뿐 release evidence가 아니다.
3. KPI 수치를 낮추거나 scope를 바꾸려면 CTO_DECISION.md에 사유·위험·대체 KPI·후속 owner를 기록한다.
4. 각 마일스톤 종료 리뷰는 §34.2 멀티에이전트 게이트와 §34.4 evidence bundle을 함께 만족해야 한다.
```

### 22.8 LLM 개발 흐름 / Handoff Runbook

LLM 코딩 에이전트는 긴 문서를 요약해서 임의 구현하지 않는다. 각 마일스톤은 아래 순서로만 실행한다.

```text
1. 현재 Milestone의 §22 목표와 §22.7 KPI를 읽는다.
2. IMPLEMENTATION_GUIDE의 해당 ticket 범위를 찾는다. `-000` prework ticket이 있으면 반드시 `-001`보다 먼저 끝낸다.
3. ticket의 Files/Endpoints/Input/Output/Done을 구현 단위로 쪼갠다.
4. API/DTO/DB/schema/env 중 하나라도 바뀌면 같은 ticket에서 OpenAPI, generated.ts, migration/model, repository, fixture/test를 함께 갱신한다.
5. §22.7 필수 증거를 생성할 수 없는 상태면 기능 Done을 선언하지 않는다.
6. 다음 Milestone은 이전 Milestone의 handoff artifact가 검증된 뒤 시작한다.
```

| Milestone | LLM 시작 입력 | 구현 ticket 순서 | 반드시 함께 갱신 | 종료 검증 / 증거 | 다음 단계 인계물 |
|---|---|---|---|---|---|
| M1 Core | M0 strict catalog, OpenAPI seed, canonical DDL, Router preset spec, Day-0 bootstrap | M1-001 → M1-002 → M1-003 → M1-004 → M1-005 → M1-006 → M1-007 | API route + DTO + OpenAPI + generated.ts, DB model + Alembic + repository, FE API client + screen state | scaffold verify, M1 smoke, JSONL schema validation, DB integrity/foreign key check, Hardware Doctor fixture | persisted Project/Dataset/Example/Job rows, training JSONL, HardwareProfile, M1 review bundle |
| M2 Teacher Data | M1 approved examples/dataset, Project route snapshot, keychain contract, teacher packet policy | M2-000 → M2-001 → M2-002 → M2-003 → M2-004 | Credential route/service + keychain adapter, TeacherPacket DTO/API/UI, DatasetGen job/resource, PII audit tests | keychain proof, packet preview/outbound diff, secret-log scan, synthetic JSONL validation, hard-negative validation, EvalSet freeze log | teacher_guard EvalSet, reviewed dataset v1, TeacherPacketApproval/audit trail, M2 review bundle |
| M3 Training | M2 approved dataset v1, strict model catalog, HardwareProfile, Job queue/store | M3-000 → M3-001 → M3-002 → M3-003 → M3-004 → M3-005 | model cache + training store + worker handler + JobEvent, ModelRun/JobResource/Checkpoint/AdapterArtifact lineage | strict catalog/cache hash verification, CUDA/MLX smoke where hardware exists, cancel/resume transcript, OOM isolation, dry-run comparison | ModelRun with adapter manifest, checkpoint metadata, backend metadata for parity, M3 review bundle |
| M4 Benchmark | M3 ModelRun/adapter, benchmark_gold or finance_reference EvalSet, metric schema | M4-001 → M4-002 → M4-003 | EvalRun/Benchmark stores, metric calculator, report schema, UI report view, hash verification | overlap report, 3-seed artifacts, benchmark_report schema validation, report hash recompute VALID, CUDA/MLX parity decision | Benchmark(status=COMPLETED), valid report hash, failure-case set, M4 review bundle |
| M5 Package+Playground | M4 completed Benchmark with VALID hash, ModelRun lineage, Agent Contract schema | M5-001 → M5-002 → M5-003 | AgentPackage contract builder + verifier + playground route/UI + audit/fallback policy | contract schema validation, verifier golden tests, Playwright playground run, fallback approval test, audit sample | immutable AgentPackage, contract_yaml/sha256, playground transcript, M5 review bundle |
| M6 Export / v0 RC | M5 AgentPackage, adapter artifact, strict external model cache contract, benchmark report | M6-001 → M6-002 | ExportArtifact store, worker export handler, runtime templates/loaders, manifest schema, secret scan | zip native smoke without Docker, manifest/hash validation, exported runtime auth/native/OpenAI-compatible smoke, Docker smoke where available, export secret scan, v0 sign-off matrix | signed v0 RC evidence bundle, zip artifact, optional Docker artifact, release decision |

LLM 중단 조건:

```text
- ticket 구현 중 필요한 endpoint/schema/table/test가 문서에 없으면 코드를 추측하지 말고 docs/spec/schema를 먼저 패치한다.
- 이전 단계 인계물이 없으면 후속 단계 mock으로 우회하지 않는다. 예: Benchmark hash VALID 없이 AgentPackage 생성 금지, AgentPackage 없이 Export 금지.
- 장비 의존 smoke(CUDA/MLX/Docker)가 로컬에서 불가능하면 skip으로 Done 처리하지 말고 evidence artifact에 "not run locally"를 남기고 해당 lane의 CI/실장비 검증을 blocking 또는 conditional로 올린다.
- mockup 문구, 예시 숫자, 임시 fixture 결과를 제품 claim이나 benchmark claim으로 승격하지 않는다.
```

---

## 33. 인수 기준 (Acceptance Criteria)

각 Phase는 §22.7 KPI와 아래 기준을 자동/수동 테스트로 통과해야 'Done'으로 본다(PABCD의 Check).

### 33.1 Phase 1 — Core Project System
```text
- [ ] Router 프리셋 선택→룰/예시 20개 입력→training JSONL 생성.
- [ ] Hardware Doctor가 GPU/VRAM/CUDA 탐지 후 G0/G1/G2 게이트 반환.
- [ ] 비-NVIDIA/저VRAM에서 학습 버튼 비활성 + 사유 표시.
- [ ] DB에 Project/Dataset/Example/Job 행 생성, 재시작 후 상태 유지.
```

### 33.2 Phase 2 — Teacher Data Generator
```text
- [ ] BYO 키는 OS 키체인에 저장(평문 미저장 검증 테스트).
- [ ] Teacher Packet Preview에 전송 항목 표시 + PII 마스킹 적용.
- [ ] 룰 5개→synthetic 200개 생성→검수→dataset v1 저장.
- [ ] eval set이 synthetic 생성 이전에 frozen(SHA256 기록).
```

### 33.3 Phase 3 — Training Engine
```text
- [ ] `google/gemma-2b-it` 또는 `microsoft/Phi-3.5-mini-instruct` QLoRA/MLX LoRA로 Router dataset fine-tune→adapter 생성.
- [ ] 학습 잡 취소/재시작 가능, checkpoint에서 resume 동작.
- [ ] CUDA OOM 시 Daemon/UI 생존(워커 격리), error_class=CUDA_OOM 기록.
- [ ] dry-run이 VRAM peak·tokens/sec·예상시간(±30%) 반환.
- [ ] Apple Silicon(≥16GB)에서 MLX LoRA로 동일 Router dataset 학습→adapter 생성, parity 비교에 필요한 backend/model_run/eval metadata 기록.
```

### 33.4 Phase 4 — Evaluation + Benchmark
```text
- [ ] test_eval_train_no_overlap 통과(의미 중복 0%).
- [ ] 벤치마크 리포트가 ≥3 seed 평균±SD + 95% CI 포함.
- [ ] EvalSet labeler κ≥0.70. LLM judge metric을 쓰는 경우 human-gold judge agreement를 표기하고, judge agreement κ<0.70이면 judge metric은 release claim에서 제외하며 rule metric profile로 대체.
- [ ] latency p50/p95/p99 + fallback 포함 effective cost/task 보고.
- [ ] CUDA/MLX 공동 리포트는 EVAL_SPEC §17.3 parity gate PASS/FAIL 판정 후에만 표시.
- [ ] 리포트는 eval runner 자동 생성(해시 포함), 수기 수치 금지.
```
> 상세 방법론: [EVAL_SPEC §17.1](../specs/EVAL_SPEC.md)

### 33.5 Phase 5 — Agent Package + Playground
```text
- [ ] agent contract YAML + input/output schema validator 동작.
- [ ] Playground 입력→JSON 응답→verifier(스키마/라벨/confidence) 결과 표시.
- [ ] confidence<임계 시 fallback 정책 표시(호출은 사용자 승인).
```

### 33.6 Phase 6 — Export
```text
- [ ] Docker 미설치 환경에서도 agent package zip export 성공.
- [ ] CUDA/lora_adapter package는 export된 Docker 컨테이너 /agents/{id}/run 200 응답 + 스키마 검증 통과. MLX/mlx_lora_adapter package는 zip-native smoke 필수, Docker export 409 `DOCKER_UNAVAILABLE` 확인.
- [ ] OpenAI-compatible endpoint로 동일 입력 동일 출력 재현.
```

### 33.7 v0 출시 게이트(전역)
```text
- [ ] 보안: 키체인 저장·로컬 API 토큰 인증·PII 마스킹 회귀 테스트 green.
- [ ] 신뢰성: 학습 크래시 복구 시나리오 통과.
- [ ] 벤치마크: EVAL_SPEC §17.1 방법론 자동 검증 통과.
- [ ] 문서: 미검증 수치 '가설' 표기 일관, Enterprise 주장 분리.
```

---

## 34. 마일스톤 (Milestones)

> 기준: 2~3인 코어팀(풀스택 1~2 + ML 1) 가정. 절대일정이 아니라 순서·게이트 정의.

| 마일스톤 | 범위 | 산출물 / 게이트 |
|---|---|---|
| M0 Product Lock | §22 Phase 0 | SPEC 12종 잠금 + base model 2종·백엔드(CUDA+MLX, 버전 라인)·**MLX v0=IN(M4 parity 게이트)**·egress·벤치마크·DevEx LOCK + 멀티에이전트/CTO GO 완료 |
| M1 Core | Phase 1 | 프로젝트/프리셋/Hardware Doctor/JSONL, §22.7 KPI + §33.1 통과 |
| M2 Teacher Data | Phase 2 | synthetic+PII+packet preview, §22.7 KPI + §33.2 통과 |
| M3 Training | Phase 3 | QLoRA(CUDA)+MLX(Apple Silicon) adapter+resume+격리, §22.7 KPI + §33.3 통과 (핵심 위험 구간) |
| M4 Benchmark | Phase 4 | EVAL_SPEC §17.1 준수 리포트, §22.7 KPI + §33.4 통과 (간판 신뢰성 확보) |
| M5 Package+Playground | Phase 5 | agent contract+verifier+playground, §22.7 KPI + §33.5 통과 |
| M6 Export / v0 RC | Phase 6 | Docker/OpenAI export, §22.7 KPI + §33.6+§33.7 전역 게이트 통과 |

### 34.1 크리티컬 패스 / 선행 결정

```text
- M0에서 base model 2종·백엔드(CUDA+MLX, 버전 라인)·MLX(v0=IN, M4 parity-gated)·egress·벤치마크 LOCK 완료 → M3/M4 추정 가능.
- M3(학습 격리·resume·CUDA/MLX parity)와 M4(오염 방지 벤치마크)가 제품 신뢰의 두 핵심 구간.
- 환경 패키징(ARCHITECTURE §8.4)은 M1부터 CI에 포함해 막판 배포 리스크를 분산한다.
```

### 34.2 멀티에이전트 재심사 게이트

각 마일스톤 종료 시 최소 8개 독립 리뷰(FE·DB·BE/API·LLM/Training·Eval/QC·Security·Architecture/Code Quality·DevEx/Environment)를 병렬로 수행한다. 사람 팀이 없을 때는 Codex sub-agent를 같은 역할로 생성해 리뷰한다.

| Review Agent | 담당 범위 | 필수 입력 | 필수 출력 |
|---|---|---|---|
| FE Agent | UI flow, state, error, accessibility, API/SSE client | Dev Plan, IMPLEMENTATION_GUIDE §14, mockup, API DTO | FE GO/NO-GO, 화면별 blocking issue, 누락 state |
| DB Agent | schema, migration, FK/CHECK/index, data lifecycle | ARCHITECTURE §24, IMPLEMENTATION_GUIDE §6 | DB GO/NO-GO, migration risk, invariant/test gap |
| BE/API Agent | FastAPI, auth, DTO, Job queue, worker orchestration | ARCHITECTURE §8/§9.6, IMPLEMENTATION_GUIDE §5/§7 | BE GO/NO-GO, API/Job state issue, failure/retry gap |
| LLM/Training Agent | dataset, tokenizer/chat template, CUDA/MLX wrapper, checkpoint | ARCHITECTURE §13, PRESET_SPEC §15, HARDWARE_DOCTOR_SPEC §11-§12 | LLM GO/NO-GO, training reproducibility risk, backend parity gap |
| Eval/QC Agent | benchmark, overlap, report, acceptance criteria, CI | EVAL_SPEC §16-§17, Dev Plan §33 | QC GO/NO-GO, missing test, unverifiable metric |
| Security Agent | keychain, bearer token, egress, PII, supply chain | SECURITY_SPEC §19, ARCHITECTURE §9.6/§24 | Security GO/NO-GO, data leak risk, auth/egress gap |
| Architecture/Code Quality Agent | design pattern consistency, layer boundaries, god-file/file-size risk, dependency direction | IMPLEMENTATION_GUIDE §3, ARCHITECTURE §23/§32, changed file list | Architecture GO/NO-GO, pattern violations, split/refactor requirements |
| DevEx/Environment Agent | IDE setup, `.venv`, requirements files, Docker boundary, toolchain versions | DEV_ENVIRONMENT_SPEC §36, ARCHITECTURE §31, IMPLEMENTATION_GUIDE §4 | DevEx GO/NO-GO, setup blocker, environment drift |
| CTO Integrator | cross-agent conflict resolution, final milestone decision | all review reports | FINAL GO/NO-GO, required doc/code changes, owner |

리뷰 출력은 아래 형식을 따른다.

```text
Role:
Decision: GO | GO_WITH_CONDITIONS | NO_GO
Blocking issues:
  - [P0/P1] file/section: issue → required fix
Non-blocking issues:
  - [P2/P3] file/section: issue → suggested fix
Missing tests:
  - test name / acceptance criterion
Spec updates required:
  - doc path / section / exact change
Assumptions:
  - ...
```

GO 조건:

```text
- P0/P1 blocking issue가 0개.
- FE/DB/BE/LLM/Eval-QC/Security/Architecture-Code/DevEx가 모두 GO 또는 GO_WITH_CONDITIONS.
- GO_WITH_CONDITIONS 조건은 다음 마일스톤 첫 티켓으로 등록되어야 한다.
- CTO Integrator가 cross-agent 충돌을 해결하고 최종 결정을 본 문서에 기록한다.
- GO 없이는 다음 마일스톤 구현 착수 금지(계획 변경은 본 문서 개정으로만).
```

M0 재심사 추가 조건:

```text
- DB Agent가 ARCHITECTURE §24.2 DDL을 실제 SQLite에서 실행 가능하다고 확인.
- BE/API Agent가 Job claim/reconcile/SSE/event gap 흐름을 재현 가능하다고 확인.
- FE Agent가 M1 화면과 API/SSE 상태를 구현 가능하다고 확인.
- LLM Agent가 CUDA/MLX wrapper 입력/출력 artifact 계약을 구현 가능하다고 확인.
- Security Agent가 key/PII/egress secret leak 경로가 문서상 차단되어 있다고 확인.
- Architecture/Code Quality Agent가 god file 금지, 파일 크기 예산, import 방향, 레이어 패턴을 검증 가능하다고 확인.
- DevEx/Environment Agent가 `.venv`, `requirements*.txt`, IDE interpreter, Docker export-only 정책을 막힘 없이 재현 가능하다고 확인.
```

### 34.3 Sign-Off Matrix / Review Artifacts

마일스톤 GO/NO-GO는 말로 승인하지 않고 review artifact로 남긴다.

```text
docs/reviews/M{n}/
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

`SIGNOFF_MATRIX.md` 형식:

```text
| Milestone | FE | DB | BE/API | LLM/Training | Eval/QC | Security | Arch/Code | DevEx | CTO | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |
```

규칙:

```text
- FE/DB/BE/API/LLM/Eval-QC/Security/Arch-Code/DevEx는 필수 칼럼이다.
- `WAIVED`는 CTO_DECISION.md에 사유·위험·후속 owner가 있을 때만 허용한다.
- P0/P1 issue가 하나라도 열려 있으면 `Decision=NOT_GO`.
- spec/API/DB/security/eval 계약 변경 후에는 영향을 받는 Agent review를 다시 수행한다.
- v0 RC는 WAIVED 없이 전원 GO여야 한다.
```

### 34.4 Review Evidence Bundles

각 Agent는 리뷰 결론과 함께 아래 증거를 확인한다.

| Agent | Required evidence |
|---|---|
| FE | screen-by-screen state matrix, API/SSE mapping, Playwright happy path, a11y/keyboard check |
| DB | Alembic upgrade/downgrade log, sqlite_master dump, foreign_key_check, integrity_check, DB test list |
| BE/API | `openapi.json`, endpoint matrix, idempotency matrix, Job lifecycle replay transcript, SSE replay/gap test |
| LLM/Training | trainer config golden snapshots, tokenizer/chat-template snapshot, CUDA/MLX smoke plan, checkpoint/resume test |
| Eval/QC | acceptance criteria trace, benchmark report hash, overlap test, release checklist |
| Security | keychain proof, token/auth/SSE tests, PII masking tests, egress allowlist/redirect/DNS tests, secret-log scan, SBOM/CVE output, model manifest verification, export secret scan |
| Architecture/Code Quality | changed file size report, layer import report, pattern consistency checklist, god-file split plan if any soft limit exceeded |
| DevEx/Environment | `.venv` creation log, Python 3.11 proof, profile-specific `requirements*.txt` exact-pin audit, VS Code/PyCharm interpreter proof, Day-0 scaffold verification, post-M1 Docker-not-required smoke |

---

## 28. 주요 리스크

| 리스크 | 대응 |
|---|---|
| 기존 fine-tuning GUI와 겹침 | Rule-first, Agent Contract, Benchmark UX로 차별화 |
| 초보자가 학습 실패로 이탈 | 타깃을 tech-savvy 사용자로 재정의(MVP_SCOPE §21), Hardware Doctor·dry-run·VRAM 가드 |
| small model 품질 부족 | hard negative, eval-first UX, fallback policy |
| cloud teacher 사용 시 보안 우려 | teacher packet preview, PII 마스킹(SECURITY_SPEC §19.6), BYO key·키체인(§19.4) |
| 학습엔진 구현 난이도 | LLaMA-Factory(CUDA)+MLX(Apple Silicon) wrapper 확정(ARCHITECTURE §13.3)으로 시작 |
| GPU 다양성 대응 어려움 | v0 학습 = NVIDIA CUDA(LLaMA-Factory) + Apple Silicon MLX, AMD/Intel은 추론·데이터·eval |
| 너무 큰 플랫폼화 | MVP 프리셋 1개(Router), wizard UI로 제한 |
| 수익모델 약화 | v0는 Community+Pro, Team/Enterprise/Domain Pack은 후속 |

### 28.1 구현 단계 핵심 리스크

| # | 리스크 | 심각도 | 대응 / 완화 | 상태 |
|---|---|---|---|---|
| IR1 | 벤치마크 오염·judge 편향으로 간판 수치 신뢰 붕괴 | 높음 | EVAL_SPEC §17.1 홀드아웃·CI·κ·재현성 강제, 수치 '가설' 표기 | 설계 반영 |
| IR2 | Local-first ↔ Cloud Teacher 메시지 모순 | 높음 | SECURITY_SPEC §19 v0 egress 정책 확정, 메시지 재정의 | 해소 |
| IR3 | API 키 평문·로컬 API 무인증 | 높음 | SECURITY_SPEC §19.4/19.5 키체인·토큰 인증 | 설계 반영 |
| IR4 | 학습 잡 크래시·OOM 시 복구 불가 | 높음 | ARCHITECTURE §8.1~8.3 큐·서브프로세스 격리·checkpoint resume | 설계 반영 |
| IR5 | VRAM 과소평가로 OOM 다발 | 높음 | HARDWARE_DOCTOR_SPEC §12 실측 하향·전제 명시, dry-run ±30%·VRAM 가드 | 설계 반영 |
| IR6 | "standalone"인데 torch/CUDA/Docker 필요 | 중간 | ARCHITECTURE §8.4 임베디드 Python·버전 핀, Docker는 export만 | 설계 반영 |
| IR7 | 환경 패키징(torch×CUDA×OS) 폭발 | 중간 | v0 단일 CUDA/torch 핀, OS 매트릭스 축소 | 설계 반영 |
| IR8 | hard negative/synthetic 품질·비용 불투명 | 중간 | 생성 알고리즘·비용 공개, 사용자 검수 | 일부 |
| IR9 | 차별화 얇음(vs Kiln) + 시장 윈도우 | 중간 | 단일 프리셋 집중·빠른 v0 출시, 벤치마크 신뢰성으로 차별 | 모니터링 |
| IR10 | LLaMA-Factory 래핑 종속(버그/UX) | 중간 | 어댑터 경계 추상화, v0.3+ PEFT 직접 구현 대안 보유 | 모니터링 |
| IR11 | MLX(Apple Silicon) 경로 parity 미달 위험 | 중간 | M4 parity 게이트(EVAL_SPEC §17.3); 실패 시 v0 CUDA-only 출시 + MLX v0.2 fast-follow; 공통 데이터/스키마 계층 | 결정·게이트화 |

---

## 30. 최종 개발 방향

MIB Studio v0는 거대한 AI 플랫폼이 아니다.

첫 버전은 다음이어야 한다.

> **단일 프리셋(Router)을 가진 로컬 GUI 앱. 사용자가 룰과 예시를 넣으면 synthetic data를 만들고, locked v0 base model(`google/gemma-2b-it` 또는 `microsoft/Phi-3.5-mini-instruct`)을 LoRA/QLoRA(CUDA) 또는 MLX LoRA(Apple Silicon)로 학습시키고, 대형 LLM 대비 benchmark를 보여준 뒤, agent package로 export한다.**

최종 한 줄 결론:

> **MIB Studio v0는 “Small Agent를 만들고, 대형 LLM 대비 성능·비용·속도를 증명하는 Local-first GUI”로 개발해야 한다.** (타깃·UX 포지셔닝은 [MVP_SCOPE §21](../specs/MVP_SCOPE.md))
