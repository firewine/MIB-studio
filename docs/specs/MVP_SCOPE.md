# MVP 범위 (MVP_SCOPE) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [PRODUCT_SPEC](./PRODUCT_SPEC.md) · [PRESET_SPEC](./PRESET_SPEC.md) · [EVAL_SPEC](./EVAL_SPEC.md)

---

## 21. MVP 개발 범위

처음부터 모든 기능을 만들지 않는다. **v0는 단일 프리셋(Router)에 집중**한다.

> **v0 포지셔닝 확정:** 타겟 사용자는 "비전문가"가 아니라 **GPU/Python 환경을 다룰 수 있는 tech-savvy 업무 사용자**다. small agent는 "대형 LLM 완전 대체"가 아니라 **"반복 업무의 70% 저비용 처리 + 어려운 케이스는 fallback"** 으로 포지셔닝한다([AGENT_CONTRACT_SPEC §18](./AGENT_CONTRACT_SPEC.md) fallback). 성공 지표는 "정확도 GPT 추월"이 아니라 **"비용/지연 절감 대비 허용 가능한 정확도 손실"** 이다.

### MVP 포함 (v0)

```text
1. 프리셋: Router 1종만
2. 룰/예시 데이터 입력 (+ Hardware Doctor 게이트)
3. synthetic 데이터 생성 (BYO API Key, OpenAI 호환 1종)
4. 학습: base model 2종(`google/gemma-2b-it`, `microsoft/Phi-3.5-mini-instruct`), NVIDIA=LLaMA-Factory QLoRA, Apple Silicon=MLX 4-bit LoRA(parity-gated)
5. 벤치마크: 필수 4타깃(Fine-tuned vs Prompt-only vs Cloud Teacher vs Rule-only), Local-large는 선택(EVAL_SPEC §17.1~§17.2 방법론 준수)
6. agent package export: Docker API + OpenAI-compatible endpoint
7. Playground (입력→JSON→verifier 결과)
```

### v0.2+ 로 연기

```text
- 프리셋 확장: Extractor, Rule Selector, Review Router, Report Draft
- QLoRA 7~8B / local teacher
- export 확장: MCP / Dify / LangGraph / CrewAI / Ollama / vLLM
- Domain Pack / Recipe Hub / 멀티유저·RBAC / Managed Compute
```

### MVP 제외 (유지)

```text
멀티유저 협업
클라우드 GPU 마켓
프리셋 마켓플레이스
엔터프라이즈 권한관리
복잡한 workflow canvas
고급 RLHF/RL training
완전 자동 agent orchestration
```
