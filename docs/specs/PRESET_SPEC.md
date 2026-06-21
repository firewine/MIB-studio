# 프리셋 / 학습 데이터 명세 (PRESET_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [PRODUCT_SPEC](./PRODUCT_SPEC.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md)

---

## 6. 제품 UX: 프리셋/매크로 방식

초보자에게 모델 학습은 어렵다. 따라서 MIB Studio는 “모델 학습 도구”가 아니라 **프리셋/매크로 조합형 small agent 제작 앱**이어야 한다.

### 6.1 5단계 프리셋 구조

| 단계 | 선택 항목 |
|---|---|
| Agent Type Preset | Router, Extractor, Rule Selector, Tool Planner, Review Router, Report Draft |
| Data Preset | CSV, JSON, PDF, 로그, 매뉴얼, 룰 텍스트, 작업자 메모 |
| Training Preset | Quick, Balanced, Production |
| Eval Preset | accuracy, F1, JSON valid, rule precision/recall, unsafe rate, latency, cost |
| Deploy Preset | Local API, Docker(v0), Ollama/vLLM/MCP/Dify/LangGraph/CrewAI(v0.2+ reference) |

> v0 범위에서는 Agent Type Preset = **Router 1종**만 활성화한다([MVP_SCOPE §21](./MVP_SCOPE.md)).

### 6.2 대표 매크로

#### Macro 1. 고객문의 분류 Agent 만들기

```text
입력:
- 고객문의 예시
- 분류 카테고리
- 정책 룰

자동 수행:
- synthetic 문의 생성
- hard negative 생성
- Router Agent 학습
- 분류 정확도 평가
- API export
```

#### Macro 2. 문서 JSON 추출 Agent 만들기 (v0.2+ reference)

```text
입력:
- PDF/텍스트 문서
- 원하는 JSON schema
- 예시 10개

자동 수행:
- 필드 추출 예시 생성
- 누락/오인식 케이스 생성
- Extractor Agent 학습
- field F1 평가
- JSON validator 연결
```

#### Macro 3. 업무 룰 선택 Agent 만들기 (v0.2+ reference)

```text
입력:
- 업무 룰 목록
- 케이스 예시
- 적용/미적용 기준

자동 수행:
- 룰 적용 케이스 생성
- 경계 케이스 생성
- Rule Selector 학습
- precision/recall 평가
- rule registry 연결
```

#### Macro 4. GPT 비용 절감 Agent 만들기

```text
입력:
- 기존 GPT 요청 로그
- 성공/실패 기준
- 사용 가능한 로컬 모델

자동 수행:
- 요청 유형 분류
- small model로 대체 가능한 케이스 탐지
- Router Agent 학습
- GPT 대비 비용/속도 비교
- fallback policy 생성
```

### 6.3 Router v0 Route Taxonomy (LOCK)

v0 Router는 **사용자 정의 route** 방식이다(빌트인 도메인팩은 v0.2+).

```text
- route 개수: 프로젝트당 2~12개 (v0)
- route_id 규칙: ^[a-z0-9_]+$, 최대 64자, 프로젝트 내 유일
- 각 route: { route_id, description, is_unsafe(bool, 기본 false) }
- 권장 예약 route: "human_review"(에스컬레이션), "blocked"(차단/unsafe)
- 출력 계약: router_output.schema (§15.4)
```

> **벤치마크용 고정 셋:** v0 AgentBench gold eval set은 재현성을 위해 **고정 finance 6-route 레퍼런스 taxonomy**(finance_income, risk_summary, investment_advice_block, human_review, blocked_pii, blocked_unsupported)를 사용한다([EVAL_SPEC §17](./EVAL_SPEC.md)). 제품 기능(사용자 정의)과 별개의 평가용 고정 셋이다.

---

## 15. 학습 데이터 표준 포맷

### 15.0 학습 JSONL 포맷 / 라벨 마스킹 (v0 LOCK)

