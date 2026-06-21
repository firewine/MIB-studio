# 벤치마킹 / 경쟁 분석 (COMPETITIVE_ANALYSIS) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [PRODUCT_SPEC](./PRODUCT_SPEC.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [ARCHITECTURE](./ARCHITECTURE.md)

---

## 27. 벤치마킹 / 경쟁 프로젝트 분석

### 27.1 결론

MIB Studio와 유사한 프로젝트는 이미 많다. 그러나 대부분은 다음 중 하나에 집중한다.

```text
1. 모델 fine-tuning 자체를 쉽게 하는 도구
2. agent workflow를 시각적으로 조립하는 도구
3. LLM app의 eval/trace/observability 도구
4. business rule/decision table을 실행하는 도구
5. production prompt를 fine-tuned cheaper model로 치환하는 도구
```

MIB Studio가 들어갈 틈은 다음 조합이다.

> **Rule-first preset/macro UX + Hardware Doctor + 2~12B small agent training + large LLM benchmark + Agent Contract export**

즉 MIB는 “또 하나의 fine-tuning GUI”가 아니라 **룰·예시·정책을 small specialist agent로 바꾸고, 대형 LLM 대비 성능/비용/속도를 증명하는 Local-first GUI**로 포지션해야 한다.

---

### 27.2 벤치마킹 우선순위

| 우선순위 | 프로젝트/제품 | 벤치마킹 이유 | MIB 반영 포인트 |
|---:|---|---|---|
| 1 | **Kiln AI** | local-first AI workbench. evals, fine-tuning, synthetic data, agents, tools까지 묶음 | task/dataset/eval/fine-tune flow, synthetic data review UX |
| 2 | **LLaMA-Factory** | 100+ 모델 fine-tuning, CLI/Web UI, LoRA/QLoRA 지원 | MIB v0 NVIDIA/CUDA training backend wrapper 확정 |
| 3 | **Unsloth** | consumer GPU에서 빠른 LoRA/QLoRA, training observability | low-VRAM profile, training speed UX, GPU 사용량 표시 |
| 4 | **H2O LLM Studio** | no-code LLM fine-tuning GUI | 초보자용 fine-tuning UX, experiment 비교 |
| 5 | **AutoTrain** | no-code training, local/cloud 모두 가능 | local/cloud 선택 UX, 데이터 검증 |
| 6 | **OpenPipe / ART** | prompt/log 기반 fine-tuning, agent RL training harness | cost reduction messaging, agent learning harness |
| 7 | **promptfoo / DeepEval** | LLM eval, red teaming, CI/CD, LLM-as-judge | AgentBench metric/eval runner 설계 |
| 8 | **Langfuse / LangSmith** | trace, eval, prompt management, cost/latency observability | benchmark/trace/eval history UX |
| 9 | **Dify / AutoGen Studio / CrewAI Studio / LangGraph Studio** | agent workflow GUI | MIB export target, later macro canvas 참고 |
| 10 | **GoRules / DecisionRules / Drools DMN** | rule table, decision flow, rule engine | Rule-first UX, rule overlap/conflict, deterministic verifier |

---

### 27.3 가장 가까운 경쟁자: Kiln AI

Kiln은 MIB와 가장 가까운 벤치마킹 대상이다. Kiln은 free/local-first workbench로서 evals, prompt optimization, fine-tuning, RAG, agents, synthetic data, tools를 하나의 task/dataset 흐름으로 묶는다.

#### Kiln에서 배울 점

```text
1. Task-first project 생성 UX
2. synthetic data 생성 및 검수 흐름
3. fine-tuning dataset과 eval dataset 분리
4. 여러 cloud/local model provider 연결
5. eval-first iteration flow
6. free app + open-source library 포지션
```

#### MIB의 차별화 포인트

```text
Kiln: AI system development workbench
MIB: Rule-to-Small-Agent Studio

MIB는 task/eval/fine-tune 일반 워크벤치가 아니라,
룰/프리셋/매크로 기반으로 2~12B specialist agent를 만들고,
대형 LLM 대비 benchmark와 Agent Contract export를 전면에 둔다.
```

#### 구현 반영

- `Task` 대신 `Agent Preset` 중심 프로젝트 생성.
- Synthetic data 생성 전에 `Rule Wizard`와 `Hard Negative Generator`를 먼저 제공.
- Fine-tuning 결과보다 `benchmark conclusion`을 전면 표시.
- Agent Package에 benchmark report, schema, verifier, fallback policy를 함께 포함.

참고:
- GitHub: https://github.com/kiln-ai/kiln
- Website: https://kiln.tech/

---

### 27.4 Training Engine 계열

#### LLaMA-Factory

LLaMA-Factory는 100개 이상 LLM/VLM의 efficient fine-tuning을 지원하고 zero-code CLI/Web UI를 제공한다. **MIB v0는 NVIDIA(CUDA) 학습 백엔드로 LLaMA-Factory를 확정**했다(버전 핀: [ARCHITECTURE §31.2](./ARCHITECTURE.md); Apple Silicon은 MLX 분기).

