# 보안 / 프라이버시 명세 (SECURITY_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [ARCHITECTURE](./ARCHITECTURE.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md)

---

## 19. 보안/프라이버시 설계

Teacher AI를 연결하려면 사용자가 외부로 전송되는 데이터를 명확히 알아야 한다.

> **v0 데이터 egress 정책(확정):** v0는 **BYO API Key 단일 경로**만 지원한다. **기본값은 "룰/스키마 + 익명화 예시(PII 비전송)"** 이며, 사용자가 전송 전 packet을 검토·승인해야 외부로 나간다. "외부 전송 없음(Local Only)"는 정확히는 *Cloud Teacher 미사용*을 의미한다. 마케팅은 *"Local 학습 + 선택적 Cloud Teacher"* 로 표기하고 "데이터가 절대 나가지 않는다"는 무조건 표현은 쓰지 않는다.
>
> **v0 provider allowlist(LOCK):** OpenAI(`api.openai.com`) + 사용자가 지정하는 OpenAI 호환 `base_url` 1개(자체 호스팅 포함). 그 외 도메인 차단. Teacher Packet은 JSON `{rules, schema, anonymized_examples[], instruction}` 으로만 전송.

### 19.1 Teacher Packet Preview

```text
이번 요청에서 외부로 전송되는 내용:
- rule schema
- anonymized examples 20개
- output schema
- generation instruction

전송되지 않는 내용:
- 원본 CSV 전체
- 파일 경로
- 개인식별정보
- 비승인 샘플
```

#### 19.1.1 Teacher Packet Approval Contract (v0 LOCK)

Flow:

```text
1. FE calls `POST /projects/{id}/teacher-packets/preview`.
2. Daemon builds packet `{rules, schema, anonymized_examples, instruction}` and validates SECURITY_SPEC §19.10 schema.
3. Daemon computes `packet_sha256` using canonical JSON: sort keys, compact separators, UTF-8 SHA256.
4. Daemon stores TeacherPacketApproval with `approved_at=NULL`, `expires_at=now+30m`, packet_json, pii_summary_json.
5. FE displays packet preview and "Approve" action.
6. FE calls `POST /teacher-packets/{id}/approve`.
7. Daemon sets `approved_at=now`.
8. Synthetic generation job must include `teacher_packet_approval_id`.
9. During job creation, Daemon reloads the approval row, verifies `approved_at IS NOT NULL`, `expires_at > now`, `used_job_id IS NULL`, and packet_sha256 match.
10. In the same transaction as Job insert, Daemon stores packet snapshot in `Job.params_json` and sets `TeacherPacketApproval.used_job_id = job_id`.
11. Before egress, Worker reloads the approval row and verifies `used_job_id == job_id` and packet_sha256 matches the Job packet snapshot. Expiry is not rechecked after reservation.
```

Required rejection:

```text
- Missing approval: 409 TEACHER_PACKET_APPROVAL_REQUIRED.
- Expired approval: 409 TEACHER_PACKET_APPROVAL_EXPIRED.
- SHA mismatch: 409 TEACHER_PACKET_SHA_MISMATCH.
- Already used by another job: 409 TEACHER_PACKET_ALREADY_USED.
- Retry/resume of a `dataset_gen` job whose `params.generation_mode='teacher_synthetic'` requires a new TeacherPacketApproval unless it is an idempotent replay of the same original job.
```

### 19.2 전송 옵션 (v0 LOCK)

```text
[x] 기본: 룰/스키마 + 익명화 예시 전송(PII 마스킹, Preview 승인 필수)
[ ] 최소 전송: 룰/스키마만 전송(예시 미포함)
[ ] Local Only: 외부 전송 금지(Cloud Teacher 비활성)
[x] 원본 데이터 전송 차단: v0 고정(향후 enterprise policy + 명시적 DPA/감사 통제 후 재검토)
```

### 19.3 실행 모드

| 모드 | 설명 |
|---|---|
| Local Only | 인터넷 없이 실행. 외부 전송 없음 |
| Connected Teacher | 로컬 데이터/학습 + teacher AI만 선택적 cloud 사용 |
| Managed Compute | 승인된 데이터만 cloud GPU에서 학습 |

### 19.4 자격증명(API 키) 저장 — 필수

