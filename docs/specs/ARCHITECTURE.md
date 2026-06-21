# 아키텍처 / 기술 스택 / 개발 환경 (ARCHITECTURE) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [SECURITY_SPEC](./SECURITY_SPEC.md) · [HARDWARE_DOCTOR_SPEC](./HARDWARE_DOCTOR_SPEC.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md)

---

## 7. 앱 형태: Local-first Standalone App

### 7.1 결론

MIB Studio는 웹 SaaS보다 **standalone desktop app**이 유리하다.

이유:

- 학습 데이터가 민감하다.
- 로컬 GPU/사내 GPU를 활용해야 한다.
- 오픈소스 채택에 유리하다.
- Pro Desktop 판매와 궁합이 좋다.
- 기업 고객에게 “사내망/온프레미스/외부 전송 없음” 메시지를 줄 수 있다.
- Teacher AI, Recipe Hub, Managed GPU만 선택형 cloud로 붙일 수 있다.

> **"standalone" 정의(정확화):** GUI는 단일 앱이지만 완전 모놀리식 실행파일은 아니다. v0는 **사전 설치 전제**를 둔다 — NVIDIA 드라이버/CUDA(또는 Apple Silicon)와 번들된 임베디드 Python 3.11(앱 내 venv). "임베디드 Python"은 앱이 들고 다니는 고정 버전 venv를 의미하며 시스템 Python에 의존하지 않는다(§8.4, §31.3).

### 7.2 추천 실행 구조

```text
[MIB Studio Desktop App]
Tauri + React UI
        ↓ localhost
[MIB Local Daemon]
FastAPI or Rust API server
        ↓
[Local Worker]
Dataset / Teacher call / Training / Eval / Export
        ↓
[Local Storage]
SQLite + Project Files + Model Adapters
        ↓
[Optional Cloud]
Teacher AI Hub / Recipe Hub / License / Managed GPU
```

### 7.3 기존 FE/BE 구조 유지

기존 웹 개발 구조를 버리지 않는다.  
단지 API 서버가 인터넷 서버가 아니라 사용자 PC 안에서 localhost로 돈다.

```text
React UI
→ http://127.0.0.1:xxxx
→ Local FastAPI
→ Local Python Worker
→ GPU / Model / Dataset / Eval
```

---

## 8. 전체 아키텍처

```text
                    ┌────────────────────┐
                    │      MIB Cloud      │
                    │ Teacher Hub         │
                    │ Recipe Hub          │
                    │ License             │
                    │ Managed GPU later   │
                    └─────────▲──────────┘
                              │ optional
┌─────────────────────────────┴─────────────────────────────┐
│                    MIB Studio Desktop                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ React UI / Tauri Shell                                │  │
│  └───────────────────▲───────────────────────────────────┘  │
│                      │ localhost API                         │
│  ┌───────────────────┴───────────────────────────────────┐  │
│  │ MIB Local Daemon                                      │  │
│  │ Project / Preset / Dataset / Job / Model Registry     │  │
│  └───────────────────▲───────────────────────────────────┘  │
│                      │ job queue                             │
│  ┌───────────────────┴───────────────────────────────────┐  │
│  │ MIB Worker                                            │  │
│  │ Data Builder / Trainer / Evaluator / Exporter         │  │
│  └───────────────────▲───────────────────────────────────┘  │
│                      │                                       │
│  ┌───────────────────┴───────────────────────────────────┐  │
│  │ Local Runtime                                         │  │
│  │ Ollama / llama.cpp / vLLM / Transformers              │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

> **주의:** 다이어그램의 `Local Runtime`은 **추론 전용**이다. 학습 런타임은 별도이며 §13.3에서 분리 정의한다.

### 8.1 작업 큐 / 잡 오케스트레이션 (v0 확정)

장시간(수 분~수 시간) 학습 잡을 HTTP 요청 수명과 분리한다.

```text
- 큐 구현: SQLite 백킹 영속 FIFO 큐(Job 테이블) + 단일 워커 루프.
  (v0는 단일 사용자/단일 GPU 가정 → Redis/Celery 불필요)
- 잡 수명: QUEUED → RUNNING → SUCCEEDED | FAILED | CANCELLED | INTERRUPTED
- 동시성: GPU 점유 잡(학습/벤치마크)은 1개만 실행. 데이터 생성·eval 등 비-GPU 잡은 별도 슬롯.
- 취소: 협조적 취소 토큰 + 프로세스 종료(SIGTERM→SIGKILL) 2단계.
- 진행률: 워커가 JobEvent에 step/loss/VRAM 기록, UI는 SSE/polling으로 스트리밍.
```

#### 8.1.1 Job 상태 전이 / writer 소유권 (v0 LOCK)

| From | To | Writer | 조건 |
|---|---|---|---|
| QUEUED | RUNNING | Worker | `claim job` 트랜잭션 성공, resource slot 확보 |
| QUEUED | CANCELLED | Daemon | 사용자가 실행 전 취소 |
| RUNNING | SUCCEEDED | Worker | handler 정상 완료 + artifact 원자적 기록 완료 |
| RUNNING | FAILED | Worker | 복구 불가 예외, `error_class` 기록 |
| RUNNING | CANCELLED | Worker | `cancel_requested_at` 감지 후 정리 완료 |
| RUNNING | INTERRUPTED | Daemon reconcile | `heartbeat_at < now()-60s` |
| FAILED/INTERRUPTED/CANCELLED | child QUEUED | Daemon | 사용자가 retry/resume 승인, 새 Job(`parent_job_id=old.id`, `attempt_count=old.attempt_count+1`) 생성. 원본 Job row는 terminal 상태로 유지 |

금지:

```text
- Daemon은 RUNNING 잡을 SUCCEEDED/FAILED로 직접 바꾸지 않는다.
- Worker는 QUEUED 잡을 삭제하지 않는다.
- Local Runtime(추론)은 Job/JobEvent를 쓰지 않는다.
```

#### 8.1.2 Job claim 트랜잭션 (SQLite)

Worker는 짧은 write transaction으로 하나의 잡만 claim한다. GPU slot이 이미 사용 중이면 GPU 잡은 건너뛰고 다음 CPU 잡을 claim한다.

```sql
BEGIN IMMEDIATE;

SELECT EXISTS(
  SELECT 1
  FROM job
  WHERE status = 'RUNNING'
    AND resource_class = 'gpu_exclusive'
) AS gpu_busy;

SELECT id
FROM job
WHERE status = 'QUEUED'
  AND (not_before_at IS NULL OR not_before_at <= :now)
  AND (:gpu_busy = 0 OR resource_class != 'gpu_exclusive')
ORDER BY priority DESC, created_at ASC
LIMIT 1;

UPDATE job
SET status = 'RUNNING',
    claimed_by = :worker_id,
    claimed_at = :now,
    heartbeat_at = :now,
    started_at = COALESCE(started_at, :now)
WHERE id = :job_id
  AND status = 'QUEUED';

COMMIT;
```

No selected job means "idle now", not "queue empty"; a queued GPU job may remain blocked by the GPU slot while CPU jobs continue to run.

DB 레벨 가드:

```text
- `ux_one_running_gpu_job`: resource_class='gpu_exclusive' AND status='RUNNING' partial unique index.
- `ux_job_idempotency_project` and `ux_job_idempotency_system`: scoped idempotency partial unique indexes.
- JobEvent는 `(job_id, seq)` UNIQUE. SSE `Last-Event-ID`는 seq로 재전송한다.
```

### 8.2 프로세스 모델 / IPC / GPU 격리

```text
- Daemon(FastAPI)과 Worker는 별도 프로세스. Daemon이 Worker를 subprocess로 spawn.
- 통신: 제어는 DB(Job/JobEvent), 로그는 stdout 파이프 스트리밍.
- GPU 격리: 모든 CUDA 작업은 Worker 서브프로세스에서 실행
  → CUDA OOM/크래시가 Daemon·UI를 죽이지 않는다.
- 헬스: Daemon이 Worker heartbeat(주기적 JobEvent) 감시, N초 무응답 시 INTERRUPTED 처리.
```

### 8.3 크래시 복구 / 내구성

```text
- 진실의 원천(소유권): RUNNING 잡의 status·heartbeat_at·JobEvent는 Worker가 기록. Daemon은 status를 직접 덮어쓰지 않고 reconcile만 수행.
- 보조 리소스 상태(ModelRun/Benchmark/EvalRun/ExportArtifact)는 API가 최초 `QUEUED` 행만 만들고, claim 이후에는 worker owner store(`training_store.py`, `benchmark_store.py`, `export_store.py`)가 Job terminal 전이와 같은 transaction에서 mirror한다.
- Daemon reconcile: heartbeat_at < now()-60s 인 RUNNING 잡을 INTERRUPTED로 전이(BEGIN IMMEDIATE 트랜잭션으로 1초 이내 짧게 락).
- 학습 중단: 마지막 Checkpoint에서 resume(스텝/옵티마이저 상태 복원).
- resume 안전 검증: Checkpoint.dataset_version == 현재 Dataset.version AND training_config_hash == ModelRun.config_hash 일 때만 재개. 불일치 시 새 학습 권고.
- Daemon 재시작: 부팅 시 RUNNING 잡을 INTERRUPTED로 reconcile → resume/폐기 선택 제공.
- SQLite: WAL 모드 + busy_timeout, 주기적 백업 + 무결성 점검.
- 전원 손실: 체크포인트는 원자적 쓰기(temp→rename).
```

#### 8.3.1 로컬 저장소 / artifact 원자성

`MIB_HOME` 기본값은 OS별 app data 디렉터리이며, 사용자가 프로젝트 루트를 변경할 수 있다.

```text
MIB_HOME/
  mib.db
  logs/
    daemon.jsonl
    worker-{worker_id}.jsonl
  model_cache/
    hf/{repo_id}/{commit_sha}/
  projects/{project_id}/
    project.json
    routes.json
    datasets/{dataset_version}/
      dataset.jsonl
      manifest.json        # row_count, sha256, schema_version
    eval_sets/{eval_set_id}/
      eval.jsonl
      manifest.json        # frozen_at, sha256, labeler_ids, kappa
    runs/{model_run_id}/
      train_config.json
      adapter/
      checkpoints/{step}/
        adapter.safetensors
        optimizer.pt
        manifest.json
    benchmarks/{benchmark_id}/
      report.json
      runs/{eval_run_id}.json
    exports/{agent_package_id}/
      agent_package.zip
      manifest.json
```

원자성 규칙:

```text
- 모든 artifact는 `*.tmp` 또는 temp 디렉터리에 쓴 뒤 fsync → rename.
- DB에는 최종 경로와 sha256이 계산된 뒤에만 성공 상태를 기록한다.
- DB 성공 상태인데 파일이 없으면 boot reconcile에서 FAILED/INTERRUPTED + AuditEvent(job_failure)를 남긴다.
- 파일 삭제는 DB soft-delete/archived 상태 기록 후 background cleanup에서 수행한다.
```

### 8.4 환경 패키징 (cross-platform)

```text
- 임베디드 Python 3.11 고정. 개발은 repo-local `.venv`, 의존성은 pip-compatible `requirements*.txt` exact pin으로 고정([DEV_ENVIRONMENT_SPEC §36](./DEV_ENVIRONMENT_SPEC.md)).
- torch×CUDA 매트릭스: v0는 CUDA 12.1 + torch 2.4.1 라인 1종으로 고정.
- 학습 스택(NVIDIA): transformers/peft/trl/bitsandbytes via LLaMA-Factory — Linux/Windows(WSL2)+NVIDIA.
- 학습 스택(Apple Silicon): MLX + mlx-lm(LoRA 4-bit) — macOS 14+, 통합 RAM ≥16GB. bitsandbytes QLoRA는 CUDA 전용이라 미사용.
- AMD/Intel GPU: 학습 비활성(Hardware Doctor가 차단), 데이터 생성·추론·eval만 허용.
- Docker는 export 산출물 실행용으로만 필요(앱 자체는 Docker 불필요).
  Docker 미설치 시 export는 zip 패키지로 대체.
