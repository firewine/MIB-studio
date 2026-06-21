# 평가 / 벤치마크 명세 (EVAL_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [PRESET_SPEC](./PRESET_SPEC.md) · [AGENT_CONTRACT_SPEC](./AGENT_CONTRACT_SPEC.md) · [COMPETITIVE_ANALYSIS](./COMPETITIVE_ANALYSIS.md)

---

## 16. 평가 지표

Agent별로 지표를 다르게 둔다.

> v0 구현 범위는 Router뿐이다. 아래 표의 Router 외 Agent 지표는 v0.2+ 프리셋 확장 시 재사용할 reference이며, v0 API/UI/worker 구현 대상이 아니다.

| Agent | 핵심 지표 |
|---|---|
| Router | route accuracy, task_type accuracy, unsafe routing rate |
| Extractor | field F1, JSON valid rate, missing field rate |
| Rule Selector | rule precision/recall, invalid rule ID rate |
| Tool Planner | tool sequence accuracy, forbidden tool usage |
| Report Draft | source faithfulness, no-new-number rate |
| Review Router | human-review precision/recall |
| 전체 하네스 | cost/task, latency, verifier pass rate, fallback rate |

공통 필수 지표:

```text
JSON valid rate
Schema adherence
No-hallucinated-number rate
Tool-call accuracy
Rule selection precision
Verifier pass rate
Latency
Cost per task
```

> **지표 산출 원칙(오염 방지):** 모든 정답 기반 지표는 **학습 데이터 생성 이전에 고정(frozen)된 홀드아웃 gold eval set**에 대해 계산한다. teacher가 생성·판정한 라벨을 정답으로 쓰지 않는다. LLM-judge가 불가피한 지표(source faithfulness 등)는 §17.1 절차를 따른다.

### 16.1 Router 지표 정의 (v0 LOCK)

```text
route accuracy = exact-match(route) 비율. per-route + macro 평균 보고.
task_type accuracy = route 정답 예시에 한해 task_type exact-match(conditional).
  v0 task_type enum: [generate_report, provide_advice, escalate, block].
unsafe routing:
  - Unsafe Recall  = unsafe 입력을 unsafe route로 보낸 비율 (목표 ≥95%).
  - Safe Precision = unsafe route 판정 중 실제 unsafe 비율 (목표 ≥98%).
  - unsafe 라벨은 보안/도메인 라벨러가 부여(§17.2 gold set).
output field accuracy = requires_calculation / requires_human_review 각각 binary accuracy + F1.
JSON valid rate = router_output.schema 통과율([PRESET_SPEC §15.4](./PRESET_SPEC.md)).
```

---

## 17. Benchmark UX

MIB Studio의 핵심 킬러 기능은 벤치마크 화면이다.

비교 대상:

```text
1. Prompt-only base model
2. Fine-tuned small model
3. Teacher model
4. Rule-only baseline
5. Optional Local-large when available
```

예시 리포트(아래 수치는 **가설·도식 예시**이며, §17.1 절차로 실측·검증되기 전에는 마케팅·대외 자료에 사용 금지):

```text
Task: Router Agent

Prompt-only selected base (`google/gemma-2b-it` or `microsoft/Phi-3.5-mini-instruct`)
accuracy: 72% (±?)
latency: 430ms

Fine-tuned selected base + LoRA adapter
accuracy: 91% (±?)
latency: 390ms

GPT-4o-mini teacher
accuracy: 94% (±?)
latency: 2.8s

Optional local-large target (`SKIPPED_OPTIONAL` when unavailable)
accuracy: 89% (±?)
latency: 7.1s

Conclusion (검증 전 가설):
Fine-tuned selected base ≈ teacher 품질의 96.8%,
7.2x 빠름,
약 92% 저렴 (fallback 비용 미포함 시).
```

제품 메시지:

```text
대형 LLM보다 똑똑하다가 아니라,
특정 반복 업무에서는 대형 LLM 호출을 small specialist agent로 대체할 수 있다.
```

### 17.1 벤치마크 방법론 (필수 · 신뢰성 게이트)

AgentBench가 제품의 간판이 되려면 아래를 코드와 리포트에 강제한다.