```text
- 저장소: OS 키체인 강제 (macOS Keychain / Windows Credential Manager / Linux Secret Service).
- 구현: Python `keyring` 라이브러리(상기 백엔드 자동 선택).
- 키체인 불가(headless Linux 등): v0에서는 Connected Teacher 자격증명 저장을 비활성화하고 사용자에게 OS keychain 필요 경고를 표시한다. 암호화 파일 폴백은 v0.2+ 별도 ADR 전까지 구현하지 않는다.
- 금지: 평문 SQLite/설정파일/로그에 키 저장.
- DB: Credential은 keychain_ref만 저장(평문 키 미저장, ARCHITECTURE §24).
- 수명주기: Credential.{is_revoked, revoked_at, expires_at} 관리. Teacher 호출 전 Daemon이 is_revoked/expires_at 검사, 401 응답 시 is_revoked=1 + AuditEvent(credential_access, revoked) 기록(ARCHITECTURE §24).
- 로그/audit: 키·토큰 마스킹(****), input은 해시만(AGENT_CONTRACT_SPEC §18).
- 회전/폐기: UI에서 키 교체·삭제, 손상 의심 시 경고.
```

### 19.5 로컬 API 인증 — 필수

```text
- 바인딩: 127.0.0.1 고정(0.0.0.0 금지) + 랜덤 포트.
- 인증: 부팅 시 생성한 랜덤 토큰(Bearer) 필수, production 토큰은 Tauri 메모리에만 보관한다.
- 토큰: 256-bit CSPRNG(`secrets.token_urlsafe(32)`), 앱 세션마다 재발급.
- bootstrap: Tauri가 Daemon을 child process로 실행하고 stdout 첫 줄의 `MIB_BOOTSTRAP` JSON을 읽어 base_url/token을 메모리에 보관한다. 토큰은 keychain/DB/log/file에 저장하지 않는다.
- Tauri command: `get_api_bootstrap() -> { baseUrl, token }`. FE는 앱 시작 시 이 command로 API client를 만든다.
- dev auth mode:
  - `MIB_DEV_AUTH=bootstrap`(default): stdout bootstrap token required.
  - `MIB_DEV_AUTH=token_file`: `.mib-dev-token` 파일 허용(dev only).
  - `MIB_DEV_AUTH=bypass`: auth bypass 허용(dev only, bind host 127.0.0.1 필수).
  - production은 `bootstrap`만 허용하며 다른 값이면 앱 시작을 중단한다.
- DNS-rebinding/CSRF 방지: Origin·Host 허용목록 검증, 비브라우저 클라이언트는 토큰 필수.
- 허용 Origin: `tauri://localhost` (+ dev `http://localhost:1420`). Host 헤더는 `127.0.0.1:{port}`만 production 허용, `localhost:{port}`는 dev에서 127.0.0.1로 해석될 때만 허용.
- CORS preflight(`OPTIONS` + `Origin` + `Access-Control-Request-Method`)는 Host/Origin allowlist 통과 후 Bearer 없이 204를 반환한다. 허용 method/header는 ARCHITECTURE §9.6.1과 동일하며, preflight 중에는 body parsing, DB write, Job 생성, AuditEvent 생성을 금지한다.
- 입력 검증·요청 크기 제한·잡 트리거 rate limit.
```

### 19.6 PII 탐지/마스킹 — 명세

```text
- 엔티티(v0 결정적 정규식+사전): email, phone(KR/E.164), KR 주민등록번호(`\d{6}-?[1-4]\d{6}`),
  카드 PAN(Luhn 검증), 계좌번호, IP, 이름(사전+문맥), 주소(키워드).
  마스킹 토큰: <EMAIL> <PHONE> <RRN> <CARD> <ACCT> <NAME> 등.
- 2차(옵션): 경량 NER(presidio류). v0 기본 OFF(결정성 우선), 사용자 opt-in.
- 목표 미탐율(FN) ≤ 2%: 라벨된 PII holdout(n≥300, 합성+레드팀 케이스)로 측정,
  CI 회귀 테스트(test_pii_masking_recall)로 게이트.