```

### 8.5 관측성(observability)

```text
- 구조화 JSON 로그 + trace_id(요청→잡→스텝 상관).
- 실패 분류: CUDA_OOM / NAN_LOSS / DISK_FULL / MODEL_DOWNLOAD_FAIL / TEACHER_API_ERROR /
  TIMEOUT / SCHEMA_VALIDATION_FAIL / PERMISSION_DENIED / ARTIFACT_MISSING.
- 메트릭: 큐 깊이, GPU 사용률, tokens/sec, 잡 성공률.
```

---

## 9. 주요 컴포넌트

### 9.1 MIB Studio Desktop

- Tauri + React + TypeScript
- 사용자 프로젝트 관리
- 프리셋/매크로 선택
- 데이터 업로드/검수
- 학습 job 모니터링
- 평가/벤치마크 리포트
- agent export

### 9.2 MIB Local Daemon

- FastAPI 기반 local API
- 프로젝트/데이터셋/모델/job 관리
- SQLite DB
- Local worker와 통신
- Cloud teacher 연결 관리
- 보안 설정 및 외부 전송 허용 정책 관리

### 9.3 MIB Worker

- Python worker
- Dataset Builder
- Teacher Data Generator
- Hard Negative Generator
- LoRA/QLoRA Trainer
- Evaluation Runner
- Benchmark Runner
- Agent Package Builder
- Exporter

### 9.4 Local Runtime (추론 전용)

- **학습된** small agent 실행 전용. 학습에는 사용하지 않는다(§13.3 학습 스택과 분리).
- v0/M6 구현 대상은 package zip과 Docker runtime에 포함되는 internal runtime loader다.
- 후속 backend adapter 후보(v0.2+ reference):
  - Ollama
  - llama.cpp
  - vLLM (NVIDIA only)
  - Transformers server mode
- OpenAI-compatible endpoint는 Local Runtime 내부 구현 옵션이 아니라 M6 exported zip/Docker runtime API로만 노출한다([AGENT_CONTRACT_SPEC §18.2](./AGENT_CONTRACT_SPEC.md)).

### 9.5 MIB Cloud

초기에는 없어도 된다.  
후속 수익화 단계에서 선택형으로 붙인다.

- Teacher Hub
- Recipe Hub
- Pro License
- Managed GPU
- Domain Pack Store
- Benchmark profile 공유

### 9.6 Local Daemon API 계약 (v0 LOCK)

127.0.0.1 바인딩 + Bearer 토큰 필수([SECURITY_SPEC §19.5](./SECURITY_SPEC.md)). 모든 응답은 JSON, 오류 형식은 `{error_code, message, details}`.

```text
프로젝트:
  POST   /projects                  201   (create)
  GET    /projects                  200   (list, page/limit)
  GET    /projects/{id}             200 | 404
  PATCH  /projects/{id}             200   (name/preset)
  DELETE /projects/{id}             204   (soft archive: archived_at set)

프리셋:
  GET    /presets                   200   (list)
  GET    /presets/{preset_id}       200   (template + defaults)

데이터셋:
  POST   /projects/{id}/datasets    201   (create/version)
  GET    /projects/{id}/datasets    200
  GET    /datasets/{id}             200   (sample grid, page/limit)
  PATCH  /datasets/{id}             200   (status/approve)
  PATCH  /examples/{id}             200   (review/edit/reject one example)

잡(비동기):
  POST   /projects/{id}/jobs        202   (submit; type=dataset_gen|train|eval|benchmark only)
  GET    /jobs                      200   (global queue, filter project_id/type/status)
  GET    /projects/{id}/jobs        200   (filter type/status)
  GET    /jobs/{job_id}             200   (detail + status)
  DELETE /jobs/{job_id}             202   (cancel)
  POST   /jobs/{job_id}/retry       202   (FAILED|INTERRUPTED|CANCELLED → child QUEUED)
  POST   /jobs/{job_id}/resume      202   (training checkpoint resume → child QUEUED; train only)
  GET    /jobs/{job_id}/events      200   text/event-stream (SSE; Last-Event-ID 재전송)

평가/내보내기:
  POST   /projects/{id}/eval-sets   201   (freeze gold eval set)
  GET    /projects/{id}/eval-sets   200
  GET    /eval-sets/{id}            200
  GET    /projects/{id}/model-runs  200
  GET    /model-runs/{id}           200
  GET    /model-runs/{id}/checkpoints 200
  GET    /projects/{id}/eval-runs   200
  GET    /eval-runs/{id}            200   (report json)
  GET    /projects/{id}/benchmarks  200
  GET    /benchmarks/{id}           200   (metadata + report hash)
  GET    /benchmarks/{id}/report    200   (benchmark_report.json + hash_status)
  POST   /projects/{id}/agent-packages        201
  GET    /projects/{id}/agent-packages        200
  GET    /agent-packages/{agent_package_id}   200
  POST   /agent-packages/{agent_package_id}/playground-runs 200
  POST   /projects/{id}/export      202
  GET    /exports/{job_id}          200   (status/artifact)
  GET    /exports/{job_id}/artifact 200   (zip/docker tar bytes; hash verified)
  POST   /exports/{job_id}/reveal   200   (open artifact folder)

하드웨어:
  POST   /hardware-doctor/scan      202   (preflight dry-run job)
  GET    /hardware-doctor/result    200   (last HardwareProfile)

Teacher packet:
  POST   /projects/{id}/teacher-packets/preview  201
  POST   /teacher-packets/{id}/approve           200

자격증명(키 값 미반환):
  GET    /credentials               200   (provider 목록)
  PUT    /credentials/{provider}    204   (키체인 저장)
  DELETE /credentials/{provider}    204
```

- Job을 생성하는 비동기 submit API만 `Idempotency-Key` 헤더를 지원한다: `POST /projects/{id}/jobs`, `POST /hardware-doctor/scan`, `POST /projects/{id}/export`. 값은 `Job.idempotency_key`와 request body hash에 영속(§9.6.4). 재요청 시 기존 job_id+202 반환.
- `POST /projects/{id}/jobs`는 project-scoped dataset/train/eval/benchmark만 받는다. `export`는 `POST /projects/{id}/export`, `hardware_scan`은 `POST /hardware-doctor/scan` 전용 endpoint만 사용한다.
- `POST /hardware-doctor/scan`은 `HardwareScanRequest` body를 받는 전용 submit API다. Daemon은 이를 `Job(type='hardware_scan', project_id=NULL, resource_class='cpu_shared', params_json=HardwareScanParams)`로 변환하고, idempotency body hash도 `HardwareScanRequest` canonical JSON 기준으로 계산한다.
- Local Daemon API does not expose `/agents/{agent_id}/run`. That route exists only inside exported zip/Docker runtime. Local Playground uses `POST /agent-packages/{id}/playground-runs`.
- 잡은 즉시 `202 + job_id` 반환, 장시간 작업은 SSE/polling으로 추적(§8.1).
- 표준 오류: 400(검증)·401(토큰)·404·409(상태충돌/중복)·422(스키마)·500.

#### 9.6.1 API 공통 규약

```text
ID: 외부 노출 id는 TEXT ULID(또는 UUIDv7). 정렬성과 로그 추적을 위해 생성 시각 포함 id 사용.
시간: ISO-8601 UTC 문자열(`2026-06-20T12:34:56.789Z`).
JSON: snake_case. 알 수 없는 필드는 422.
페이지네이션: `?limit=50&cursor=...`, 응답 `{items, next_cursor}`.
오류: `{error_code, message, details, trace_id}`. details에는 사용자 표시 가능 값만 포함.
trace_id: 모든 응답/Job/JobEvent/AuditEvent에 전달.
```

Auth middleware contract:

```text
- production: all endpoints require Bearer token except `/healthz`.
- CORS preflight (`OPTIONS` + `Origin` + `Access-Control-Request-Method`) is a middleware response, not an endpoint. It bypasses Bearer only after Host/Origin allowlist passes.
- dev auth mode is controlled only by `MIB_DEV_AUTH`.
  - `MIB_DEV_AUTH=bootstrap` (default): stdout bootstrap token required.
  - `MIB_DEV_AUTH=token_file`: `.mib-dev-token` allowed in dev only.
  - `MIB_DEV_AUTH=bypass`: auth bypass allowed only when `APP_ENV=development` AND bind host is 127.0.0.1.
  - production accepts only `bootstrap`; any other value aborts startup.