```text
1. 데이터 분리(오염 방지)
   - eval set은 teacher synthetic 생성 '이전'에 고정(frozen, SHA256 기록).
   - train/eval 의미 중복 0% 검증 테스트(test_eval_train_no_overlap) 통과 필수.
   - 최종 주장용 test set은 개발 중 한 번도 보지 않은 별도 hold-out.

2. 통계적 표기
   - 단일 점추정 금지. ≥3 seed 다회 실행, 평균±표준편차 + 95% CI 표기.
   - 예: accuracy 91.2% ± 1.8% (n=500, 5 seeds), 95% CI [88.9, 93.5].

3. LLM-as-judge 검증
   - judge 사용 지표는 human-gold와의 judge agreement Cohen's κ를 공개한다.
   - judge agreement κ ≥ 0.70이면 judge metric을 release claim에 사용할 수 있고, 미만이면 judge metric은 제외하고 rule 기반 결정적 metric으로 대체한다.
   - judge는 temperature 0 + 프롬프트 버전 해시 고정.

4. latency/cost 공정성(apples-to-apples)
   - 동일 입력셋·동일 max_tokens·동일 측정 하드웨어 명시.
   - latency는 p50/p95/p99, warm-start(burn-in N회 후).
   - cost는 fallback 호출 비용 포함 'effective cost/task'로 보고.
   - cost 가정(단가·기준일) 명시 + 민감도(단가 2배 시 우위 변화).

5. 재현성
   - eval set/checkpoint SHA256, 학습/추론 seed 고정.
   - 리포트는 eval runner가 자동 생성(수기 입력 금지), 버전·해시 포함.
```

> **백엔드 parity:** NVIDIA(CUDA) 경로와 Apple Silicon(MLX) 경로의 eval 지표는 §17.3 게이트를 통과한 뒤에만 동일 리포트에 함께 표기한다([ARCHITECTURE §13.3](./ARCHITECTURE.md)).

### 17.2 v0 벤치마크 구성 (LOCK)

비교 타깃(동일 frozen eval set · 동일 max_tokens=256 · warm-start):

```text
Required:
1. Prompt-only base = selected benchmark base model(default `google/gemma-2b-it`, no adapter, `prompts/router.prompt_only.v1.txt`)
2. Fine-tuned small = selected benchmark `model_run_id`의 LoRA adapter(ARCHITECTURE §13.3.2)
3. Cloud Teacher    = gpt-4o-mini (temperature 0, system prompt 버전 고정)  ※ BYO key
4. Rule-only baseline = if-else 8~10 룰(routing_rules.yaml, 제품팀 작성)

Optional:
5. Local large = 24B급 Q4 vLLM. v0 report에는 hardware available일 때만 포함하고, 없으면 `target_status=SKIPPED_OPTIONAL`로 기록한다.
```

Base-model cardinality:

```text
- 한 Benchmark는 정확히 하나의 selected base model family를 비교한다.
- v0 default acceptance benchmark는 `google/gemma-2b-it` 기반 model_run을 사용한다.
- `microsoft/Phi-3.5-mini-instruct`는 동일 절차로 별도 Benchmark를 생성해 비교한다. 다른 base model을 같은 Benchmark 안에 두 번째 `fine_tuned` target으로 넣지 않는다.
- CUDA/MLX parity는 같은 base model family와 같은 dataset/eval_set을 가진 `fine_tuned` target_key 두 개(`backend='cuda'`, `backend='mlx'`)로 표현한다.
```

Prompt/rule baseline artifacts:

```text
- Prompt-only는 `prompts/router.prompt_only.v1.txt`의 exact SHA256을 `BenchmarkTargetConfig.prompt_template_sha256`에 기록한다.
- Rule-only는 `rules/router.routing_rules.v1.yaml`을 사용하고, 파일은 `schemas/routing_rules.schema.json`에 검증되어야 한다.
- Rule-only evaluator는 ascending priority first-match, no-match=`default_route_id`, side-effect/network 호출 금지다.
```

Gold eval set 구성:

```text
- EvalSet.purpose='teacher_guard': n=20~50, teacher synthetic 이전에 고정되는 pre-teacher holdout. Teacher 생성 품질 감시용이며 release/benchmark claim에는 사용 금지.
- EvalSet.purpose='benchmark_gold': n=200~300, 사용자 프로젝트 route taxonomy 기준 production benchmark set.
- EvalSet.purpose='finance_reference': n=200~300, finance 레퍼런스 6-route(PRESET_SPEC §6.3) 기준 v0 release/regression acceptance profile.
- Day-0 smoke fixture: `examples/fixtures/gold_eval.finance.v1.jsonl`은 converter/schema/hash 테스트용 최소 20행 fixture이며, production EvalSet이나 release claim 근거로 사용할 수 없다.
- 라벨: 도메인+보안 라벨러 3인 다수결, EvalSet labeler inter-rater Cohen's κ ≥0.70 기록
- 생성 시점: teacher synthetic '이전'에 고정. SHA256→EvalSet.sha256, frozen_at 기록.
- 모든 EvalSet은 dataset route_snapshot_sha256을 기록한다. `benchmark_gold`는 해당 사용자 프로젝트 route snapshot과 같은 route ids/order를 사용해야 하고, `finance_reference`는 고정 finance 6-route snapshot만 사용한다.
- hold-out: 최종 주장용 test set은 개발 중 비공개 별도 분할.
- 메타(리포트 포함): frozen_date, labeler_ids, kappa, encoder_version.
```

> **저장(감사):** 벤치마크는 `Benchmark`(comparison) + `EvalRun`(target_key×seed) 테이블로 영속화하며, 각 EvalRun은 `target_key`, `target_type`, `backend`, `target_status`, `target_config_json`(model/base_url/temperature/judge_prompt_hash/labeler_ids/gold_sha256)과 `credential_id`(teacher 호출 추적)를 기록한다([ARCHITECTURE §24](./ARCHITECTURE.md)). Local-large를 실행할 수 없으면 seed=0 `SKIPPED_OPTIONAL` 행 1개를 만들고 `EvalRun.metrics_json.skip_reason`에 사유를 남긴다.

### 17.3 CUDA/MLX Parity 게이트 (M4)

```text
대상: 동일 gold eval set, 각 백엔드 ≥3 seed(권장 5: 42,123,456,789,999), 그 외 파라미터 동결.
임계(per-metric):
  route accuracy |Δ| ≤ 2.0pp, task_type |Δ| ≤ 2.0pp, unsafe routing |Δ| ≤ 1.5pp(보안 tighter),
  latency p50 상대차 ≤ 20%, cost 상대차 ≤ 10%.
통계: Welch t-test. 어느 지표든 p<0.05 이면서 |Δ| 임계 초과 시 FAIL.
판정: 모든 지표 PASS → parity PASS(공동 리포트).
      FAIL → 원인분석; v0는 CUDA-only 출시 + MLX v0.2 fast-follow(Dev Plan IR11).
리포트: benchmark report JSON에 parity_status(PASS|FAIL)·per-metric Δ·p-value·결정성 caveat 포함.
```

> 결정성 caveat 근거: MLX(Metal/MPS) 비결정성으로 seed 고정에도 ±0.5~1pp 변동 가능([ARCHITECTURE §13.3.3](./ARCHITECTURE.md)).

### 17.4 train/eval Overlap 검사 (test_eval_train_no_overlap)

```text
Layer 1 (정확 중복): hash(input.text) 교집합 = 0.
Layer 2 (의미 중복): sentence-transformers/all-MiniLM-L6-v2(frozen)로 임베딩,
  각 eval 예시의 train 대비 max cosine ≥ 0.85 이면 flag. flagged = 0 이어야 PASS.
CI: 위 검사를 pytest(test_eval_train_no_overlap)로 자동화, 리포트에 encoder_version·threshold 기록.
```

### 17.5 Benchmark Report Schema (v0 LOCK)

`EvalRun.metrics_json` 최소 구조:

```json
{
  "route_accuracy": 0.912,
  "route_accuracy_macro": 0.901,
  "task_type_accuracy": 0.884,
  "unsafe_recall": 0.962,
  "safe_precision": 0.981,
  "requires_calculation_accuracy": 0.901,
  "requires_calculation_f1": 0.887,
  "requires_human_review_accuracy": 0.944,
  "requires_human_review_f1": 0.931,
  "json_valid_rate": 0.996,
  "schema_adherence": 0.992,
  "verifier_pass_rate": 0.973,
  "fallback_rate": 0.081,
  "latency_ms": {
    "p50": 390,
    "p95": 880,
    "p99": 1210
  },
  "cost_per_task_usd": 0.00012,
  "effective_cost_per_task_usd": 0.00021,
  "invalid_outputs": {
    "invalid_json": 1,
    "schema_failed": 2,
    "route_not_allowed": 0,
    "missing_required_field": 1
  }
}
```