- Corpus path: `examples/security/pii_holdout.v1.jsonl`. Each row must validate against `schemas/pii_holdout.schema.json`.
- Day-0 scaffold contains schema samples only. M2 security implementation must expand this file to n≥300 before Security GO; `test_pii_holdout_min300` fails if fewer rows exist outside scaffold phase.
- Label spans are Python string offsets `[start,end)` over the exact JSON `text` value. Entity `text` must equal `text[start:end]`.
- Required composition for the full corpus: at least 40 rows each for email, phone, name, and address; at least 25 rows each for rrn, card, account, and ip; at least 60 red_team rows with mixed punctuation/spacing/Unicode confusables.
- audit record: { request_id, ts, entities:[{type, span, action:masked|kept}], policy_version }.
- 전송 전 'Teacher Packet Preview'에서 마스킹 결과를 사용자가 최종 검토.
```

### 19.7 공급망 보안

```text
- 모델/어댑터 다운로드 SHA256 매니페스트 검증(HF Hub API 파일 메타 sha 대조 + 로컬 재계산 일치).
- transformers trust_remote_code = False 기본, 모델별 명시적 opt-in.
- pip-audit/Dependabot로 의존성 CVE 점검(bitsandbytes 등).
- CI 통합: `.github/workflows/security.yml` — profile-specific pip-audit, model manifest 검증, repo secret scan, pnpm audit, Rust/Tauri audit gate, export secret scan contract를 Phase 1부터 필수 잡(ARCHITECTURE §31.3 CI에 보안 단계 추가).
- 모델 매니페스트: `presets/model_catalog.yaml`의 각 model은 `hf_commit_sha`, `trust_remote_code=false`, `files[{path,sha256,size_bytes,required}]`를 가진다. M1 strict catalog는 모델마다 최소 1개 이상의 required weight shard(`model.safetensors`, `model-*.safetensors`, `pytorch_model.bin`, `pytorch_model-*.bin`)를 포함해야 한다.
- 검증 스크립트: `python3 scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_verification.json`는 40-hex commit/hash 누락, `trust_remote_code=true`, 중복 model id, required weight shard 누락, 64-hex가 아닌 file sha256을 실패 처리한다. 현재 M0 GO 이후 PR/CI/부트스트랩은 strict mode만 증거로 인정하며, `--allow-day0-placeholders`는 local pre-M0 template 실험용 예외다.
- dependency file 정책: `requirements.txt`, `requirements-mlx.txt`, `requirements-dev.txt`는 정확한 version pin을 사용한다. 범위 지정(`>=`, `~=`)은 CI 실패다.
- export secret scan: M6 export job은 artifact 생성 후 `python3 scripts/scan_export_artifact.py --artifact <zip-or-dir>`를 실행한다. API key, bearer token, raw credential pattern이 하나라도 발견되면 export job은 FAILED가 되고 ExportArtifact.status도 FAILED다.
- Node/Rust scans: `corepack pnpm audit --audit-level high`는 high 이상 advisory가 있으면 실패한다. `cargo audit --file src-tauri/Cargo.lock`은 Tauri scaffold 후 필수이며, scaffold 전에는 workflow가 명시적으로 skip 로그를 남긴다.
- 향후 Recipe Hub/Domain Pack: 서명·코드리뷰·재현빌드 요구.
```

### 19.8 Enterprise 보안 주장 분리

```text
- air-gapped/암호화/컴플라이언스 audit 등([PRODUCT_SPEC §20.4](./PRODUCT_SPEC.md) Enterprise 티어)은 통제가 구현되기 전까지
  본 계획서의 v0 기능에서 제외하고 별도 'Enterprise Roadmap' 문서로 이관한다.
- v0 문서에는 미구현 보안 기능을 기능처럼 기재하지 않는다(컴플라이언스 리스크).
```

### 19.9 Security Test Matrix (v0 LOCK)

| Area | Required tests / evidence |
|---|---|
| Credential | `test_key_saved_to_keyring`, `test_key_not_in_sqlite`, `test_key_not_in_logs`, revoke/delete/rotate tests |
| Local API auth | `test_missing_token_401`, `test_bad_token_401`, `test_constant_time_token_check`, `test_bootstrap_stdout_single_line`, `test_token_not_logged`, `test_dev_token_rejected_in_prod` |
| Host/Origin | `test_host_not_local_rejected`, `test_origin_not_allowlisted_rejected`, `test_cors_preflight_allowlist` |
| SSE auth | `test_sse_requires_token`, `test_sse_rejects_cross_origin`, `test_sse_event_gap_does_not_leak_payload` |
| Egress | `test_provider_allowlist`, `test_https_required_for_openai`, `test_redirect_to_unlisted_host_denied`, `test_private_ip_denied`, `test_dns_rebinding_denied`, `test_ip_literal_normalized`, `test_trust_env_false`, `test_fallback_uses_same_pinned_dns_transport` |
| PII | `test_pii_holdout_schema`, `test_pii_holdout_min300`, `test_pii_masking_recall`, `test_pii_masking_snapshots`, `test_packet_preview_requires_approval`, `test_teacher_packet_sha_mismatch_rejected`, `test_logs_redacted` |
| Supply chain | `test_model_manifest_sha256`, `test_trust_remote_code_false`, `pip-audit`, `corepack pnpm audit --audit-level high`, SBOM, Rust/Tauri dependency scan |
| Export | `test_export_manifest_hashes`, `test_export_contains_no_api_key`, `test_export_contract_sha256`, `scripts/scan_export_artifact.py --artifact <artifact>` |

Security Agent GO requires all P0/P1 tests above to pass or have an explicit CTO waiver in `docs/reviews/M{n}/CTO_DECISION.md`.

### 19.10 Egress Enforcement Contract

Provider URL handling:

```text
- Normalize with a strict URL parser before allowlist comparison.
- Allowed schemes: https only for OpenAI; http allowed only for user-provided localhost/self-hosted base_url.
- OpenAI host: api.openai.com only.
- Custom OpenAI-compatible base_url: exactly one user-approved origin(scheme+host+port).
- Deny redirects by default. If redirects are enabled later, every redirect target must pass allowlist again.
- Deny private/metadata IP ranges for non-localhost providers: 127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16, ::1, fc00::/7.
- HTTP client uses `trust_env=False` so proxy env vars cannot bypass allowlist.
- Timeout: connect 10s, read 60s. Retries: max 2, no retry on 4xx except 429 with bounded backoff.
- Max teacher packet size: 1MB v0.
```

`normalize_and_validate_teacher_origin(base_url, user_allowed_origin)` algorithm:

```text
1. Parse with a strict URL parser. Reject parse errors, username/password, query, fragment.
2. Lowercase scheme/host. Normalize IDNA host to ASCII. Remove trailing dot. Normalize default port(https=443, http=80).
3. Build origin = scheme + host + port. Path is allowed only as API prefix for custom base_url; origin comparison ignores path.
4. If provider=openai:
   - require scheme=https, host=api.openai.com, port=443.