- bootstrap: Daemon writes exactly one stdout line `MIB_BOOTSTRAP {"base_url":"http://127.0.0.1:{port}","token":"...","pid":...}`. Tauri stores token in memory and exposes `get_api_bootstrap`.
- production token is never stored in keychain, DB, file, log, JobEvent, or AuditEvent.
- token compare uses constant-time comparison.
- missing/invalid token → 401 AUTH_REQUIRED or AUTH_INVALID.
- valid token but disallowed Origin/Host → 403 ORIGIN_NOT_ALLOWED or HOST_NOT_ALLOWED.
- allowed Host: 127.0.0.1:{port}. `localhost:{port}` is dev-only alias after resolving to 127.0.0.1.
- allowed Origin: tauri://localhost, http://localhost:1420 in dev.
- request body size limit applies before route handler.
```

CORS/preflight response:

```text
- Allowed methods: GET, POST, PATCH, PUT, DELETE, OPTIONS.
- Allowed request headers: Authorization, Content-Type, Idempotency-Key, Last-Event-ID, X-Trace-Id.
- Allowed Origin response: echo the request Origin; do not use `*`.
- Credentials: do not set `Access-Control-Allow-Credentials` because auth is Bearer header only.
- Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers.
- Success: 204 with empty body. Disallowed Host/Origin/method/header: 403 with standard error shape where possible.
- No route handler, DB write, Job creation, or body parsing is allowed during preflight.
```

Project deletion lifecycle:

```text
- `DELETE /projects/{id}` is soft archive only: set `Project.archived_at=now`, update `updated_at`, return 204.
- `GET /projects` excludes archived projects by default and supports `?include_archived=true` for Settings/admin views.
- `GET /projects/{id}` returns archived projects with `archived_at` so read-only UI can render history.
- Mutating project-scoped APIs reject archived projects with 409 `PROJECT_ARCHIVED`, except export artifact download/reveal/read-only benchmark/report/package reads.
- ProjectRoute edits are allowed only before the first Dataset/EvalSet/Job/ModelRun/Benchmark/AgentPackage exists. After that, `PATCH /projects/{id}` route edits return 409 `ROUTE_TAXONOMY_LOCKED` with the locking resource id; v0 does not support in-place route taxonomy migration.
- Child rows are not deleted by local API archive.
- `ON DELETE CASCADE` FKs exist only for future hard-purge maintenance tools, tests, or explicit admin cleanup outside v0 UI.
- v0 has no hard-delete endpoint. Any hard purge requires a separate ADR and audit event.
```

SSE auth decision:

```text
- Do not use native EventSource in production because it cannot set Authorization headers.
- Use fetch-based streaming SSE client with `Authorization: Bearer ...`.
- `/jobs/{job_id}/events` applies the same token, Host, and Origin checks as JSON endpoints.
- Event payloads are sanitized before serialization.
```

잡 생성 응답:

```json
{
  "job_id": "01JZ...",
  "status": "QUEUED",
  "type": "train",
  "events_url": "/jobs/01JZ.../events",
  "created_resource_type": "model_run",
  "created_resource_id": "01JZ...",
  "idempotency_replayed": false
}
```

SSE 이벤트:

```text
id: {JobEvent.seq}
event: {JobEvent.event_type}
data: {"job_id":"...","seq":12,"ts":"...","level":"info","payload":{...},"trace_id":"..."}
```

`Last-Event-ID`가 있으면 `seq > Last-Event-ID`부터 재전송한다. JobEvent 보존 기준은 job당 최근 5,000개 또는 terminal 후 30일 중 먼저 도달하는 조건이다. 이벤트 보존 기간이 지나 재전송할 수 없으면 409 + `EVENT_GAP`을 반환하고 클라이언트는 `/jobs/{job_id}`를 다시 읽는다.

`EVENT_GAP` body:

```json
{
  "error_code": "EVENT_GAP",
  "message": "Requested event history is no longer available.",
  "details": {
    "job_id": "01JZ...",
    "last_event_id": 12,
    "next_available_seq": 48
  },
  "trace_id": "01JZ..."
}
```

#### 9.6.2 Job submit DTO (v0)

```json
{
  "type": "train",
  "params": {
    "preset_id": "router.basic.v1",
    "dataset_id": "01JZ...",
    "base_model": "google/gemma-2b-it",
    "backend": "cuda",
    "training_preset": "balanced",
    "seed": 42
  }
}
```

검증:

```text
- Client는 `resource_class`를 보내지 않는다. Daemon이 job type과 target backend로 결정한다.
- `train`은 항상 `gpu_exclusive`.
- `benchmark`는 항상 `gpu_exclusive` orchestrator job이다. v0 Benchmark worker는 child Job을 만들지 않고 같은 benchmark job 안에서 target×seed EvalRun 계획을 순차 실행한다. Benchmark에는 fine_tuned/local target이 포함될 수 있으므로 전체 benchmark duration 동안 GPU exclusivity를 예약해 training/eval과 동시 실행되지 않게 한다. 필요하면 evaluator service를 재사용하지만 Job queue에는 parent benchmark job 하나만 존재한다.
- `eval` resource_class는 ad-hoc single target evaluation 전용이며 target backend로 결정한다: cuda/mlx/local_large/prompt_only local inference = `gpu_exclusive`, teacher/rule_based = `cpu_shared`. Benchmark report 생성에는 child eval job을 사용하지 않는다.
- `dataset_gen`, `hardware_scan`, `export(zip)`은 `cpu_shared`. `export(docker)` build도 `cpu_shared`이며 exported runtime smoke는 별도 Docker smoke gate에서 실행한다.
- `type=train`이면 `dataset_id`, `base_model`, `backend`, `seed` 필수.
- `type=dataset_gen` AND `generation_mode=teacher_synthetic`이면 `teacher_packet_approval_id` 필수.
- `teacher_synthetic` is never a Job.type in v0. It is only `Job.type='dataset_gen'` with `params.generation_mode='teacher_synthetic'`.
- `dataset_gen` job with `generation_mode='teacher_synthetic'` 생성 시 TeacherPacketApproval은 approved_at not null, expires_at > now, used_job_id null이어야 하며, Job insert와 같은 transaction에서 used_job_id를 새 job_id로 예약한다.
- `backend=cuda`는 HardwareProfile.capability_gate ∈ {G1,G2} AND gpu_vendor='nvidia'.
- `backend=mlx`는 HardwareProfile.capability_gate ∈ {G1,G2} AND gpu_vendor='apple'.
- `type=benchmark`는 `eval_set_id`가 frozen 상태여야 한다.
- `type=benchmark`의 `params.targets`는 prompt_only, teacher, rule_based를 정확히 1개씩 포함해야 한다. fine_tuned는 selected benchmark model_run 1개가 기본이며, CUDA/MLX parity benchmark에서는 같은 base model family와 같은 eval_set에 대해 fine_tuned target_key를 backend별 2개까지 허용한다. local_large는 optional 1개까지 허용한다.
- `type=eval`은 `params.target`에 동일한 `BenchmarkTargetConfig` 한 개를 포함해야 하며, benchmark worker가 target×seed 단위 실행에 재사용한다.
- prompt_only target은 `base_model` + `prompt_template_sha256`, fine_tuned target은 `model_run_id`, teacher target은 `credential_id` + 허용된 `teacher_base_url_origin`, rule_based target은 `routing_rules_path` + `routing_rules_sha256`가 필수다.
- local_large target이 hardware/profile 제약으로 실행 불가하면 job은 실패하지 않고 report에 `target_status=SKIPPED_OPTIONAL`로 기록한다.
- `type=hardware_scan`은 project_id 없이도 허용하되, 결과 저장 시 machine_id 기준 최신 profile 갱신.
```

#### 9.6.3 Job Control API

`DELETE /jobs/{job_id}`는 즉시 프로세스를 죽이지 않고 취소 요청을 기록한다.

```json
{
  "job_id": "01JZ...",
  "status": "RUNNING",
  "cancel_requested": true,
  "events_url": "/jobs/01JZ.../events"
}
```

상태별 동작:

| API | 허용 상태 | 결과 | 409 조건 |
|---|---|---|---|
| `DELETE /jobs/{id}` | QUEUED | status=CANCELLED | terminal job 재취소 |
| `DELETE /jobs/{id}` | RUNNING | `cancel_requested_at` 설정 | 이미 cancel requested |
| `POST /jobs/{id}/retry` | FAILED/INTERRUPTED/CANCELLED | 새 attempt로 QUEUED | SUCCEEDED/RUNNING/QUEUED |
| `POST /jobs/{id}/resume` | INTERRUPTED/FAILED train job | checkpoint 검증 후 QUEUED | checkpoint/config/dataset mismatch |

retry/resume 규칙:

```text
- retry는 같은 Job row를 재사용하지 않고 parent_job_id를 가리키는 새 Job을 만든다.
- 새 Job.attempt_count = parent.attempt_count + 1.
- resume은 Checkpoint.dataset_id == ModelRun.dataset_id AND Checkpoint.dataset_version == current Dataset.version AND training_config_hash == ModelRun.config_hash일 때만 허용.
- retry/resume 생성 시 JobEvent(status_change)와 AuditEvent(event_type='job_control', action='retry'|'resume', resource_type='job')를 기록한다.
```

#### 9.6.4 Idempotency

Idempotency는 Job 생성 API에서만 `Idempotency-Key` + request body SHA256으로 판정한다.

```text
scope:
  project job: UNIQUE(project_id, idempotency_key) WHERE project_id IS NOT NULL
  system job:  UNIQUE(idempotency_key) WHERE project_id IS NULL
ttl:
  24h. `idempotency_expires_at` 이후 같은 key는 terminal job에서만 release 후 새 요청으로 처리 가능.
body hash:
  validated Pydantic DTO를 canonical JSON으로 직렬화한 SHA256을 `idempotency_body_sha256`에 저장.
replay:
  같은 key + 같은 body hash → 기존 job_id + idempotency_replayed=true.
mismatch:
  같은 key + 다른 body hash → 409 IDEMPOTENCY_BODY_MISMATCH.
null project:
  `project_id IS NULL`은 hardware_scan만 허용. system-scope unique index로 중복 방지.
```

Canonical JSON:

```text
data = dto.model_dump(mode="json", by_alias=True, exclude_none=True)
body = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
sha256 = SHA256(UTF-8(body))
```

Expired key lifecycle:

```text
- Before inserting a new idempotent job, the service runs a `BEGIN IMMEDIATE` transaction.
- It clears `idempotency_key` and `idempotency_body_sha256` only on matching expired jobs in terminal states:
  SUCCEEDED, FAILED, CANCELLED, INTERRUPTED.
- Expired QUEUED/RUNNING jobs do not release their key. They continue to replay/mismatch until terminal or reconciled.
- Retry with a secondary resource rebinds the secondary row to the child job in the same transaction: Benchmark.job_id or ExportArtifact.job_id becomes the child job id. The original failed Job remains immutable and is reachable through parent_job_id/audit history, but read DTOs expose the current controlling job id.
- The partial unique indexes remain unchanged; expired terminal rows are released by application transaction before insert.
```

Non-job POST(`POST /projects`, dataset build request validation, teacher packet preview/approve, credentials upsert)는 v0에서 `Idempotency-Key`를 받지 않는다. 중복 방지는 각 테이블의 UNIQUE constraint, state-transition guard, 또는 409 conflict로 처리한다. v0.2+에서 non-job idempotency가 필요하면 별도 `idempotency_record` 테이블을 추가하는 ADR이 먼저 필요하다.

---

## 13. 기술 스택

### 13.1 Frontend / Desktop

```text
Tauri
React
TypeScript
Tailwind
React Router
TanStack Query
React Hook Form
Zod + JSON Schema bridge
MSW
Vitest + React Testing Library
Playwright + axe
React Flow later
```

초기에는 복잡한 canvas보다 wizard UI가 낫다.

Frontend rules:

```text
- API types are generated from OpenAPI when backend exists; before that, DTOs mirror IMPLEMENTATION_GUIDE §5.
- Server state uses TanStack Query. Long-running jobs use SSE hook + query reconciliation.
- Forms use React Hook Form; validation schemas are derived from Zod or JSON Schema.
- Tables/grids use simple controlled components in M1; virtualized grid can be added after M2.
- E2E happy path is Playwright: create project → add 20 examples → build dataset → observe JobEvent.
```

### 13.2 Local API

```text
FastAPI
Pydantic
SQLAlchemy
SQLite
```

### 13.3 Worker / Training (학습 전용)

**v0 학습 백엔드(플랫폼별 분기):**
- **NVIDIA CUDA**: LLaMA-Factory wrapper (QLoRA via bitsandbytes) — 주 경로.
- **Apple Silicon**: MLX wrapper (mlx-lm LoRA, 4-bit 양자화) — 통합 메모리.

(PEFT/TRL 직접 구현은 v0.3+ 옵션으로 보류)

```text
공통: Python 3.11
NVIDIA: torch 2.4.1 + LLaMA-Factory 0.9.5 + Transformers/PEFT/TRL/Accelerate/bitsandbytes, CUDA 12.1
        대상 OS: Linux, Windows(WSL2)