MIB 반영:

```text
- v0 training backend = LLaMA-Factory (확정, NVIDIA/CUDA)
- model zoo / dataset format / LoRA config 구조 참고
- 고급 사용자를 위해 generated training config export 제공
```

참고:
- GitHub: https://github.com/hiyouga/LLaMA-Factory
- Paper: https://arxiv.org/abs/2403.13372

#### Unsloth

Unsloth는 low-VRAM 환경에서 빠른 fine-tuning과 training observability가 강점이다. MIB의 Hardware Doctor와 Training Profile 추천에 참고할 만하다.

MIB 반영:

```text
- 8GB/16GB/24GB VRAM별 추천 프로파일
- 학습 중 loss/GPU usage/live log 표시
- Quick/Balanced/Production preset별 LoRA/QLoRA 설정 자동 추천
```

참고:
- GitHub: https://github.com/unslothai/unsloth
- Docs: https://unsloth.ai/docs/

#### H2O LLM Studio

H2O LLM Studio는 no-code GUI 기반 LLM fine-tuning UX를 제공한다. MIB는 fine-tuning GUI 자체를 참고하되, 모델 학습 이후의 Agent Contract, verifier, benchmark, export를 더 강하게 잡아야 한다.

MIB 반영:

```text
- 학습 job progress UI
- experiment 비교 UI
- hyperparameter 화면의 초보자/고급자 분리
```

참고:
- GitHub: https://github.com/h2oai/h2o-llmstudio

#### Hugging Face AutoTrain

AutoTrain은 no-code training을 local/cloud 모두에서 지원한다. MIB도 local-first를 기본으로 하되, managed GPU를 후속 수익화 옵션으로 둘 수 있다.

MIB 반영:

```text
- Local run / Cloud run 선택 UX
- dataset validation
- Hugging Face model import/export
```

참고:
- GitHub: https://github.com/huggingface/autotrain-advanced
- Paper: https://arxiv.org/abs/2410.15735

---

### 27.5 Agent Workflow Builder 계열

Dify, AutoGen Studio, CrewAI Studio, LangGraph Studio, Langflow, Flowise는 agent workflow를 만들고 조립하는 도구다. MIB는 이들과 정면 경쟁하기보다 **그 workflow 안에 들어갈 small specialist agent를 만드는 도구**가 되어야 한다.

#### 벤치마킹 포인트

```text
Dify:
- production-ready LLM app/workflow/RAG/agent builder UX
- MIB export target으로 적합

AutoGen Studio:
- no-code multi-agent prototyping/debugging
- agent/workflow JSON spec 참고

CrewAI Studio:
- drag-and-drop agent/task/tool canvas
- v1 이후 macro canvas 참고

LangGraph Studio:
- stateful workflow debugging / agent visualization
- advanced workflow export target
```

#### MIB 전략

```text
v0: Wizard UI
v1: Preset/Macro Blocks
v2: Canvas editor

Export targets:
- Docker API
- OpenAI-compatible endpoint
- MCP server
- Dify tool
- LangGraph node
- CrewAI tool/agent
```

참고:
- Dify GitHub: https://github.com/langgenius/dify
- AutoGen GitHub: https://github.com/microsoft/autogen
- AutoGen Studio docs: https://microsoft.github.io/autogen/
- CrewAI Studio docs: https://docs.crewai.com/en/enterprise/features/crew-studio
- LangGraph: https://github.com/langchain-ai/langgraph

---

### 27.6 Eval / Benchmark / Observability 계열

MIB의 핵심 킬러 기능은 `AgentBench`다. Fine-tuned small agent가 대형 LLM 대비 얼마나 쓸 만한지 증명해야 한다.

#### promptfoo

promptfoo는 prompt/model 비교, red teaming, CI/CD 자동 평가를 지원한다.

MIB 반영:

```text
- side-by-side model 비교
- eval case table
- red-team/unsafe case 테스트
- CI-friendly eval config export
```

참고:
- GitHub: https://github.com/promptfoo/promptfoo

#### DeepEval

DeepEval은 LLM app용 Pytest-like evaluation framework다.

MIB 반영:

```text
- metric plugin 구조
- LLM-as-judge 옵션
- pytest/CI export
```

참고:
- GitHub: https://github.com/confident-ai/deepeval
- Website: https://deepeval.com/

#### Langfuse / LangSmith

Langfuse는 trace, eval, prompt management, monitoring, debugging을 제공하는 open-source LLM engineering platform이다.

MIB 반영:

```text
- eval run history
- cost/latency/trace dashboard
- failed case drill-down
- prompt/template versioning
```

참고:
- Langfuse GitHub: https://github.com/langfuse/langfuse
- Langfuse docs: https://langfuse.com/docs

---

### 27.7 Rule Engine / Decision Engine 계열

