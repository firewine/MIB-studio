# UX_SPEC — UX / 정보 구조 / 화면 명세 (§35)

> 범위: **MIB Studio v0(Router 프리셋)의 화면·정보 구조(IA)·워크플로·UI 상태 규약**을 정의한다.
> 관련: [PRODUCT_SPEC](./PRODUCT_SPEC.md) · [PRESET_SPEC](./PRESET_SPEC.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [HARDWARE_DOCTOR_SPEC](./HARDWARE_DOCTOR_SPEC.md) · [SECURITY_SPEC](./SECURITY_SPEC.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md) · [ARCHITECTURE](./ARCHITECTURE.md)
> 시각 캐논(canonical mockup): [`docs/mockup/mib_fe_mockup_v6_routes_contract.html`](../mockup/mib_fe_mockup_v6_routes_contract.html) — 본 문서가 정의하는 Router route-contract builder 흐름을 구현한 단일 파일 고충실도 목업. `docs/mockup/README.md`가 명시하듯 이전 HTML mockup은 archive이며, 구현 기준이 아니다.

---

## 35.0 목적·범위·캐논

- 본 문서는 **무엇을 보여줄지(IA)와 어떻게 행동할지(UX 상태)** 를 규정한다. 비주얼 디테일·인터랙션은 캐논 목업이 보유한다.
- v0 범위는 **Agent Type = Router 1종**([MVP_SCOPE §21](./MVP_SCOPE.md))이다. 다른 프리셋(Extractor/Rule Selector 등)은 화면상 **비활성(v0.2+)** 로만 노출한다.
- 핵심 제품 명제를 모든 화면이 일관되게 드러내야 한다: **"Big models teach · Small agents work · Rules govern · Benchmarks prove."**
- 본 문서와 캐논 목업이 불일치하면 **본 문서가 우선**한다. 목업은 본 문서 변경 시 동일 이터레이션에서 갱신한다.

## 35.1 정보 구조(IA) & 내비게이션

앱 셸은 3영역으로 고정한다.

- **상단바(top bar):** 현재 프로젝트·현재 화면 브레드크럼, **작업 큐 표시기**(실행 중 잡 수/진행률, 클릭 시 해당 잡으로 이동), **Hardware 등급 배지**(G0/G1/G2 + GPU/백엔드), **Local-only · Teacher 연결 상태** 칩, 설정.
- **사이드바:** 프로젝트 스위처 + `대시보드` + **워크플로 스테퍼**(7단계, 상태: done/current/locked) + 관리(설정·Hardware Doctor).
- **메인:** 현재 화면. 화면 헤더는 `단계 태그 · 제목 · 1–2문장 설명 · 주요 액션`을 갖는다.

규칙:
- 워크플로는 **선형 진행**을 기본으로 하되, 완료된 단계는 자유 이동 가능. **잠금(locked) 단계는 내비게이션하지 않고** 사유 토스트("학습 완료 후 활성화")를 띄운다.
- 비동기 작업(데이터 생성·학습·평가·내보내기)은 **백그라운드 잡**으로 실행되며 상단바 작업 큐에서 항상 가시화한다([ARCHITECTURE §8 작업 큐](./ARCHITECTURE.md)).

## 35.2 핵심 워크플로(7단계) & 화면 인벤토리

| # | 화면 | 사용자 책임 | 핵심 노출 | 근거 스펙 |
|---|---|---|---|---|
| — | 대시보드 | 에이전트·실행 이력 개요, 신규 시작 | 에이전트 목록(상태·vs-Teacher·cost), 최근 학습 실행 | PRODUCT_SPEC §4–5 |
| 1 | Hardware Doctor | 학습 가능 등급 확인 | G0/G1/G2 매트릭스, dry-run(VRAM/속도/리스크) | [HARDWARE_DOCTOR_SPEC §11–12](./HARDWARE_DOCTOR_SPEC.md) |
| 2 | 정의(Define) | Router route 정의 | route(2–12, `^[a-z0-9_]+$` ≤64)·unsafe 표시·출력 계약 | [PRESET_SPEC §6.1–6.3, §15.4](./PRESET_SPEC.md) |
| 3 | 데이터(Data) | 시드 입력·생성·검수·버전 | 시드/룰, Teacher Packet Preview, 검수 그리드(필터·페이지), 데이터셋 이력 | [PRESET_SPEC §15](./PRESET_SPEC.md) · [SECURITY_SPEC §19.6](./SECURITY_SPEC.md) |
| 4 | 학습(Train/Monitor) | 프리셋·하이퍼파라미터·실행 | base/backend, 프리셋(Quick/Balanced/Production), loss·VRAM·로그, 오류/재개 | [ARCHITECTURE §13.3.2, §8.3, §8.5](./ARCHITECTURE.md) |
| 5 | 벤치마크(AgentBench) | 대체 가능성 증명 | 필수 4타깃 + 선택 Local-large 비교(정확도±CI·unsafe·latency·effective cost), parity, 방법론 | [EVAL_SPEC §16–17](./EVAL_SPEC.md) |
| 6 | 패키지·플레이그라운드 | 계약 확인·테스트 | schema·verifier·fallback·audit, 입력→출력 검증, fallback 임계값 | [AGENT_CONTRACT_SPEC §18](./AGENT_CONTRACT_SPEC.md) |
| 7 | 내보내기(Export) | 배포 | zip · Docker API, OpenAI-compatible wrapper는 exported runtime 내부 기능, 패키지 구성, 라이선스 고지 | [ARCHITECTURE §9.6](./ARCHITECTURE.md) · [PRODUCT_SPEC](./PRODUCT_SPEC.md) |

부가: 설정(자격증명·데이터 전송 정책).

## 35.3 UI 상태 규약 (필수)

각 화면은 아래 상태를 **명시적으로** 처리한다(없으면 미완성으로 간주). 전체 canonical state matrix와 CTA 규칙은 [IMPLEMENTATION_GUIDE §14.4](./IMPLEMENTATION_GUIDE.md)를 따른다.

- **로딩/실행 중:** 백그라운드 잡은 진행률·ETA·로그 스트림(JobEvent)을 보여준다.
- **빈(empty)/최초 실행:** 대시보드는 신규 에이전트 진입(프리셋 선택 → Hardware Doctor 자동 실행)을 제공한다.
- **오류(error):** 학습/생성 실패는 **`error_class`를 표면화**한다(`CUDA_OOM·NAN_LOSS·DISK_FULL·TEACHER_API_ERROR·TIMEOUT`). 마지막 정상 체크포인트 보존 사실과 **복구 액션**(체크포인트 재개 · 로그 보기 · 파라미터 조정 후 재시작)을 함께 제시한다([ARCHITECTURE §8.5](./ARCHITECTURE.md)).
- **체크포인트 재개:** 체크포인트 목록을 제공하고 `dataset_version`·`config_hash` 불일치 항목은 **재개 차단(stale)** 으로 표시한다([ARCHITECTURE §8.3](./ARCHITECTURE.md)).
- **잠금(locked):** 미달성 단계는 비활성 + 사유 안내. 클릭 시 진입하지 않는다.

## 35.4 Hardware Doctor 게이팅 UX

- 진단 결과 등급에 따라 **단계 가용성**을 제어한다.
  - **G0**(GPU 없음/<12GB): 학습 단계 **비활성**. 데이터 생성·검수·추론/플레이그라운드만 허용("Teacher 경로만 진행").
  - **G1**(NVIDIA ≥12GB · Apple Silicon ≥16GB): 2~4B QLoRA 학습 가능(v0 핵심 경로).
  - **G2**(NVIDIA ≥24GB · Apple Silicon ≥32GB): 7~8B 학습·로컬 Teacher(v0.2+).
- dry-run 추정(VRAM peak·tokens/sec·시간·리스크)과 변동 폭(±) 고지를 함께 노출한다.

## 35.5 데이터 전송·Teacher Packet·자격증명 UX

- **Teacher Packet Preview(전송 전 승인 필수):** 전송됨/전송 안 됨 항목을 명시하고, **PII 마스킹 적용 범위**(주민번호·계좌·카드·이메일·전화·IP·이름·주소)를 보여준다([SECURITY_SPEC §19.6](./SECURITY_SPEC.md)). 문구는 "데이터가 절대 나가지 않음"이 아니라 **"Local 학습 + 선택적 Cloud Teacher"** 로 정직하게 표현한다.
- **자격증명:** v0는 **BYO key(OpenAI/OpenAI 호환) 단일 경로**. 키는 OS 키체인에만 저장([SECURITY_SPEC §19.4](./SECURITY_SPEC.md)). 연결 상태(미연결/연결됨)와 검증·테스트 액션을 제공하고, **키 미연결 시 데이터 생성 차단**을 안내한다. 비허용 provider(Anthropic·Gemini·OpenRouter)는 v0.2+로 비활성 표기.

## 35.6 벤치마크 표현 규칙 & 실행 이력

- **"증명" 프레이밍:** "대형 LLM보다 똑똑하다"가 아니라 **이 반복 업무에서 small agent가 대형 호출을 대체 가능한지**를 정확도·비용·속도로 보여준다.
- **표준 비교:** 필수 4타깃(Prompt-only · Fine-tuned(우리) · Teacher · Rule-only) + 선택 Local-large. Local-large는 하드웨어가 없으면 `SKIPPED_OPTIONAL`로 표시한다. 지표: route accuracy(±95% CI), unsafe recall/precision, latency p50/p95, **effective cost/task(fallback 포함)**([EVAL_SPEC §16–17](./EVAL_SPEC.md)).
- **신뢰성 표기 강제:** 미검증 수치는 **"예시(미검증)"** 로 라벨하고, frozen eval SHA·seed·CI·LLM-judge κ를 함께 노출한다. 리포트는 eval runner가 자동 생성(수기 금지).
- **CUDA↔MLX parity 조건부:** parity PASS면 양 백엔드 결과를 함께 보고. **FAIL이면 v0는 CUDA 전용 출시 + MLX는 공유 리포트에서 제외·v0.2 연기**임을 명시([EVAL_SPEC §17.3](./EVAL_SPEC.md)).
- **per-route/cost 분해:** unsafe 라우트별 recall/precision, effective cost 산출 내역(토큰·단가·fallback율·민감도)을 확장 표시.
- **실행 이력(run history / adapter registry):** 대시보드에 최근 학습 실행을 보존·노출한다. 각 실행은 `adapter · config_hash · dataset_version · benchmark report`와 함께 저장되어 **재사용·비교**가 가능하다([ARCHITECTURE §24 ModelRun/Checkpoint](./ARCHITECTURE.md)).

## 35.7 접근성·시각 기준 (baseline)

- 활성 내비 항목에 `aria-current`, 모달 닫기 버튼에 `aria-label`, 토스트에 `role=status`(`aria-live=polite`), 오류 카드에 `role=alert`.
- 키보드: 모달은 `Esc`로 닫기. 포커스 가시성(`:focus-visible`) 보장.
- 상태 색(ok/warn/danger/info)은 텍스트 대비 WCAG AA를 목표로 하고, 색에만 의존하지 않도록 라벨/아이콘을 병기한다.

## 35.8 추적성 & 변경 관리

- 본 문서의 각 화면은 §35.2 표의 근거 스펙과 1:1로 추적된다. 스펙(특히 PRESET/EVAL/SECURITY/HARDWARE_DOCTOR/AGENT_CONTRACT/ARCHITECTURE)이 바뀌면 본 문서와 캐논 목업을 같은 이터레이션에서 갱신한다.
- 캐논 목업의 모든 개정은 파일 상단 주석 `VERSION HISTORY`에 **날짜·변경·근거·영향 섹션**을 누적(이전 항목 보존)한다.