Apple Silicon: MLX + mlx-lm, macOS 14+ (M1 이상, 통합 RAM ≥16GB)
AMD/Intel GPU: v0 학습 비지원(추론·데이터·eval만)
```

> bitsandbytes NF4 QLoRA는 CUDA 전용이라 Apple Silicon에서 재현 불가 → MLX 4-bit LoRA로 대체.
> 두 백엔드의 eval 지표·품질은 [EVAL_SPEC §17.3](./EVAL_SPEC.md) 기준으로 **동등성(parity) 검증**을 거쳐야 비교 리포트에 함께 표기한다.
> **MLX(Apple Silicon)는 v0 포함이되 M4 parity 게이트 조건부**: parity 실패 시 v0는 CUDA-only로 출시하고 MLX는 v0.2 fast-follow(Dev Plan IR11).
> Ollama/llama.cpp/vLLM는 학습에 쓰지 않는다(§13.4 추론 전용).

### 13.3.1 v0 Base Model 카탈로그 (LOCK)

| 항목 | Model 1 | Model 2 |
|---|---|---|
| HF repo id | `google/gemma-2b-it` | `microsoft/Phi-3.5-mini-instruct` |
| 파라미터 | ~2.5B | ~3.8B |
| License | **Gemma Terms of Use**(상업 이용 허용, 고지·제약 준수) | **MIT** |
| Context length | 8192 | 128K (131072) |
| 학습 seq_len(v0) | ≤1024 | ≤1024 |
| chat template | `tokenizer.apply_chat_template` (system role 미지원 → instruction을 user turn에 prepend) | `tokenizer.apply_chat_template` (system role 지원) |
| trust_remote_code | False | False (transformers ≥4.43 native 지원) |
| LoRA target | all-linear semantics (LLaMA-Factory `lora_target=all`) | all-linear semantics (LLaMA-Factory/MLX config value `all`) |

- HF commit SHA(pin)는 M1 Day-0 fill 산출물 `presets/model_catalog.yaml`에 기록(다운로드 재현성·SHA256 검증, [SECURITY_SPEC §19.7](./SECURITY_SPEC.md)). M0는 필드/검증 계약을 잠그며, `M1_DAY0_FILL` placeholder는 CI `--no-download` 전 반드시 제거한다.
- **Gemma는 Apache-2.0이 아니라 Gemma Terms of Use**이며 export/배포 시 라이선스 고지 필수. Phi-3.5-mini-instruct는 MIT.

### 13.3.2 학습 하이퍼파라미터 기본값 (v0 LOCK)

Training Preset(Quick/Balanced/Production)은 아래 기본을 사용하고 Hardware Doctor 실측으로 보정한다.

| 파라미터 | G1 (2~4B) | G2 (7~8B) |
|---|---|---|
| LoRA rank | 8 | 16 |
| LoRA alpha (=2×rank) | 16 | 32 |
| learning rate | 5e-4 (CUDA) / 1e-4 (MLX) | 동일 |
| lr scheduler | cosine + warmup 100 steps | 동일 |
| epochs | 3 (plateau 시 early-stop) | 3 |
| per-device batch | 1 | 1 |
| grad accumulation | 8 | 16 |
| max grad norm | 1.0 | 1.0 |
| weight decay | 0.01 | 0.01 |
| precision | bf16 (CUDA) / 플랫폼 기본 (MLX) | 동일 |
| gradient checkpointing | ON | ON |
| max_seq_length | 1024 | 1024 |
| optimizer | AdamW (paged on CUDA) | 동일 |
| label masking | output 토큰만 loss (`train_on_outputs_only`) | 동일 |
| seed | 42 (override 가능, Job/Checkpoint 기록) | 동일 |

- Preset 매핑: Quick=1 epoch, Balanced=기본값, Production=3 epoch + 검증셋 early-stop.
- NaN/Inf loss 시 학습 중단 + `error_class=NAN_LOSS`(§8.5).

### 13.3.3 재현성 / 결정성

```text
seed 초기화 순서(공통): random → numpy → torch(+cuda) | mx.random → transformers.set_seed
CUDA: torch.use_deterministic_algorithms(True), CUBLAS_WORKSPACE_CONFIG=:16:8 → 결정적.
MLX(Apple Silicon): Metal/MPS 결정성 보장 없음 → seed 고정해도 run간 ±0.5~1pp 변동 가능.
  대응: ≥3 seed 평균±SD 보고(단일 run 비교 금지). EVAL_SPEC §17.3 parity 게이트가 이를 흡수.
checkpoint resume: 가중치+optimizer 상태+step(+가능 시 RNG) 복원, loss 점프 시 조사.
eval set freeze: 확정 시 SHA256 → EvalSet.sha256 저장, 수정 시 version bump(CI가 동결 위반 검사).
```

### 13.3.4 Trainer Wrapper Contract (v0 LOCK)

Worker의 `train` handler는 backend별 구현을 숨기고 동일한 `TrainerJobInput`을 받는다.

```json
{
  "job_id": "01JZ...",
  "project_id": "01JZ...",
  "model_run_id": "01JZ...",
  "dataset_path": "MIB_HOME/projects/.../dataset.jsonl",
  "dataset_sha256": "64hex",
  "base_model": "google/gemma-2b-it",
  "backend": "cuda",
  "method": "qlora",
  "output_dir": "MIB_HOME/projects/.../runs/{model_run_id}",
  "seed": 42,
  "max_seq_length": 1024,
  "hyperparams": {
    "epochs": 3,
    "lora_rank": 8,
    "lora_alpha": 16,
    "learning_rate": 0.0005,
    "batch_size": 1,
    "grad_accumulation": 8
  }
}
```

위 예시는 CUDA/LLaMA-Factory balanced preset의 canonical input이다. MLX backend는 동일 `TrainerJobInput` envelope를 사용하되 backend config의 기본 learning rate는 §13.3.2의 MLX 기본값인 `0.0001`을 사용한다.

Generated files:

```text
runs/{model_run_id}/
  train_config.json              # canonical TrainerJobInput + hashes
  backend_config.yaml|json       # LLaMA-Factory YAML or MLX config JSON
  adapter/
  checkpoints/{step}/
  logs/train.jsonl
  manifest.json                  # artifact paths + sha256 + backend version
```

CUDA/LLaMA-Factory command template:

```bash
llamafactory-cli train runs/{model_run_id}/backend_config.yaml
```

Required LLaMA-Factory YAML fields:

```yaml
stage: sft
do_train: true
model_name_or_path: "{resolved_hf_model_path}"
dataset: "mib_router_{dataset_id}"
dataset_dir: "runs/{model_run_id}/dataset/llamafactory"
template: "{gemma|phi}"
finetuning_type: lora
lora_target: "{model_catalog.lora_target}"
output_dir: "runs/{model_run_id}/adapter"
overwrite_output_dir: true
cutoff_len: 1024
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 0.0005
num_train_epochs: 3
logging_steps: 10
save_steps: 100
bf16: true
quantization_bit: 4
trust_remote_code: false
seed: 42
```

Required LLaMA-Factory dataset conversion:

```text
runs/{model_run_id}/dataset/llamafactory/
  train.jsonl
  valid.jsonl
  dataset_info.json

Conversion input:
  canonical dataset.jsonl rows from PRESET_SPEC §15.0.

train.jsonl / valid.jsonl row schema:
  {"instruction": string, "input": string, "output": string}

Mapping:
  instruction = row.instruction
  input = json.dumps(row.input, sort_keys=True, ensure_ascii=False)
  output = json.dumps(row.output, sort_keys=True, ensure_ascii=False)

dataset_info.json:
{
  "mib_router_{dataset_id}": {
    "file_name": "train.jsonl",
    "formatting": "alpaca",
    "columns": {
      "prompt": "instruction",
      "query": "input",
      "response": "output"
    }
  }
}

Validation:
  - `output` must validate router_output.schema before conversion.
  - `input.allowed_routes` must equal ProjectRoute snapshot order for the project.
  - deterministic split: validation rows are every 10th approved row, minimum 20 validation rows only when dataset size >=200; otherwise use 10% rounded up.
```

MLX command template:

```bash
python -m mlx_lm.lora \
  --model {hf_model_path} \
  --train \
  --data {dataset_dir} \
  --adapter-path runs/{model_run_id}/adapter \
  --iters {iters} \
  --batch-size 1 \
  --learning-rate {learning_rate}
```

Required MLX dataset/config mapping:

```text
runs/{model_run_id}/dataset/mlx/
  train.jsonl      # exact chat record schema below
  valid.jsonl      # deterministic 10% split, min 20 rows if available

backend_config.json:
{
  "model": "{resolved_hf_model_path}",
  "train": true,
  "data": "runs/{model_run_id}/dataset/mlx",
  "adapter_path": "runs/{model_run_id}/adapter",
  "iters": "{computed from epochs * rows / batch_size}",
  "batch_size": 1,
  "learning_rate": 0.0001,
  "max_seq_length": 1024,
  "seed": 42,
  "trust_remote_code": false
}

MLX train.jsonl / valid.jsonl row schema:
{
  "messages": [
    {"role": "user", "content": "{instruction}\n\n{input_json}"},
    {"role": "assistant", "content": "{output_json}"}
  ]
}

Gemma system-role handling:
  - Gemma has no system role in v0; instruction is prepended to the user content exactly as above.
Phi system-role handling:
  - Phi may support a system role, but v0 keeps the same two-message schema for CUDA/MLX parity unless an ADR changes both wrappers and fixtures.
```

Wrapper obligations:

```text
- stdout/stderr line → JobEvent(log)
- parsed loss → JobEvent(loss)
- parsed or sampled memory → JobEvent(vram)
- generated adapter sha256 → ModelRun.adapter_path + manifest
- known failure → DB error_class enum
- unknown exception → error_class=UNKNOWN, safe error_message only
- no API key/raw example text in logs
```

Golden tests:

```text
- llamafactory_config.golden.yaml snapshot
- mlx_config.golden.json snapshot
- tokenizer/chat-template golden prompt for Gemma and Phi
- router_20.jsonl → train_config.json snapshot
- no-GPU dry-run config generation test
- CUDA smoke and MLX smoke are hardware-gated tests
```

### 13.3.5 Checkpoint / Resume Contract

Checkpoint cadence:

```text
- save every N training steps(default 100) OR every 10 minutes, whichever comes first.
- always save final checkpoint on successful completion.
- keep last 3 checkpoints + best checkpoint by validation route_accuracy.
```

Checkpoint directory:

```text
checkpoints/{step}/
  adapter.safetensors | adapters.npz
  optimizer.pt | optimizer.npz
  trainer_state.json
  rng_state.json                  # best effort; MLX may be partial
  manifest.json                   # dataset_id, dataset_version, config_hash, weights_sha256
```

Resume rules:

```text
- dataset_id, dataset_version, training_config_hash must match current ModelRun.
- backend and base_model must match.
- if optimizer/RNG state is unavailable, resume is allowed only with warning and new EvalRun seed group.
- resume emits JobEvent(status_change: resume_started) and records parent_job_id.
```

Resume tests:

```text
- interrupt after checkpoint → resume → adapter produced.
- mismatch dataset_version → 409 CHECKPOINT_DATASET_MISMATCH.
- mismatch config_hash → 409 CHECKPOINT_CONFIG_MISMATCH.
- resumed run report includes parent_job_id and checkpoint_id.
```

### 13.4 Inference / Eval (추론 전용)

```text
v0/M6: package runtime loader + Transformers/MLX adapter path inside exported zip/Docker
v0.2+ reference: Ollama
v0.2+ reference: llama.cpp
v0.2+ reference: vLLM (NVIDIA only)
Pydantic validation
custom metric scripts
```

### 13.5 Packaging / Export

```text
Docker
local file registry
YAML agent contract
OpenAI-compatible exported runtime endpoint wrapper
MCP server later
```

---

## 14. 데이터 흐름

```text
[User chooses preset]
        ↓
[User inputs rules/examples/schema]
        ↓
[Data Builder creates initial dataset]
        ↓
