# 제품 정의서 (PRODUCT_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다. 타 문서를 가리키는 §참조는 해당 스펙 문서에서 찾는다.
> 관련: [PRESET_SPEC](./PRESET_SPEC.md) · [MVP_SCOPE](./MVP_SCOPE.md) · [COMPETITIVE_ANALYSIS](./COMPETITIVE_ANALYSIS.md)

---

## 1. 제품 한 줄 정의 (장기 비전)

**MIB Studio는 (장기적으로) 비전문가도 GUI에서 룰, 예시, 데이터, 대상 2~12B 모델, 평가 기준을 블록/프리셋으로 조합하여 특수목적 Small Agent를 학습·평가·배포할 수 있게 하는 Local-first Agent 제작 스튜디오다.**

> **v0 MVP 타깃(확정):** "비전문가"는 **장기 비전**이며, v0 MVP의 실제 타깃은 **GPU/Python 환경을 다룰 수 있는 tech-savvy 업무 사용자**다([MVP_SCOPE §21](./MVP_SCOPE.md)). §4 핵심 사용자 목록도 모두 기술/도메인 전문 역할이다. small agent는 대형 LLM 완전 대체가 아니라 반복 업무 저비용 처리 + fallback 포지셔닝.

핵심 철학:

```text
Big models teach.
Small agents work.
Rules govern.
Benchmarks prove.
```

의미:

- **Big models teach**: GPT/Gemini/Claude/24B+ 로컬 모델은 teacher, judge, fallback 역할을 한다.
- **Small agents work**: 2~12B 모델은 좁은 역할의 specialist agent로 학습되어 빠르고 싸게 반복 업무를 처리한다.
- **Rules govern**: 룰, 스키마, verifier, permission, fallback policy가 small agent를 통제한다.
- **Benchmarks prove**: 학습 결과는 대형 LLM, prompt-only baseline, rule-only baseline과 성능·비용·속도로 비교된다.

---

## 2. 제품 포지션

MIB Studio는 단순 Fine-tuning GUI도 아니고, 일반 Agent Workflow Builder도 아니다.

| 구분 | 기존 제품군 | MIB Studio의 차별점 |
|---|---|---|
| Fine-tuning GUI | H2O LLM Studio, AutoTrain, LLaMA-Factory | 모델 학습 자체보다 **Agent Contract + Eval + Export**에 집중 |
| Agent Builder | Dify, Langflow, Flowise, CrewAI, LangGraph Studio | workflow를 그리는 것이 아니라 그 안에 넣을 **small specialist agent**를 제작 |
| Rule Engine | GoRules, DecisionRules, Drools | 룰 실행만이 아니라 룰/예시를 **학습 데이터·hard negative·eval set**으로 변환 |
| Eval/Observability | LangSmith, Kiln | task/eval 중심을 넘어 **룰 기반 small agent 제작 UX** 제공 |
| Model Cost Reduction | OpenPipe | production prompt 치환뿐 아니라 **비전문가용 룰→agent 제작 GUI** 제공 |

제품 카테고리:

```text
Rule-to-Small-Agent Studio
Small Agent Macro Studio
MIT App Inventor for Small Agents
```

---

## 3. 네이밍 구조

### 3.1 메인 브랜드

```text
MIB Studio
```

공식 풀네임 후보:

```text
MicroAgent Inventor Blocks
Model · Instruct · Benchmark
```

### 3.2 내부 모듈명

```text
MIB Studio
 ├─ Blocks UI
 ├─ Recipe Hub
 ├─ AgentBench
 ├─ IMF Engine
 ├─ NoFate Guard
 └─ Rebel Runtime
```

| 모듈 | 의미 |
|---|---|
| **Blocks UI** | 룰, 데이터, 모델, 학습, 평가, 배포 블록 조합 GUI |
| **Recipe Hub** | 프리셋/매크로/도메인팩 저장소 |
| **AgentBench** | 대형 LLM 및 baseline 대비 벤치마크 모듈 |
| **IMF Engine** | Instructed Model Forge. 데이터 생성·학습·adapter 생성 엔진 |
| **NoFate Guard** | verifier, safety rule, fallback, audit 모듈 |
| **Rebel Runtime** | small agent local runtime / export runtime |

---

## 4. 핵심 사용자

MIB Studio의 1차 고객은 ML 엔지니어가 아니라, **업무 룰은 알지만 모델 학습·평가·배포는 어려운 사용자**다.

| 사용자 | 필요 |
|---|---|
| 스타트업 개발자 | GPT API 비용 절감, small specialist agent 내재화 |
| 사내 AI 담당자 | 업무별 local/private agent 제작 |
| SaaS 팀 | 고객지원, 문서분류, 추출, 라우팅 자동화 |
| 도메인 전문가 | 금융, 제조, 법무, 세무, 고객지원 룰을 agent화 |
| SI/컨설턴트 | 고객사별 small agent 빠른 제작 |
| 교육기관/부트캠프 | local LLM/agent 실습 환경 |

---

## 5. 핵심 사용 시나리오

> **v0 범위:** 아래 중 **5.1 Router만 v0**에 포함된다. 5.2 Extractor / 5.3 Rule Selector / 5.4 Review Router / 5.5 Report Draft는 **v0.2+로 연기**된다([MVP_SCOPE §21](./MVP_SCOPE.md)).

### 5.1 Router Agent Maker

입력 문장을 보고 어떤 agent, workflow, 부서, 룰팩으로 보낼지 분류한다.

예시:

```text
고객문의 → 환불 / 기술지원 / 영업 / 사람검토
제조로그 → 설비알람 / 품질 / 정비 / 안전
금융요청 → 계산 / 설명 / 투자추천위험 / 사람검토
```