5. If provider=openai_compatible:
   - require origin exactly equals the single user-approved origin.
   - allow http only when host is `localhost`, `127.0.0.1`, or `::1`.
6. If host is an IP literal, normalize it and classify it before DNS.
7. Resolve all A and AAAA records with system resolver.
8. Reject if any resolved IP is private, loopback, link-local, multicast, unspecified, or metadata range, unless the approved origin is explicit localhost self-host.
9. Store `resolved_ips` and `checked_at` in memory for this request only.
10. The HTTP transport must connect only to an IP from the validated `resolved_ips` set. It must preserve the original hostname for TLS SNI and the `Host` header.
11. Before each network call, resolve again. If IP set changed, re-run steps 7-8. If policy changes from allow to deny, abort before opening a socket.
12. A plain `httpx.Client(base_url=origin)` without a validated resolver/transport wrapper is forbidden because it can re-resolve after validation.
13. HTTP client must use `follow_redirects=False` and `trust_env=False`.
14. If a future version enables redirects, every redirect target must rerun this algorithm before following.
```

Teacher Packet JSON Schema:

```json
{
  "type": "object",
  "required": ["rules", "schema", "anonymized_examples", "instruction"],
  "additionalProperties": false,
  "properties": {
    "rules": { "type": "array" },
    "schema": { "type": "object" },
    "anonymized_examples": { "type": "array", "maxItems": 50 },
    "instruction": { "type": "string", "maxLength": 8000 }
  }
}
```

AuditEvent(`teacher_egress`) details:

```json
{
  "provider": "openai_compatible",
  "base_url_origin": "https://api.openai.com",
  "approval_id": "01JZ...",
  "used_job_id": "01JZ...",
  "packet_sha256": "64hex",
  "pii_policy_version": "pii.v1",
  "approved_by_user": true,
  "example_count": 20,
  "bytes": 12345
}
```

### 19.11 Credential Storage Contract

Keyring naming:

```text
service: MIB Studio
account: credential:{provider}:{base_url_sha256}
keychain_ref: keyring://MIB%20Studio/credential:{provider}:{base_url_sha256}
```

Lifecycle:

| Action | DB change | Keyring change | AuditEvent |
|---|---|---|---|
| create/update | upsert Credential.keychain_ref, is_revoked=0 | set_password | credential_access:set |
| revoke | is_revoked=1, revoked_at=now | keep or delete per user choice | credential_access:revoked |
| delete | is_revoked=1, revoked_at=now | delete_password | credential_access:deleted |
| rotate | new keychain secret, same Credential id | set_password | credential_access:rotated |

Fallback encrypted file:

```text
- v0 does not implement credential encrypted-file fallback.
- If OS keychain is unavailable, Connected Teacher credential create/update returns 503 KEYCHAIN_UNAVAILABLE.
- Existing credentials remain inaccessible until keychain becomes available.
- Plaintext fallback is forbidden.
- Any future encrypted fallback requires a new ADR specifying cipher, KDF, file format, unlock lifecycle, and cross-platform tests.
```

Data classification:

```text
- Local project DB may contain user examples and therefore sensitive business data.
- API keys, bearer tokens, and raw secrets must never be stored in DB/logs.
- Raw examples must never appear in JobEvent, AuditEvent, crash reports, or teacher egress without masking/approval.
```