[Teacher model generates synthetic + hard negatives]
        ↓
[User reviews sample grid]
        ↓
[Training Engine fine-tunes selected locked v0 base model]
        ↓
[Evaluation Engine tests against eval set]
        ↓
[Benchmark Engine compares against large LLM/baseline]
        ↓
[Agent Package Builder creates deployable agent]
        ↓
[User tests in Playground]
        ↓
[Export]
```

---

## 23. Canonical Folder Structure

The canonical implementation tree is [IMPLEMENTATION_GUIDE §3](./IMPLEMENTATION_GUIDE.md). Architecture does not keep a second copy of the tree.

Normative ownership decisions:

```text
- `services/shared/db` owns SQLAlchemy models, migrations, DB session, and repositories.
- `services/shared/security` owns auth, Origin/Host validation, egress policy, redaction, and credential storage.
- `services/api/app` owns FastAPI routes, DTO schemas, service orchestration, and OpenAPI export.
- `services/worker` owns job loop, handler orchestration, runtime adapters, and artifact handoff.
- Worker may import `services/shared/db/repositories/job_store.py`; it must not import `services/api/app/services/*`.
- DB models are split by domain from Day-0. A single `models.py` god file is forbidden.
- A single `core/security.py` god file is forbidden.
```

### 23.1 Code Organization Rules (God File 방지)

구현 세부 규칙은 [IMPLEMENTATION_GUIDE §3.1-§3.3](./IMPLEMENTATION_GUIDE.md)를 따른다. Architecture 관점의 상위 원칙은 아래와 같다.

```text
- layer boundary를 어기는 import는 기본 금지다.
- route/component/handler/model 파일은 orchestration만 담당하고, domain logic을 몰아넣지 않는다.
- 파일이 soft limit을 넘으면 PR에서 split plan을 제시한다.
- 파일이 hard limit을 넘으면 migration/generated 예외가 아닌 한 P1 blocking issue다.
- `utils`, `helpers`, `common` 이름의 무소유 god module은 만들지 않는다.
- 새 abstraction은 기존 local pattern과 일치하거나, ADR/spec 변경으로 먼저 설명되어야 한다.
```

---

## 24. 핵심 DB 모델 (M0 재심사 대상)

초기 SQLite 기준.

> **M0 상태:** 아래 ERD 수준 모델은 개념 지도이고, 실제 구현 기준은 §24.2의 canonical SQLite schema profile이다. M0-7은 BE/DB 리뷰를 통과했으며 §24.2 DDL/인덱스/불변식이 구현 기준이다.

```text
Project
- id
- name
- preset_id
- created_at

Dataset
- id
- project_id
- version
- path
- sha256
- sample_count
- status
- schema_version
- route_snapshot_json # dataset 생성 시점의 ProjectRoute ordered snapshot
- route_snapshot_sha256 # canonical route_snapshot_json SHA256

Example
- id
- dataset_id
- row_index
- input_json
- output_json
- input_sha256
- source
- split
- review_status
- approved

ModelRun
- id
- project_id
- dataset_id
- base_model
- backend
- method
- adapter_path
- adapter_sha256       # adapter artifact canonical SHA256; SUCCEEDED 전까지 nullable
- artifact_manifest_sha256 # adapter manifest canonical SHA256; SUCCEEDED 전까지 nullable
- status
- seed                 # 재현성
- config_json
- config_hash          # SHA256(base_model+method+rank+lr+seed+dataset_version): 재현성/seed 그룹핑
- best_checkpoint_id   # resume 후보 Checkpoint.id(선택)
- resumable            # bool
- started_at
- ended_at
- created_at

Benchmark
- id
- project_id          # FK Project.id (CASCADE)
- eval_set_id         # FK EvalSet.id (frozen gold set, EVAL §17.2)
- job_id              # parent Job.id; retry/resume child가 생기면 현재/최신 controlling job으로 갱신
- status              # QUEUED|RUNNING|COMPLETED|FAILED|CANCELLED|INTERRUPTED
- report_path         # eval runner 자동 생성 리포트(JSON)
- report_sha256       # benchmark_report.json canonical hash
- parity_status       # PASS|FAIL|NA (CUDA/MLX, EVAL §17.3)
- created_at
- completed_at

EvalRun                 # Benchmark의 (target × seed) 결과 1행
- id
- benchmark_id        # FK Benchmark.id (CASCADE)
- model_run_id        # FK ModelRun.id, NULL=비학습 baseline(prompt_only/teacher/rule_based)
- target_key          # benchmark 내 stable key. 예: prompt_gemma, ft_cuda_run01, ft_mlx_run02
- target_type         # prompt_only|fine_tuned|teacher|local_large|rule_based
- backend             # cuda|mlx|teacher|rule_based|prompt_only|local_large
- target_status       # QUEUED|RUNNING|COMPLETED|FAILED|CANCELLED|INTERRUPTED|SKIPPED_OPTIONAL
- target_config_json  # {model_name, base_url, temperature, quantization, judge_prompt_hash, labeler_ids, gold_sha256}
- seed                # target별 ≥3 seed (EVAL §17.3)
- credential_id       # FK Credential.id, NULL 가능(teacher 호출 감사)
- metrics_json        # route_accuracy, task_type_accuracy, unsafe_recall, latency_p50, cost_per_task ...; SKIPPED_OPTIONAL이면 {"skip_reason": "..."} 필수
- created_at

AgentPackage             # 배포 단위(불변): 계약 변경 시 새 버전 행 생성
- id
- agent_id              # exported runtime model id, e.g. support_router.v1
- project_id
- model_run_id
- benchmark_id
- route_catalog_sha256  # contract.route_catalog.sha256와 동일
- contract_yaml
- contract_version       # 정수, 패키지마다 증가
- contract_sha256        # 배포본 무결성/감사 (AGENT_CONTRACT §18)
- created_at

ExportArtifact           # zip/docker export 산출물. AgentPackage 1개가 여러 export를 가질 수 있다.
- id
- job_id                # FK Job.id, UNIQUE
- agent_package_id      # FK AgentPackage.id
- export_type           # zip|docker
- status                # QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED|INTERRUPTED
- manifest_path
- manifest_sha256       # manifest.json canonical SHA256
- artifact_path
- artifact_sha256       # zip archive 또는 docker image tar/digest SHA256
- error_message
- created_at
- completed_at

HardwareProfile
- id
- machine_id
- os
- cpu
- ram_gb
- gpu_vendor
- gpu_name
- vram_gb
- unified_ram_gb
- cuda_status
- mlx_status
- capability_gate
- dry_run_result_json

Job
- id
- project_id
- type            # dataset_gen | train | eval | benchmark | export | hardware_scan
- status          # QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED|INTERRUPTED
- resource_class  # cpu_shared | gpu_exclusive
- priority
- params_json     # train: {preset_id, route_set_hash, base_model, hyperparams, dataset_version, seed}
- idempotency_key # API §9.6 Idempotency-Key 영속화. UNIQUE(project_id, idempotency_key)
- idempotency_body_sha256
- idempotency_expires_at
- attempt_count   # CANCELLED/FAILED→QUEUED 재시도 횟수
- parent_job_id   # FK Job.id, nullable (train→eval→export 워크플로 연결)
- eval_set_id     # FK EvalSet.id, nullable (eval/benchmark/dataset_gen 추적)
- preset_version  # 생성 시 Preset 버전 스냅샷(재현성)
- claimed_by      # worker_id
- claimed_at
- cancel_requested_at
- not_before_at
- error_class     # CUDA_OOM | NAN_LOSS | ... (§8.5)
- error_message
- created_at
- started_at
- ended_at
- heartbeat_at    # Worker가 갱신 (소유권: §8.3)

JobEvent
- id
- job_id
- seq             # SSE Last-Event-ID 재전송 기준
- ts
- level           # debug|info|warn|error
- event_type      # status_change|heartbeat|step|loss|vram|log|artifact|metric|error
- payload_json
- trace_id

Checkpoint
- id
- job_id
- model_run_id
- step
- path
- metrics_json
- dataset_id
- dataset_version      # resume 안전: 현재 Dataset.version과 일치해야 재개 허용
- training_config_hash # ModelRun.config_hash와 일치 검증
- weights_sha256       # 어댑터 무결성
- created_at

Credential
- id
- provider        # v0: openai | openai_compatible (allowlist, SECURITY §19)
- base_url
- keychain_ref    # OS 키체인 참조(평문 키 저장 금지)
- is_revoked      # bool, 401/사용자 폐기 시 1
- revoked_at      # nullable
- expires_at      # nullable
- created_at
- last_used_at

EvalSet
- id
- project_id
- dataset_id
- purpose             # teacher_guard|benchmark_gold|finance_reference
- version
- path
- sha256          # 재현성/오염검증
- sample_count
- route_snapshot_sha256
- labeler_ids_json
- kappa
- frozen_at       # teacher 생성 이전 고정 시점
- is_holdout

SchemaMigration
- version
- applied_at
- description

Preset
- id
- name              # 예: router.basic.v1
- preset_type       # router (v0); extractor|rule_selector|... (v0.2+)
- base_model_options # JSON: 허용 HF model id 목록
- data_template     # JSON: 입력/출력 구조 정의
- training_defaults # JSON: G1/G2 하이퍼파라미터(§13.3.2)
- eval_options      # JSON: metric 목록
- export_options    # JSON
- version
- created_at

ProjectRoute            # Router route taxonomy 영속화(PRESET §6.3)
- id
- project_id          # FK Project.id (CASCADE)
- route_id            # ^[a-z0-9_]+$ ≤64, UNIQUE(project_id, route_id)
- description
- is_unsafe           # bool (unsafe routing 지표용, EVAL §16.1)
- created_at

AuditEvent              # 감사/egress/PII/실패 추적(SECURITY §19.6, §8.5)
- id
- ts
- event_type          # pii_mask|teacher_egress|credential_access|export|agent_run|job_failure
- resource_type       # job|credential|eval_run|agent_package|dataset
- resource_id         # nullable (trace_id/job_id 등)
- action              # masked|kept|sent|approved|revoked|error
- policy_version      # PII/정책 버전(재현)
- details_json        # {entities:[{type,span,action}], error_class, vram_peak ...}
- trace_id
- retention_until     # UTC ISO-8601. v0 minimum 365 days.
- contract_sha256     # agent_run/export 관련 감사일 때 contract snapshot hash
- created_at
```

### 24.1 스키마 규약 (v0 LOCK)

```text
타입: *_json = TEXT(JSON), 시간 = ISO-8601 TEXT, bool = INTEGER(0/1).
SQLite 주의: CHECK/UNIQUE/FK는 ALTER ADD 불가 → CREATE TABLE 시점에 정의(스키마 변경은 Alembic로 재생성).