```text
- 파일: dataset.jsonl, 1줄 1예시. 물리 필드: { instruction: string, input: object, output: object }.
- on-disk JSONL의 input/output은 JSON object다. 문자열로 double-encode하지 않는다.
- trainer 변환 단계에서 assistant 메시지 content만 `json.dumps(output, ensure_ascii=False)`로 직렬화한다.
- v0는 single-turn. instruction=작업정의, input=사용자 입력, output=정답 JSON object.
- 학습 시 wrapper가 모델별 chat template로 변환(ARCHITECTURE §13.3.1, §13.3.4):
    instruction → system (Gemma는 system 미지원 → user turn에 prepend)
    input → user, output → assistant
- 라벨 마스킹: loss는 output 토큰에만(train_on_outputs_only). instruction/input은 마스킹.
- 길이: 토크나이즈 후 max_seq_length(1024) 초과분 경고/절단. Dataset Builder가 사전 검증.
- MLX 경로도 동일 JSONL 사용(변환기만 다름).
```

`task_type` enum(v0 Router):

```text
generate_report | provide_advice | escalate | block
```

### 15.1 Router 데이터

```json
{
  "instruction": "Classify the request into one of the allowed routes.",
  "input": {
    "text": "이 포트폴리오의 세후 월 인컴 리포트를 만들어줘.",
    "allowed_routes": ["finance_income", "risk_summary", "investment_advice_block", "human_review"]
  },
  "output": {
    "route": "finance_income",
    "task_type": "generate_report",
    "requires_calculation": true,
    "requires_human_review": false,
    "confidence": 0.92
  }
}
```

### 15.2 Extractor 데이터 (v0.2+ reference, v0 구현 금지)

```json
{
  "instruction": "Extract fields from the text according to the schema.",
  "input": {
    "text": "미국 ETF 월배당 1800만원 정도고, 일반계좌랑 ISA 섞여 있어요.",
    "schema": {
      "asset_type": "string",
      "income_type": "string",
      "estimated_annual_income_krw": "number",
      "account_types": "string[]"
    }
  },
  "output": {
    "asset_type": "US_ETF",
    "income_type": "monthly_distribution",
    "estimated_annual_income_krw": 18000000,
    "account_types": ["general", "ISA"],
    "confidence": 0.82
  }
}
```

### 15.3 Rule Selector 데이터 (v0.2+ reference, v0 구현 금지)

```json
{
  "instruction": "Select applicable rule IDs for the given case.",
  "input": {
    "tax_residency": "KR",
    "asset_type": "US_ETF",
    "annual_income_krw": 18000000,
    "account_type": "general",
    "available_rules": [
      "kr_financial_income_safe_line.v1",
      "us_dividend_withholding.v1",
      "pension_withdrawal_tax.v1"
    ]
  },
  "output": {
    "candidate_rules": [
      "kr_financial_income_safe_line.v1",
      "us_dividend_withholding.v1"
    ],
    "excluded_rules": [
      {
        "rule_id": "pension_withdrawal_tax.v1",
        "reason": "no pension account detected"
      }
    ],
    "requires_human_review": false
  }
}
```

---

## 15.4 Router 입력/출력 JSON Schema (v0 LOCK)

`router_input.schema` (draft-07):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["text", "allowed_routes"],
  "additionalProperties": false,
  "properties": {
    "text": { "type": "string", "minLength": 1, "maxLength": 8000 },
    "allowed_routes": {
      "type": "array", "minItems": 2, "maxItems": 12,
      "items": { "type": "string", "pattern": "^[a-z0-9_]+$", "maxLength": 64 }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

`router_output.schema` (draft-07):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["route", "task_type", "requires_calculation", "requires_human_review", "confidence"],
  "additionalProperties": false,
  "properties": {
    "route": { "type": "string", "pattern": "^[a-z0-9_]+$", "maxLength": 64 },
    "task_type": {
      "type": "string",
      "enum": ["generate_report", "provide_advice", "escalate", "block"]
    },
    "requires_calculation": { "type": "boolean" },
    "requires_human_review": { "type": "boolean" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

> verifier 규칙: 출력은 위 스키마 통과 + `route ∈ allowed_routes` + `confidence ∈ [0,1]`. 위반 시 fallback([AGENT_CONTRACT_SPEC §18](./AGENT_CONTRACT_SPEC.md)).