### 5.2 JSON Extractor Agent Maker

비정형 텍스트, 로그, 이메일, PDF에서 정해진 JSON 스키마로 필드를 추출한다.

예시:

```text
이메일 → 고객명, 요청유형, 긴급도
설비로그 → 알람코드, 시간, 장비명, 증상
포트폴리오 문장 → 종목, 배당금, 계좌유형
```

### 5.3 Rule Selector Agent Maker

상황 입력과 룰 목록을 보고 적용해야 할 룰 ID를 선택한다.

예시 출력:

```json
{
  "selected_rules": ["safe_line_warning.v1", "us_dividend_withholding.v1"],
  "excluded_rules": [
    {
      "rule_id": "pension_withdrawal_tax.v1",
      "reason": "pension account not detected"
    }
  ],
  "requires_human_review": false,
  "confidence": 0.91
}
```

### 5.4 Human Review Router

자동 처리 가능 여부와 사람 검토 필요 여부를 분류한다.

### 5.5 Report Draft Agent

계산 결과, 검색 결과, rule result만 사용해 고객용/관리자용 리포트 초안을 생성한다.  
새로운 숫자를 만들면 안 되며, source field를 반드시 참조해야 한다.

---

## 20. 수익모델

SaaS 하나로 가지 않는다.  
Open-source + Pro Desktop + Team Self-host + Enterprise On-prem + Domain Pack + Managed Compute 조합이 적합하다.

### 20.1 Community Edition

무료 / 오픈소스.

```text
로컬 단일 사용자 GUI
2~12B 모델 학습(NVIDIA=LoRA/QLoRA, Apple Silicon=MLX LoRA)
BYO GPU / BYO API key
기본 dataset import/export
기본 synthetic data 생성
기본 eval
기본 JSON schema 검증
기본 agent export: Docker / local API
기본 모델 지원
```

> **데이터 egress 주의:** "기본 synthetic data 생성"은 **BYO API key(외부 Teacher 호출)** 가 필요하며, 기본값은 schema+익명 예시만 전송한다([SECURITY_SPEC §19](./SECURITY_SPEC.md)). 그 외 학습·eval·export·JSON 검증은 로컬 실행이다.

### 20.2 Pro Desktop

개인/파워유저 유료.

```text
고급 Rule Wizard
Hard Negative Generator
Teacher model 기반 자동 예시 생성
Agent type template library
자동 hyperparameter recommendation
학습 실패 진단
eval dashboard 고급화
baseline vs fine-tuned 비교
cost/latency estimator
export to Dify/LangGraph/CrewAI/MCP
local model registry
checkpoint 비교
```

### 20.3 Team Self-host

팀 단위 유료.

```text
multi-user workspace
RBAC
project sharing
dataset review workflow
human labeling queue
Git sync
private model registry
shared GPU worker queue
team eval history
audit log
approval flow
team template library
API keys/project permissions
```

### 20.4 Enterprise On-prem / Air-gapped (v1+ 로드맵 · v0 비포함)

> **주의:** 아래 항목은 **목표 로드맵**이며 v0에 구현되지 않는다. air-gap/암호화/컴플라이언스 통제는 별도 'Enterprise Roadmap' 문서에서 실제 통제와 함께 정의하기 전까지 영업·RFP에 기능으로 약속하지 않는다([SECURITY_SPEC §19.8](./SECURITY_SPEC.md)).

기업용(목표):

```text
SSO/SAML/OIDC
LDAP/AD 연동
air-gapped installer
private VPC/on-prem deployment
model/data encryption
compliance audit logs
custom SLA
dedicated support
private connector 개발
custom model allowlist
GPU cluster integration
Kubernetes deployment
offline license
security review package
```

### 20.5 Paid Domain Packs

```text
Customer Support Router Pack
Finance Rule Selector Pack
AI Cost Router Pack
Legal Document Extractor Pack
Manufacturing RCA Agent Pack
Government RFP Review Pack
```

### 20.6 Managed Compute / Credits

```text
GPU training job
synthetic data generation credit
eval run credit
hosted inference endpoint
adapter hosting
batch benchmark run
```

---

## 25. 초기 데모 시나리오

### Demo A. 고객지원 라우터

```text
고객 문의 20개 + 카테고리 룰
→ synthetic 1,000개 생성
→ 4B router 학습
→ GPT-4o-mini 대비 정확도/비용 비교
```

### Demo B. 제조 알람 RCA 라우터

```text
설비 알람 + 작업자 메모
→ 원인 카테고리 분류
→ 점검 우선순위 라우팅
```

### Demo C. GetBeta 금융 룰 선택 Agent

```text
투자자 요청
→ 세후 계산 / safe line / 투자추천 위험 / 사람검토 분류
```

---

## 26. 스타트업 합류용 포지션

MIB Studio 자체는 독립 제품이 될 수도 있지만, 스타트업 팀에 합류할 때는 다음 포지션으로 제안할 수 있다.

```text
AI Agent System Architect
Small Agent Platform Lead
Rule-to-Agent Workflow Architect
LLM Cost/Latency Optimization Lead
```

팀에 제공할 가치:

```text
대형 LLM을 무작정 붙이지 않고
도메인 룰을 정리해서 small agent로 만들고
2~12B 모델을 로컬/온프레미스에서 돌리고
대형 LLM 대비 정확도, 비용, 속도를 벤치마킹하고
실패 케이스는 fallback과 verifier로 막는다.
```

적합한 팀:

1. Factory OS / 제조 AX
2. Robot 운영 리스크 / 로봇 검증
3. V2X / 자율주행 안전 플랫폼
4. SDV 서비스 플랫폼
5. AI 빌딩 운영