FK (ON DELETE CASCADE는 별도 표기):
  Project.preset_id→Preset.id
  Dataset.project_id→Project.id (CASCADE), Example.dataset_id→Dataset.id (CASCADE)
  ProjectRoute.project_id→Project.id (CASCADE)
  ModelRun.project_id→Project.id, ModelRun.dataset_id→Dataset.id
  Job.project_id→Project.id, Job.parent_job_id→Job.id (nullable), Job.eval_set_id→EvalSet.id (nullable)
  JobEvent.job_id→Job.id (CASCADE)
  Checkpoint.job_id→Job.id, Checkpoint.model_run_id→ModelRun.id, Checkpoint.dataset_id→Dataset.id
  Benchmark.project_id→Project.id (CASCADE), Benchmark.eval_set_id→EvalSet.id
  EvalRun.benchmark_id→Benchmark.id (CASCADE), EvalRun.model_run_id→ModelRun.id (nullable),
    EvalRun.credential_id→Credential.id (nullable)
  AgentPackage.project_id→Project.id, AgentPackage.model_run_id→ModelRun.id, AgentPackage.benchmark_id→Benchmark.id
  ExportArtifact.job_id→Job.id, ExportArtifact.agent_package_id→AgentPackage.id
  EvalSet.project_id→Project.id, EvalSet.dataset_id→Dataset.id

CHECK/UNIQUE (enum 무결성):
  Example.review_status ∈ {PENDING,APPROVED,REJECTED,EDITED}
  Job.status ∈ {QUEUED,RUNNING,SUCCEEDED,FAILED,CANCELLED,INTERRUPTED}
  Job.type ∈ {dataset_gen,train,eval,benchmark,export,hardware_scan}
  Job.resource_class ∈ {cpu_shared,gpu_exclusive}
  Job.error_class ∈ {NULL,CUDA_OOM,NAN_LOSS,DISK_FULL,MODEL_DOWNLOAD_FAIL,TEACHER_API_ERROR,TIMEOUT,
                     SCHEMA_VALIDATION_FAIL,PERMISSION_DENIED,ARTIFACT_MISSING,UNKNOWN}
  UNIQUE(Job.project_id, Job.idempotency_key) WHERE idempotency_key IS NOT NULL AND project_id IS NOT NULL
  UNIQUE(Job.idempotency_key) WHERE idempotency_key IS NOT NULL AND project_id IS NULL
  UNIQUE(resource_class) WHERE resource_class='gpu_exclusive' AND status='RUNNING'
  Benchmark.status ∈ {QUEUED,RUNNING,COMPLETED,FAILED,CANCELLED,INTERRUPTED}; parity_status ∈ {PASS,FAIL,NA}
  EvalRun.target_type ∈ {prompt_only,fine_tuned,teacher,local_large,rule_based}
  EvalRun.backend ∈ {cuda,mlx,teacher,rule_based,prompt_only,local_large}
  EvalRun.target_status ∈ {QUEUED,RUNNING,COMPLETED,FAILED,CANCELLED,INTERRUPTED,SKIPPED_OPTIONAL}; SKIPPED_OPTIONAL은 target_type='local_large' AND seed=0일 때만 허용. benchmark_report에는 COMPLETED/FAILED/SKIPPED_OPTIONAL terminal targets만 직렬화한다.
  UNIQUE(EvalRun.benchmark_id, EvalRun.target_key, EvalRun.seed)
  ExportArtifact.export_type ∈ {zip,docker}; ExportArtifact.status ∈ Job.status와 동일
  Credential.provider ∈ {openai,openai_compatible}(v0); is_revoked ∈ {0,1}; UNIQUE(provider)
  ProjectRoute.is_unsafe ∈ {0,1}; UNIQUE(project_id, route_id)
  Preset.preset_type ∈ {router}(v0); UNIQUE(name, version); Preset 불변(새 버전=새 행)
  HardwareProfile.dry_run_result_json: json_valid + $.gate∈{G0,G1,G2} + $.risk∈{low,medium,high}

인덱스:
  Job(project_id,status,created_at), JobEvent(job_id,seq), Example(dataset_id,approved),
  Checkpoint(job_id,step DESC), ModelRun(project_id,created_at DESC),
  Benchmark(project_id,eval_set_id), EvalRun(benchmark_id,target_key),
  ExportArtifact(agent_package_id,export_type,created_at),
  ProjectRoute(project_id,is_unsafe), AuditEvent(ts DESC), AuditEvent(resource_id), AuditEvent(retention_until)

소유권/단일 writer (§8.3): RUNNING 잡의 status·heartbeat_at·JobEvent는 Worker가 기록(진실의 원천).
  Daemon은 heartbeat_at < now()-60s 인 RUNNING 잡만 INTERRUPTED로 reconcile(BEGIN IMMEDIATE).
  Local Runtime(추론)은 DB 읽기 전용.

resume 안전: Checkpoint.dataset_version == Dataset.version AND training_config_hash == ModelRun.config_hash 일 때만 허용.

보존/유지보수: JobEvent는 잡당 최근 5,000개 또는 terminal 후 30일 중 먼저 도달하는 조건으로 보존(초과분 pruning), 주기적 PRAGMA optimize/VACUUM.
  AuditEvent.retention_until은 생성 시점+max(contract.retention_days, 365일)로 계산한다. v0 AuditEvent 보존 최소값은 365일이다. 멀티테넌시(workspace_id)는 v0 미도입 — 필요 시 상위 테이블에
  nullable workspace_id를 Alembic으로 추가(데이터 재작성 불필요).

SQLite: WAL + busy_timeout=5000ms. 마이그레이션: Alembic(alembic.ini + versions/), 초기 리비전 포함.
큐 파라미터: heartbeat_interval=10s, reconcile_interval=15s, heartbeat_timeout=60s, JobEvent 기록 = step OR 30s(먼저 도달), 취소 = SIGTERM→(10s)→SIGKILL.

HardwareProfile.dry_run_result_json:
  { gate:"G0|G1|G2", gpu_vendor, vram_gb|unified_ram_gb, cuda:bool, mlx:bool,
    training_enabled:bool, training_disabled_reason_code, training_disabled_reason_message,
    allowed_backends:["cuda"|"mlx"], unlock_requirements:[string],
    model, seq_len, batch, grad_accum, lora_rank,
    vram_peak_gb, tokens_per_sec, est_minutes_per_1k:number, risk:"low|medium|high",
    failure_details:{code,message}|null }