MIB의 Rule-first UX는 GoRules, DecisionRules, Drools/DMN 계열을 참고해야 한다. 다만 이들은 룰을 deterministic하게 실행하는 도구이고, MIB는 룰을 학습 데이터, hard negative, eval set, Agent Contract로 바꾸는 도구다.

#### GoRules

GoRules는 business teams가 AI copilot과 MCP integration을 통해 rules를 build/test/deploy할 수 있게 하는 AI business rules engine이다.

MIB 반영:

```text
- decision table / decision graph UI 참고
- rule test case 생성 UX 참고
- MCP integration 참고
```

참고:
- Website: https://gorules.io/
- ZEN Engine GitHub: https://github.com/gorules/zen

#### DecisionRules

DecisionRules는 AI assistant가 live decision flows/tables를 만들고 업데이트하고 실행할 수 있는 native MCP integration을 강조한다.

MIB 반영:

```text
- rule table import/export
- document-to-rule extraction
- AI-assisted rule authoring
```

참고:
- Website: https://www.decisionrules.io/en/

#### Drools / DMN

Drools DMN은 DMN 모델을 실행하는 오픈소스 Java 구현체이며, decision table과 conformance 개념을 참고할 수 있다.

MIB 반영:

```text
- 룰 overlap/conflict/missing condition 감지
- deterministic verifier 설계
- enterprise rule format 호환성 검토
```

참고:
- Apache KIE Drools DMN: https://kie.apache.org/components/drools/drools_dmn/

---

### 27.8 OpenPipe / ART 계열

OpenPipe는 production prompt/log를 fine-tuned cheaper model로 치환하는 메시지가 강하고, ART는 Agent Reinforcement Trainer로 agent가 경험에서 학습하도록 하는 RL framework를 지향한다.

MIB 반영:

```text
- 대형 LLM 비용 절감 메시지
- production trace 기반 dataset 생성
- agent training harness 구조
- v1 이후 agent RL/GRPO는 후속 연구 과제로 분리
```

참고:
- OpenPipe GitHub: https://github.com/openpipe/openpipe
- ART GitHub: https://github.com/openpipe/art
- ART website: https://openpipe.ai/open-source-rl

---

### 27.9 MIB 차별화 선언

MIB가 피해야 할 포지션:

```text
1. 또 하나의 fine-tuning GUI
2. 또 하나의 agent workflow builder
3. 또 하나의 rule engine
4. 또 하나의 eval dashboard
5. LoRA 빠르게 해주는 wrapper
```

MIB가 가져가야 할 포지션:

```text
Rule-to-Small-Agent Studio

사용자가 룰·예시·정책을 넣으면,
Hardware Doctor가 가능한 제작 경로를 추천하고,
Teacher AI가 synthetic/hard negative/eval set을 만들고,
2~12B 모델을 NVIDIA에서는 LoRA/QLoRA, Apple Silicon에서는 MLX LoRA로 fine-tune하고,
대형 LLM 대비 성능/비용/속도를 benchmark하고,
Agent Contract + verifier + fallback + export package를 생성한다.
```

핵심 차별점 5개:

```text
1. Rule-first preset/macro UX
2. Hardware Doctor + Capability Planner
3. 2~12B specialist agent 제작
4. 대형 LLM 대비 성능/비용/속도 benchmark
5. Agent Contract + verifier + export package
```

---

### 27.10 벤치마킹 기반 개발 Backlog 반영

| Backlog | 출처/벤치마크 | MVP 반영 여부 |
|---|---|---|
| Task/Preset project flow | Kiln | MVP 필수 |
| Synthetic data + eval split | Kiln, AutoTrain | MVP 필수 |
| Training backend wrapper | LLaMA-Factory, Unsloth | MVP 필수 |
| Hardware Doctor | Unsloth/Ollama류 local UX + MIB 차별점 | MVP 필수 |
| Large LLM vs small model benchmark | promptfoo, DeepEval, OpenPipe | MVP 필수 |
| Agent Contract export | MIB 차별점 | MVP 필수 |
| Rule Wizard / Decision table | GoRules, DecisionRules, Drools | v0.2 필수 |
| Dify/LangGraph/CrewAI export | Agent workflow builder 계열 | v0.3 이후 |
| Trace/eval history dashboard | Langfuse/LangSmith | v0.3 이후 |
| Marketplace / Recipe Hub | Dify/Kiln 생태계 참고 | v1 이후 |
| Agent RL / GRPO | OpenPipe ART | v1 이후 연구 |

---

### 27.11 조사 기준

- 조사일: 2026-06-20
- 기준: GitHub, 공식 문서, 프로젝트 홈페이지, 논문/개발자 커뮤니티 공개 자료
- 판단 원칙: 기능 단순 비교보다 **MIB의 제품 철학과 사용자 흐름에 직접 영향을 주는 UX/아키텍처/수익화 포인트**를 우선 반영한다.