`benchmark_report.json` 구조 예시(fine-tuned parity slice excerpt):

> Full report must include exactly one `prompt_only`, one `teacher`, one `rule_based`, one or two `fine_tuned`, and one optional `local_large` target object. The large metric objects below show the `fine_tuned` parity slice; other completed required targets use the same `metric_object` shape.

```json
{
  "schema_version": "benchmark_report.v1",
  "benchmark_id": "01JZ...",
  "project_id": "01JZ...",
  "eval_set": {
    "id": "01JZ...",
    "purpose": "benchmark_gold",
    "sha256": "64hex",
    "route_snapshot_sha256": "64hex",
    "sample_count": 240,
    "frozen_at": "2026-06-20T00:00:00Z",
    "kappa": 0.78
  },
  "overlap_check": {
    "exact_duplicate_count": 0,
    "semantic_flag_count": 0,
    "encoder_version": "sentence-transformers/all-MiniLM-L6-v2@frozen",
    "threshold": 0.85,
    "passed": true
  },
  "targets": [
    {
      "target_key": "ft_cuda_primary",
      "target_type": "fine_tuned",
      "target_status": "COMPLETED",
      "model_run_id": "01JZ...",
      "model": "google/gemma-2b-it",
      "backend": "cuda",
      "seeds": [42, 123, 456],
      "mean_metrics": {
        "route_accuracy": 0.912,
        "route_accuracy_macro": 0.901,
        "task_type_accuracy": 0.884,
        "unsafe_recall": 0.962,
        "safe_precision": 0.981,
        "requires_calculation_accuracy": 0.901,
        "requires_calculation_f1": 0.887,
        "requires_human_review_accuracy": 0.944,
        "requires_human_review_f1": 0.931,
        "json_valid_rate": 0.996,
        "schema_adherence": 0.992,
        "verifier_pass_rate": 0.973,
        "fallback_rate": 0.081,
        "latency_p50_ms": 390,
        "latency_p95_ms": 880,
        "latency_p99_ms": 1210,
        "cost_per_task_usd": 0.00012,
        "effective_cost_per_task_usd": 0.00021
      },
      "std_metrics": {
        "route_accuracy": 0.012,
        "route_accuracy_macro": 0.014,
        "task_type_accuracy": 0.017,
        "unsafe_recall": 0.008,
        "safe_precision": 0.006,
        "requires_calculation_accuracy": 0.013,
        "requires_calculation_f1": 0.015,
        "requires_human_review_accuracy": 0.010,
        "requires_human_review_f1": 0.012,
        "json_valid_rate": 0.002,
        "schema_adherence": 0.003,
        "verifier_pass_rate": 0.005,
        "fallback_rate": 0.010,
        "latency_p50_ms": 12,
        "latency_p95_ms": 44,
        "latency_p99_ms": 60,
        "cost_per_task_usd": 0.00001,
        "effective_cost_per_task_usd": 0.00002
      },
      "ci95": {
        "route_accuracy": 0.018,
        "route_accuracy_macro": 0.020,
        "task_type_accuracy": 0.022,
        "unsafe_recall": 0.012,
        "safe_precision": 0.010,
        "requires_calculation_accuracy": 0.018,
        "requires_calculation_f1": 0.020,
        "requires_human_review_accuracy": 0.015,
        "requires_human_review_f1": 0.017,
        "json_valid_rate": 0.004,
        "schema_adherence": 0.004,
        "verifier_pass_rate": 0.007,
        "fallback_rate": 0.015,
        "latency_p50_ms": 20,
        "latency_p95_ms": 70,
        "latency_p99_ms": 92,
        "cost_per_task_usd": 0.00002,
        "effective_cost_per_task_usd": 0.00003
      }
    },
    {
      "target_key": "ft_mlx_primary",
      "target_type": "fine_tuned",
      "target_status": "COMPLETED",
      "model_run_id": "01JZ...",
      "model": "google/gemma-2b-it",
      "backend": "mlx",
      "seeds": [42, 123, 456],
      "mean_metrics": {
        "route_accuracy": 0.908,
        "route_accuracy_macro": 0.897,
        "task_type_accuracy": 0.881,
        "unsafe_recall": 0.958,
        "safe_precision": 0.979,
        "requires_calculation_accuracy": 0.899,
        "requires_calculation_f1": 0.884,
        "requires_human_review_accuracy": 0.941,
        "requires_human_review_f1": 0.928,
        "json_valid_rate": 0.995,
        "schema_adherence": 0.991,
        "verifier_pass_rate": 0.970,
        "fallback_rate": 0.084,
        "latency_p50_ms": 430,
        "latency_p95_ms": 930,
        "latency_p99_ms": 1300,
        "cost_per_task_usd": 0.00013,
        "effective_cost_per_task_usd": 0.00022
      },
      "std_metrics": {
        "route_accuracy": 0.013,
        "route_accuracy_macro": 0.015,
        "task_type_accuracy": 0.017,
        "unsafe_recall": 0.009,
        "safe_precision": 0.006,
        "requires_calculation_accuracy": 0.014,
        "requires_calculation_f1": 0.016,
        "requires_human_review_accuracy": 0.011,
        "requires_human_review_f1": 0.013,
        "json_valid_rate": 0.002,
        "schema_adherence": 0.003,
        "verifier_pass_rate": 0.006,
        "fallback_rate": 0.011,
        "latency_p50_ms": 14,
        "latency_p95_ms": 50,
        "latency_p99_ms": 72,
        "cost_per_task_usd": 0.00001,
        "effective_cost_per_task_usd": 0.00002
      },
      "ci95": {
        "route_accuracy": 0.019,
        "route_accuracy_macro": 0.021,
        "task_type_accuracy": 0.023,
        "unsafe_recall": 0.013,
        "safe_precision": 0.010,
        "requires_calculation_accuracy": 0.019,
        "requires_calculation_f1": 0.021,
        "requires_human_review_accuracy": 0.016,
        "requires_human_review_f1": 0.018,
        "json_valid_rate": 0.004,
        "schema_adherence": 0.004,
        "verifier_pass_rate": 0.008,
        "fallback_rate": 0.016,
        "latency_p50_ms": 24,
        "latency_p95_ms": 78,
        "latency_p99_ms": 105,
        "cost_per_task_usd": 0.00002,
        "effective_cost_per_task_usd": 0.00003
      }
    },
    {
      "target_key": "local_large_optional",
      "target_type": "local_large",
      "target_status": "SKIPPED_OPTIONAL",
      "model_run_id": null,
      "model": null,
      "backend": "local_large",
      "seeds": [0],
      "skip_reason": "no compatible 24B local runtime"
    }
  ],
  "parity": {
    "status": "PASS",
    "metrics": [
      {"name": "route_accuracy", "delta_pp": 1.2, "p_value": 0.21}
    ]
  },
  "cost_assumptions": {
    "currency": "USD",
    "pricing_date": "2026-06-20",
    "fallback_provider": "openai-compatible"
  },
  "artifact_hashes": {
    "report_sha256": "64hex",
    "eval_set_sha256": "64hex"
  }
}
```

Report hash canonicalization:

```text
- `schemas/benchmark_report.schema.json` is the committed JSON Schema artifact.
- `benchmark_report.json` must validate against that schema before writing Benchmark.report_path.
- To compute `artifact_hashes.report_sha256`, remove only `artifact_hashes.report_sha256` from the JSON object.
- Serialize the remaining object with:
  json.dumps(report_without_report_sha, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
- SHA256 the UTF-8 bytes.
- Store the resulting 64-hex value in both `artifact_hashes.report_sha256` and `Benchmark.report_sha256`.
- `GET /benchmarks/{id}/report` must recompute the hash and return `hash_status=VALID|MISMATCH|MISSING`.
- Manual edits to `benchmark_report.json` after hashing are invalid; UI must show hash mismatch.
```

Invalid output handling:

```text
- invalid JSON counts as route/task incorrect and verifier_failed.
- schema_failed counts as verifier_failed.
- route_not_allowed counts as route incorrect even if text label is close.
- missing confidence counts as schema_failed.
- fallback-triggered examples are included in effective cost/task and fallback_rate.
```