```

### 24.2 Canonical SQLite Schema Profile (v0 LOCK)

ORM 클래스명은 `Project`, `Job`처럼 PascalCase를 쓰되 실제 테이블명은 lower_snake_case로 고정한다. `id`는 정렬 가능한 TEXT ULID(또는 UUIDv7)이며, 시간은 UTC ISO-8601 TEXT다.

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE preset (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  preset_type TEXT NOT NULL CHECK (preset_type IN ('router')),
  version INTEGER NOT NULL CHECK (version > 0),
  base_model_options_json TEXT NOT NULL CHECK (json_valid(base_model_options_json)),
  data_template_json TEXT NOT NULL CHECK (json_valid(data_template_json)),
  training_defaults_json TEXT NOT NULL CHECK (json_valid(training_defaults_json)),
  eval_options_json TEXT NOT NULL CHECK (json_valid(eval_options_json)),
  export_options_json TEXT NOT NULL CHECK (json_valid(export_options_json)),
  created_at TEXT NOT NULL,
  UNIQUE (name, version)
);

CREATE TABLE project (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
  preset_id TEXT NOT NULL REFERENCES preset(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT
);

CREATE TABLE project_route (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  route_id TEXT NOT NULL CHECK (length(route_id) BETWEEN 1 AND 64),
  description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 2000),
  is_unsafe INTEGER NOT NULL DEFAULT 0 CHECK (is_unsafe IN (0,1)),
  created_at TEXT NOT NULL,
  UNIQUE (project_id, route_id)
);

CREATE TABLE dataset (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK (version > 0),
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  sample_count INTEGER NOT NULL DEFAULT 0 CHECK (sample_count >= 0),
  status TEXT NOT NULL CHECK (status IN ('DRAFT','BUILT','REVIEWED','APPROVED','ARCHIVED')),
  schema_version TEXT NOT NULL,
  route_snapshot_json TEXT NOT NULL CHECK (json_valid(route_snapshot_json)),
  route_snapshot_sha256 TEXT NOT NULL CHECK (length(route_snapshot_sha256) = 64),
  created_at TEXT NOT NULL,
  frozen_at TEXT,
  UNIQUE (project_id, version)
);

CREATE TABLE example (
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL REFERENCES dataset(id) ON DELETE CASCADE,
  row_index INTEGER NOT NULL CHECK (row_index >= 0),
  input_json TEXT NOT NULL CHECK (json_valid(input_json)),
  output_json TEXT NOT NULL CHECK (json_valid(output_json)),
  input_sha256 TEXT NOT NULL CHECK (length(input_sha256) = 64),
  source TEXT NOT NULL CHECK (source IN ('user','import','teacher','hard_negative','eval_gold')),
  split TEXT NOT NULL CHECK (split IN ('train','validation','eval')),
  review_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (review_status IN ('PENDING','APPROVED','REJECTED','EDITED')),
  approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0,1)),
  created_at TEXT NOT NULL,
  UNIQUE (dataset_id, row_index)
);

CREATE TABLE eval_set (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  dataset_id TEXT NOT NULL REFERENCES dataset(id),
  version INTEGER NOT NULL CHECK (version > 0),
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  sample_count INTEGER NOT NULL CHECK (sample_count > 0),
  purpose TEXT NOT NULL CHECK (purpose IN ('teacher_guard','benchmark_gold','finance_reference')),
  route_snapshot_sha256 TEXT NOT NULL CHECK (length(route_snapshot_sha256) = 64),
  labeler_ids_json TEXT NOT NULL CHECK (json_valid(labeler_ids_json)),
  kappa REAL CHECK (kappa IS NULL OR (kappa >= 0 AND kappa <= 1)),
  frozen_at TEXT NOT NULL,
  is_holdout INTEGER NOT NULL DEFAULT 0 CHECK (is_holdout IN (0,1)),
  created_at TEXT NOT NULL,
  UNIQUE (project_id, version)
);

CREATE TABLE hardware_profile (
  id TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL,
  os TEXT NOT NULL,
  cpu TEXT,
  ram_gb REAL NOT NULL CHECK (ram_gb > 0),
  gpu_vendor TEXT NOT NULL CHECK (gpu_vendor IN ('nvidia','apple','amd','intel','none','unknown')),
  gpu_name TEXT,
  vram_gb REAL,
  unified_ram_gb REAL,
  cuda_status TEXT CHECK (cuda_status IN ('ok','missing','unsupported','na')),
  mlx_status TEXT CHECK (mlx_status IN ('ok','missing','unsupported','na')),
  capability_gate TEXT NOT NULL CHECK (capability_gate IN ('G0','G1','G2')),
  dry_run_result_json TEXT NOT NULL CHECK (json_valid(dry_run_result_json)),
  created_at TEXT NOT NULL
);

CREATE TABLE credential (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL CHECK (provider IN ('openai','openai_compatible')),
  base_url TEXT NOT NULL,
  keychain_ref TEXT NOT NULL,
  is_revoked INTEGER NOT NULL DEFAULT 0 CHECK (is_revoked IN (0,1)),
  revoked_at TEXT,
  expires_at TEXT,
  created_at TEXT NOT NULL,
  last_used_at TEXT,
  UNIQUE (provider)
);

CREATE TABLE job (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES project(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('dataset_gen','train','eval','benchmark','export','hardware_scan')),
  resource_class TEXT NOT NULL CHECK (resource_class IN ('cpu_shared','gpu_exclusive')),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')),
  priority INTEGER NOT NULL DEFAULT 0,
  params_json TEXT NOT NULL CHECK (json_valid(params_json)),
  idempotency_key TEXT,
  idempotency_body_sha256 TEXT CHECK (idempotency_body_sha256 IS NULL OR length(idempotency_body_sha256) = 64),
  idempotency_expires_at TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  parent_job_id TEXT REFERENCES job(id),
  eval_set_id TEXT REFERENCES eval_set(id),
  preset_version INTEGER,
  claimed_by TEXT,
  claimed_at TEXT,
  cancel_requested_at TEXT,
  not_before_at TEXT,
  error_class TEXT CHECK (error_class IS NULL OR error_class IN (
    'CUDA_OOM','NAN_LOSS','DISK_FULL','MODEL_DOWNLOAD_FAIL','TEACHER_API_ERROR',
    'TIMEOUT','SCHEMA_VALIDATION_FAIL','PERMISSION_DENIED','ARTIFACT_MISSING','UNKNOWN'
  )),
  error_message TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  heartbeat_at TEXT
);

CREATE TABLE job_event (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES job(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL CHECK (seq > 0),
  ts TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('debug','info','warn','error')),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'status_change','heartbeat','step','loss','vram','log','artifact','metric','error'
  )),
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  trace_id TEXT NOT NULL,
  UNIQUE (job_id, seq)
);

CREATE TABLE job_resource (
  job_id TEXT PRIMARY KEY REFERENCES job(id) ON DELETE CASCADE,
  resource_type TEXT NOT NULL CHECK (resource_type IN ('dataset','model_run','benchmark','export_artifact','hardware_profile')),
  resource_id TEXT NOT NULL,
  is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)),
  created_at TEXT NOT NULL
);

CREATE TABLE teacher_packet_approval (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  dataset_id TEXT NOT NULL REFERENCES dataset(id),
  packet_sha256 TEXT NOT NULL CHECK (length(packet_sha256) = 64),
  packet_json TEXT NOT NULL CHECK (json_valid(packet_json)),
  pii_summary_json TEXT NOT NULL CHECK (json_valid(pii_summary_json)),
  approved_at TEXT,
  expires_at TEXT NOT NULL,
  used_job_id TEXT UNIQUE REFERENCES job(id),
  created_at TEXT NOT NULL
);

CREATE TABLE model_run (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  dataset_id TEXT NOT NULL REFERENCES dataset(id),
  base_model TEXT NOT NULL CHECK (base_model IN ('google/gemma-2b-it','microsoft/Phi-3.5-mini-instruct')),
  backend TEXT NOT NULL CHECK (backend IN ('cuda','mlx')),
  method TEXT NOT NULL CHECK (method IN ('qlora','mlx_lora')),
  adapter_path TEXT,
  adapter_sha256 TEXT CHECK (adapter_sha256 IS NULL OR length(adapter_sha256) = 64),
  artifact_manifest_sha256 TEXT CHECK (artifact_manifest_sha256 IS NULL OR length(artifact_manifest_sha256) = 64),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')),
  seed INTEGER NOT NULL,
  config_json TEXT NOT NULL CHECK (json_valid(config_json)),
  config_hash TEXT NOT NULL CHECK (length(config_hash) = 64),
  best_checkpoint_id TEXT,
  resumable INTEGER NOT NULL DEFAULT 0 CHECK (resumable IN (0,1)),
  started_at TEXT,
  ended_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE checkpoint (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES job(id),
  model_run_id TEXT NOT NULL REFERENCES model_run(id) ON DELETE CASCADE,
  step INTEGER NOT NULL CHECK (step >= 0),
  path TEXT NOT NULL,
  metrics_json TEXT NOT NULL CHECK (json_valid(metrics_json)),
  dataset_id TEXT NOT NULL REFERENCES dataset(id),
  dataset_version INTEGER NOT NULL CHECK (dataset_version > 0),
  training_config_hash TEXT NOT NULL CHECK (length(training_config_hash) = 64),
  weights_sha256 TEXT NOT NULL CHECK (length(weights_sha256) = 64),
  created_at TEXT NOT NULL,
  UNIQUE (model_run_id, step)
);

CREATE TABLE benchmark (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  eval_set_id TEXT NOT NULL REFERENCES eval_set(id),
  job_id TEXT NOT NULL UNIQUE REFERENCES job(id),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','INTERRUPTED')),
  report_path TEXT,
  report_sha256 TEXT CHECK (report_sha256 IS NULL OR length(report_sha256) = 64),
  parity_status TEXT NOT NULL DEFAULT 'NA' CHECK (parity_status IN ('PASS','FAIL','NA')),
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE eval_run (
  id TEXT PRIMARY KEY,
  benchmark_id TEXT NOT NULL REFERENCES benchmark(id) ON DELETE CASCADE,
  model_run_id TEXT REFERENCES model_run(id),
  target_key TEXT NOT NULL CHECK (length(target_key) BETWEEN 1 AND 80),
  target_type TEXT NOT NULL CHECK (target_type IN ('prompt_only','fine_tuned','teacher','local_large','rule_based')),
  backend TEXT NOT NULL CHECK (backend IN ('cuda','mlx','teacher','rule_based','prompt_only','local_large')),
  target_status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (target_status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','INTERRUPTED','SKIPPED_OPTIONAL')),
  target_config_json TEXT NOT NULL CHECK (json_valid(target_config_json)),
  seed INTEGER NOT NULL,
  credential_id TEXT REFERENCES credential(id),
  metrics_json TEXT NOT NULL CHECK (json_valid(metrics_json)),
  created_at TEXT NOT NULL,
  CHECK (target_status != 'SKIPPED_OPTIONAL' OR (target_type = 'local_large' AND seed = 0)),
  UNIQUE (benchmark_id, target_key, seed)
);

CREATE TABLE agent_package (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL CHECK (agent_id GLOB '[a-z0-9_]*.v[0-9]*'),
  project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  model_run_id TEXT NOT NULL REFERENCES model_run(id),
  benchmark_id TEXT NOT NULL REFERENCES benchmark(id),
  route_catalog_sha256 TEXT NOT NULL CHECK (length(route_catalog_sha256) = 64),
  contract_yaml TEXT NOT NULL,
  contract_version INTEGER NOT NULL CHECK (contract_version > 0),
  contract_sha256 TEXT NOT NULL CHECK (length(contract_sha256) = 64),
  created_at TEXT NOT NULL,
  UNIQUE (project_id, contract_version),
  UNIQUE (project_id, agent_id)
);

CREATE TABLE export_artifact (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL UNIQUE REFERENCES job(id),
  agent_package_id TEXT NOT NULL REFERENCES agent_package(id),
  export_type TEXT NOT NULL CHECK (export_type IN ('zip','docker')),
  status TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED')),
  manifest_path TEXT,
  manifest_sha256 TEXT CHECK (manifest_sha256 IS NULL OR length(manifest_sha256) = 64),
  artifact_path TEXT,
  artifact_sha256 TEXT CHECK (artifact_sha256 IS NULL OR length(artifact_sha256) = 64),
  error_message TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE audit_event (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'pii_mask','teacher_egress','credential_access','export','agent_run','job_failure','job_control','job_reconcile','security'
  )),
  resource_type TEXT NOT NULL CHECK (resource_type IN (
    'job','credential','eval_run','agent_package','export_artifact','dataset','project','system'
  )),
  resource_id TEXT,
  action TEXT NOT NULL,
  policy_version TEXT,
  details_json TEXT NOT NULL CHECK (json_valid(details_json)),
  trace_id TEXT,
  retention_until TEXT NOT NULL,
  contract_sha256 TEXT CHECK (contract_sha256 IS NULL OR length(contract_sha256) = 64),
  created_at TEXT NOT NULL
);

CREATE TABLE schema_migration (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL,
  description TEXT NOT NULL
);
```

Required indexes:

```sql
CREATE INDEX ix_project_updated_at ON project(updated_at DESC);
CREATE INDEX ix_dataset_project_version ON dataset(project_id, version DESC);
CREATE INDEX ix_example_dataset_approved ON example(dataset_id, approved);
CREATE INDEX ix_example_input_sha256 ON example(input_sha256);
CREATE INDEX ix_eval_set_project_version ON eval_set(project_id, version DESC);
CREATE INDEX ix_eval_set_dataset ON eval_set(dataset_id);
CREATE INDEX ix_hardware_profile_machine_created ON hardware_profile(machine_id, created_at DESC);
CREATE INDEX ix_job_project_status_created ON job(project_id, status, created_at);
CREATE INDEX ix_job_status_priority_created ON job(status, priority DESC, created_at);
CREATE INDEX ix_job_heartbeat ON job(status, heartbeat_at);
CREATE INDEX ix_job_event_job_seq ON job_event(job_id, seq);
CREATE INDEX ix_job_resource_resource_current ON job_resource(resource_type, resource_id, is_current);
CREATE UNIQUE INDEX ux_job_resource_current
ON job_resource(resource_type, resource_id)
WHERE is_current = 1;
CREATE INDEX ix_teacher_packet_project_created ON teacher_packet_approval(project_id, created_at DESC);
CREATE INDEX ix_teacher_packet_sha ON teacher_packet_approval(packet_sha256);
CREATE INDEX ix_model_run_project_created ON model_run(project_id, created_at DESC);
CREATE INDEX ix_checkpoint_model_step ON checkpoint(model_run_id, step DESC);
CREATE INDEX ix_benchmark_project_eval_set ON benchmark(project_id, eval_set_id);
CREATE INDEX ix_eval_run_benchmark_target_key ON eval_run(benchmark_id, target_key);
CREATE INDEX ix_eval_run_benchmark_target_type ON eval_run(benchmark_id, target_type);
CREATE INDEX ix_export_artifact_package_type ON export_artifact(agent_package_id, export_type, created_at DESC);
CREATE INDEX ix_export_artifact_job ON export_artifact(job_id);
CREATE INDEX ix_project_route_project_unsafe ON project_route(project_id, is_unsafe);
CREATE INDEX ix_audit_event_ts ON audit_event(ts DESC);
CREATE INDEX ix_audit_event_resource ON audit_event(resource_type, resource_id);
CREATE INDEX ix_audit_event_retention ON audit_event(retention_until);

CREATE UNIQUE INDEX ux_job_idempotency_project
  ON job(project_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL AND project_id IS NOT NULL;

CREATE UNIQUE INDEX ux_job_idempotency_system
  ON job(idempotency_key)
  WHERE idempotency_key IS NOT NULL AND project_id IS NULL;

CREATE UNIQUE INDEX ux_one_running_gpu_job
  ON job(resource_class)
  WHERE resource_class = 'gpu_exclusive' AND status = 'RUNNING';
```

### 24.3 DB Invariants / Application-Level Checks

SQLite `CHECK`만으로 표현하기 어려운 규칙은 서비스 레이어와 테스트에서 강제한다.

```text
1. route_id regex(`^[a-z0-9_]+$`)는 Pydantic + preset validator에서 검사한다.
2. Dataset.status='APPROVED'인 데이터셋만 train job에 사용할 수 있다.
3. Dataset.route_snapshot_json은 ProjectRoute를 `created_at,id` 순으로 정렬한 canonical snapshot이며, Dataset.route_snapshot_sha256은 그 canonical JSON SHA256이다. 승인된 Example.input.allowed_routes는 이 snapshot의 route_id 순서와 같아야 한다.
4. `dataset_gen`/`generation_mode=teacher_synthetic` job 생성 전에는 같은 dataset route_snapshot_sha256을 가진 `EvalSet.purpose='teacher_guard'`가 frozen 상태여야 한다.
5. Benchmark job은 `EvalSet.purpose IN ('benchmark_gold','finance_reference')`만 허용한다. `teacher_guard`는 release/benchmark claim에 사용할 수 없다.
6. `test_eval_train_no_overlap`은 Example.input_sha256 exact 중복 0 + embedding 유사도 flag 0을 확인한다.
7. train job backend=cuda이면 HardwareProfile.gpu_vendor='nvidia' AND capability_gate∈{G1,G2}.
8. train job backend=mlx이면 HardwareProfile.gpu_vendor='apple' AND capability_gate∈{G1,G2}.
9. `model_run.method='qlora'`는 backend='cuda'에서만 허용하고, `method='mlx_lora'`는 backend='mlx'에서만 허용한다.
10. `job.project_id IS NULL`은 `type='hardware_scan'`에서만 허용한다. Generic `POST /projects/{id}/jobs`는 hardware_scan/export를 받지 않고, 전용 endpoint가 해당 Job row를 만든다.
11. Checkpoint resume은 `checkpoint.dataset_id == model_run.dataset_id` AND
   `checkpoint.training_config_hash == model_run.config_hash`일 때만 허용한다.
12. `model_run.best_checkpoint_id`는 circular FK를 피하기 위한 soft reference다. 읽을 때 Checkpoint 존재를 검증한다.
13. Benchmark는 prompt_only, teacher, rule_based target을 정확히 1개씩 가져야 하며 fine_tuned target은 1개 또는 CUDA/MLX parity용 2개만 허용한다. 각 required target_key별 COMPLETED distinct seed가 최소 3개 이상이어야 Benchmark가 COMPLETED가 될 수 있다. CUDA/MLX parity는 `target_type='fine_tuned'` target_key 2개(`backend='cuda'`, `backend='mlx'`)로 표현한다. optional local_large는 COMPLETED distinct seed ≥3 또는 `SKIPPED_OPTIONAL` seed=0 1행 중 하나를 가져야 한다.
14. AgentPackage contract는 불변이다. agent_id/route_catalog_sha256/contract_yaml/model_run_id/benchmark_id/contract_version/contract_sha256을 수정하지 않고 새 contract_version 행을 만든다. AgentPackage.model_run_id와 benchmark_id는 같은 project_id에 속해야 하며, Benchmark.status='COMPLETED'이고 report_path/report_sha256 재계산 결과가 `hash_status='VALID'`일 때만 package 생성 가능하다. `hash_status`는 DB에 저장하지 않고 read/service layer에서 report file을 재해시해 산출한다. agent_id는 서버가 `{slug}.v{contract_version}`으로 할당하며 contract.route_catalog.sha256은 AgentPackage.route_catalog_sha256과 같아야 한다.
15. ExportArtifact는 export job 생성 시 QUEUED로 선생성한다. zip과 docker는 같은 AgentPackage에 대해 별도 ExportArtifact 행을 가진다. SUCCEEDED 전환은 manifest_sha256과 artifact_sha256 검증 후에만 가능하다.
16. Credential.keychain_ref만 DB에 저장한다. 실제 키 값은 DB/로그/AuditEvent에 쓰지 않는다.
17. `Job.type='dataset_gen'` and `params.generation_mode='teacher_synthetic'`인 job은 unexpired TeacherPacketApproval.approved_at이 있고 packet_sha256이 재계산값과 일치해야 생성 가능하다. retry/resume 시 기존 approval은 재사용하지 않고 새 TeacherPacketApproval을 요구한다.
18. JobEvent.seq는 `BEGIN IMMEDIATE` 안에서 `COALESCE(MAX(seq),0)+1`로 할당하고 같은 트랜잭션에서 insert한다.
19. Example.review_status='APPROVED'이면 approved=1, REJECTED이면 approved=0이어야 한다. EDITED는 input_json/output_json 재검증 후 APPROVED 또는 PENDING으로 전환 가능하다.
20. ModelRun.status='SUCCEEDED'이면 adapter_path, adapter_sha256, artifact_manifest_sha256이 모두 non-null이어야 한다.
21. AuditEvent.retention_until은 `created_at + max(contract.audit.retention_days, 365 days)` 이상이어야 한다.
22. JobResource는 job이 생성한 대표 resource를 연결하는 구조화된 링크다. 최초 train submit transaction은 `Job(type='train')`, `ModelRun(status='QUEUED')`, `JobResource(job_id=job.id, resource_type='model_run', resource_id=model_run.id, is_current=1)`을 함께 insert한다. `ModelRunRead.job_id`와 retry/resume current job lookup은 `job_resource(resource_type='model_run', resource_id=model_run.id, is_current=1)`에서 읽고, `params_json`을 파싱해 job을 찾지 않는다. 새 retry/resume child job이 같은 resource를 제어하면 기존 JobResource.is_current=0, child JobResource.is_current=1을 같은 transaction에서 갱신한다. `ux_job_resource_current`가 resource별 current link 1개만 허용한다.
```

### 24.4 Migration / Alembic Acceptance

M1 Day-0의 초기 리비전은 아래를 통과해야 한다.

```text
- `alembic upgrade head` 후 모든 테이블/FK/index/partial index가 생성된다.
- `alembic downgrade base`가 빈 DB에서 성공한다.
- SQLite `PRAGMA foreign_key_check` 결과 0건.
- `PRAGMA integrity_check` = ok.
- seed preset(`router.basic.v1`) 삽입 후 Project 생성 smoke test 통과.
- job claim 동시성 테스트: 두 worker가 동시에 gpu_exclusive job을 claim해도 RUNNING은 1개.
- orphan artifact reconcile test: DB SUCCEEDED + missing file이면 boot reconcile이 AuditEvent를 남긴다.
```

DB review evidence bundle:

```text
docs/reviews/M0/DB_REVIEW.md에 아래를 첨부하거나 링크한다.
- `alembic upgrade head` log
- `alembic downgrade base` log
- `SELECT name,type,sql FROM sqlite_master ORDER BY type,name` dump
- `PRAGMA foreign_key_check` 결과
- `PRAGMA integrity_check` 결과
- DB pytest result: §24.3 invariant 전체 매핑
- seed dump: router.basic.v1 preset row + model_catalog load result
- idempotency proof: project scope + system scope unique index tests
```

---

## 31. 개발 환경 (Dev Environment)

### 31.1 지원 매트릭스

| OS | 앱/데이터/추론/eval | 로컬 학습 |
|---|---|---|
| Ubuntu 22.04+ (NVIDIA) | O | O (권장) |
| Windows 11 + WSL2 (NVIDIA) | O | O |
| Windows 11 네이티브 (NVIDIA) | O | △ (WSL2 권장) |
| macOS Apple Silicon (M1+, ≥16GB) | O | O (MLX: ≥16GB→G1, ≥32GB→G2) |
| 비-NVIDIA GPU(AMD/Intel) | O | X |

### 31.2 툴체인 (M0 LOCK · exact patch는 M1 Day-0 environment files에서 기록)

```text
Node.js 20 LTS + pnpm 9.x            # 데스크탑/웹 UI
Rust stable + Tauri 2.x              # 데스크탑 셰
Python 3.11.x (임베디드)             # Daemon + Worker
repo-local .venv                     # IDE/개발 기본 interpreter
pip + requirements*.txt exact pins   # IDE/pip-audit 호환 dependency source
SQLite 3.40+ (WAL)
Docker(선택)                         # export 산출물 실행용

# 학습(NVIDIA)
CUDA 12.1 + NVIDIA driver 535~560
torch 2.4.1+cu121
transformers 4.56.2
peft 0.18.0 / trl 0.24.0 / accelerate 1.11.0 / bitsandbytes 0.49.2
LLaMA-Factory 0.9.5

# 학습(Apple Silicon)
MLX 0.31.2 + mlx-lm 0.31.3 + transformers 5.0.0 (torch 불필요)

# eval/CI
sentence-transformers (all-MiniLM-L6-v2)  # overlap 검사(EVAL_SPEC §17.1)
pytest / ruff / pip-audit                 # 테스트·린트·CVE
```

> Apple Silicon은 torch 설치 불필요(MLX 단독). M0는 호환성 라인(major/minor)을 잠그고, 정확한 patch 버전과 해시는 M1 Day-0 산출물 `requirements.txt` / `requirements-mlx.txt` / `requirements-dev.txt`에 기록한다.

### 31.3 로컬 셋업(개발자)

```text
1. python3.11 -m venv .venv
2. . .venv/bin/activate
3. python -m pip install --upgrade pip
4. NVIDIA/Linux/WSL2: python -m pip install -r requirements.txt -r requirements-dev.txt
5. Apple Silicon:     python -m pip install -r requirements-mlx.txt -r requirements-dev.txt
6. corepack enable && corepack pnpm install
7. corepack pnpm tauri dev          # M1-007 Tauri/Vite scaffold 생성 후에만 실행
8. 사전: NVIDIA 드라이버/CUDA(또는 Apple Silicon ≥16GB), Python 3.11
9. CI: lint + type-check + unit + 오염검증 테스트 + dry-run 학습 스모크
```

Docker는 M1~M5 개발 셋업 명령에 포함하지 않는다. Docker는 M6 export image build/run smoke에만 필요하다([DEV_ENVIRONMENT_SPEC §36.8](./DEV_ENVIRONMENT_SPEC.md)).

### 31.4 환경 변수 / 시크릿

```text
- API 키는 .env가 아니라 OS 키체인(SECURITY_SPEC §19.4). `.env`의 유일한 v0 secret 예외는 Day-0 gated HF model catalog fill용 local-only `HF_TOKEN`이며, 앱 런타임 credential 저장소로 쓰지 않는다.
- MIB_HOME(프로젝트/모델/DB 경로), MIB_DAEMON_PORT(랜덤 기본), MIB_LOG_LEVEL.
```

---

## 32. 언어/스택 적합성 (Language/Stack Fit)

| 레이어 | 선택 | 근거 | 대안/리스크 |
|---|---|---|---|
| 데스크톱 셸 | Tauri 2 (Rust) | 경량 번들·OS 키체인/파일 접근·보안 기본값, Electron 대비 작은 용량 | Electron(용량↑), Rust 학습비용 |
| UI | React + TypeScript + Tailwind | 생태계·채용·wizard UI 빠른 구현 | — |
| 로컬 API | FastAPI (Python) | ML 생태계와 동일 언어로 마찰 최소, Pydantic 스키마 검증 | Rust API는 ML 연동 마찰로 v0 제외 |
| Worker | Python | transformers/peft/trl/LLaMA-Factory/MLX가 Python 1급 | — |
| 학습 | LLaMA-Factory(CUDA) + MLX(Apple Silicon) | 다모델 QLoRA 검증된 경로, 자체구현 대비 시간 절약(§13.3) | 이중 백엔드 parity 부담 |
| 추론 | Ollama/llama.cpp/vLLM/Transformers | 폭넓은 로컬 추론·OpenAI 호환 | vLLM은 NVIDIA 한정 |
| 저장 | SQLite (WAL) + 파일 | 단일 사용자 로컬앱에 충분, 무설치 | 동시성 한계→단일 워커로 회피 |
| 마이그레이션 | Alembic | 스키마 버전관리 | — |

> **핵심 판단:** API/Worker를 모두 Python으로 두어 ML 마찰을 없애고, Rust는 셸(보안·배포)에 한정한다. 단일 사용자·단일 GPU 가정 덕분에 Redis/Celery/분산학습은 v0에서 불필요하다.
