# Hardware Doctor / 사양 / Teacher 전략 (HARDWARE_DOCTOR_SPEC) — MIB Studio

> 상위: [MIB Studio 개발 계획서 v0.3](../foundation/MIB_Studio_Dev_Plan_v0.3.md)
> 상태: v0.3 · 개발 계획서에서 분리·이관
> 비고: 추적성을 위해 원 계획서의 섹션 번호(§N)를 유지한다.
> 관련: [ARCHITECTURE](./ARCHITECTURE.md) · [EVAL_SPEC](./EVAL_SPEC.md) · [SECURITY_SPEC](./SECURITY_SPEC.md)

---

## 10. Teacher AI 전략

Teacher AI는 다음 역할을 한다.

```text
1. Synthetic training data 생성
2. Hard negative / edge case 생성
3. Student small agent 평가 / benchmark judge
4. Prompt/schema 개선
5. 실패 케이스 재라벨링
```

### 10.1 Teacher 연결 방식

| 방식 | 대상 | 설명 |
|---|---|---|
| BYO API Key | Community/개발자 | v0는 OpenAI(`api.openai.com`) + 사용자가 지정한 OpenAI-compatible `base_url` 1개만 허용(SECURITY_SPEC §19). Gemini/Anthropic/OpenRouter는 v0.2+ 후보 |
| Local Teacher (v0.2+ reference) | 보안/오프라인 사용자 | Ollama, LM Studio, vLLM, llama.cpp server |
| Managed Teacher Hub (v0.2+ reference) | Pro/Team 사용자 | synthetic data, hard negative, eval judge, benchmark를 credit으로 제공 |

> **v0 구현 규칙:** Teacher provider UI/API는 BYO API Key 경로만 활성화한다. Local Teacher와 Managed Teacher Hub는 roadmap reference이며, v0.2+ ADR 전에는 disabled 상태 외로 구현하지 않는다.

### 10.2 Teacher 등급

| Teacher 등급 | 모델 크기 | 역할 | 필요 사양 |
|---|---:|---|---|
| Teacher Lite | 7B~8B | 초안 생성, 간단 라벨링 | 8~12GB VRAM |
| Teacher Standard | 12B~14B | synthetic data, hard negative | 16~24GB VRAM |
| Teacher Pro Local | 24B~32B | benchmark judge, 고급 데이터 생성 | 24~48GB VRAM |
| Cloud Teacher | GPT/Gemini/Claude/대형 open model | 고품질 teacher/judge | 로컬 GPU 불필요 |

### 10.3 기본 전략

```text
v0 Student: locked strict catalog(`google/gemma-2b-it`, `microsoft/Phi-3.5-mini-instruct`)
v0 Teacher: BYO OpenAI-compatible provider only
v0.2+ reference: Local Teacher 12B~14B quantized, 24B+ judge, managed teacher hub
```

---

## 11. Hardware Doctor

MIB Studio의 첫 기능 중 하나는 **내 PC가 어떤 small agent를 만들 수 있는지 검사하는 Hardware Doctor**여야 한다.

### 11.1 검사 항목

```text
1. OS 확인
2. CPU 확인
3. RAM 확인
4. GPU vendor 확인
5. VRAM 총량/사용 가능량 확인
6. CUDA/ROCm/Metal/Vulkan 지원 확인
7. 드라이버 버전 확인
8. Python/torch/transformers/peft/bitsandbytes 설치 확인
9. 로컬 runtime provider(v0.2+ reference: Ollama/vLLM/llama.cpp) 설치 확인
10. 디스크 여유 공간 확인
11. 짧은 inference test
12. 짧은 training dry-run
```

### 11.2 Capability Tier

```text
Tier 0: CPU Only
- 데이터셋 생성
- BYO Cloud Teacher
- eval 일부
- local training 비추천

Tier 1: Inference Lite
- 4B~8B quantized inference
- prompt-only baseline
- local teacher lite

Tier 2: Train Small
- 2B~4B LoRA/QLoRA 가능
- Router 학습 가능(v0 핵심). Extractor는 v0.2+ 프리셋 확장 후 같은 tier를 재사용한다.

Tier 3: Train Medium
- 7B~8B QLoRA 가능
- production small agent 가능

Tier 4: Teacher Local
- 12B~14B teacher inference 가능
- local synthetic data 가능

Tier 5: Pro Local Lab
- 24B+ teacher / 12B training 가능
- benchmark lab 가능
```

> **v0 단순화:** 위 Tier는 내부 분류이며, v0 UI는 3개 게이트로만 노출한다.
> - **G0 데이터/추론**: 학습 불가(CPU 또는 AMD/Intel GPU). 데이터 생성·eval·추론·BYO Cloud Teacher만.
> - **G1 Train Small**: NVIDIA ≥12GB(QLoRA) 또는 **Apple Silicon 통합 RAM ≥16GB(MLX)**. 2~4B Router 학습 가능(v0 핵심 경로).
> - **G2 Train Plus**: NVIDIA ≥24GB 또는 **Apple Silicon 통합 RAM ≥32GB**. 7~8B 및 local teacher 가능(v0.2+).
>
> 학습 백엔드는 플랫폼별로 분기한다 — NVIDIA=CUDA(LLaMA-Factory), Apple Silicon=MLX([ARCHITECTURE §13.3](./ARCHITECTURE.md)). AMD/Intel GPU는 v0에서 G0(학습 미지원)(§12 전제).

### 11.3 Preflight Dry-run

VRAM 공식만으로는 부족하므로 실제 미니 테스트를 수행한다.

```text
1. 선택 모델 로드 가능 여부 확인
2. 256~512 token inference test
3. 10 sample eval test
4. 5~10 step training dry-run: NVIDIA는 QLoRA, Apple Silicon은 MLX LoRA
5. peak VRAM 측정
6. tokens/sec 측정
7. 예상 학습 시간 계산
```

예상 출력(예시, 실측값은 머신마다 다름):

```text
Model: google/gemma-2b-it (NVIDIA=QLoRA / Apple Silicon=MLX LoRA), seq_len 1024, batch 1, grad_accum 16, LoRA rank 16

Estimated training time (±30%):
- 1,000 examples: ~25 min
- 5,000 examples: ~2h

VRAM peak:
- observed: 13.8GB / 16GB
- risk: medium

Recommendation:
- seq_len 1024 (2048은 VRAM +60~80%)
- batch size 1
- gradient accumulation 16
- LoRA rank 16
```

> **한계:** dry-run(5~10 step)은 로드/VRAM/속도만 검증한다. 데이터 품질·loss 발산·후반 OOM은 보장하지 않으므로, 추정치는 ±30% 범위로 표기하고 학습 중 실시간 VRAM 가드(임계 초과 시 자동 중단·권고)를 둔다.

---

## 12. 최소/권장 사양

> **공통 전제:** 아래 학습 사양은 *seq_len 1024, batch 1, grad_accum 8~16, LoRA rank 8~16, bf16, gradient checkpointing 활성* 기준 추정이며 Hardware Doctor 실측으로 보정한다. **학습 경로는 플랫폼별로 분기한다 — NVIDIA=CUDA(LLaMA-Factory/bitsandbytes QLoRA), Apple Silicon=MLX(통합 메모리, mlx-lm LoRA 4-bit).** AMD(ROCm)/Intel은 v0 학습 비지원이며 데이터 생성·추론·eval만 가능하다. NVIDIA는 VRAM, Apple Silicon은 통합 RAM이 기준이며, seq_len을 2048로 올리면 메모리 요구가 약 1.6~1.8배 증가한다.

### 12.1 Community 최소 사양

앱 실행 + 데이터셋 생성 + eval 일부 기준.

| 항목 | 최소 | 권장 |
|---|---:|---:|
| OS | Windows 11 / Ubuntu 22.04+ / macOS Apple Silicon | Ubuntu 22.04+ 또는 Windows 11 + WSL2 |
| RAM | 16GB | 32GB 이상 |
| GPU | 없어도 실행 | NVIDIA 8GB VRAM 이상 |
| Storage | 50GB | NVMe 200GB 이상 |
| Python | 3.11.x | 3.11.x 고정 |
| 기능 | BYO API teacher, dataset/eval | 2B~4B local inference |

### 12.2 2B~4B 학습 가능 사양

| 항목 | 최소 | 권장 |
|---|---:|---:|
| GPU | NVIDIA 12GB VRAM (QLoRA) | NVIDIA 16GB VRAM |
| RAM | 32GB | 64GB |
| Storage | 100GB | NVMe 200GB+ |
| 학습 방식 | QLoRA + gradient checkpointing | QLoRA, seq_len ≤1024 |
| 대상 | Router (v0 핵심), Extractor(v0.2+) | 실사용 small agent |

### 12.3 7B~8B 학습 가능 사양

| 항목 | 최소 | 권장 |
|---|---:|---:|
| GPU | NVIDIA 20GB VRAM (QLoRA) | NVIDIA 24GB VRAM |
| RAM | 64GB | 64~128GB |
| Storage | 200GB | NVMe 500GB |
| 학습 방식 | QLoRA, seq_len ≤1024 | QLoRA + gradient checkpointing |
| 대상 | 고품질 specialist agent | production 후보 |

### 12.4 12B 학습 가능 사양

| 항목 | 최소 | 권장 |
|---|---:|---:|
| GPU | NVIDIA 32GB VRAM (QLoRA) | NVIDIA 48GB VRAM |
| RAM | 64GB | 128GB |
| Storage | 300GB | NVMe 1TB |
| 학습 방식 | QLoRA, seq_len ≤1024, grad checkpointing 필수 | 안정적 QLoRA |
| 대상 | 고급 agent | local teacher/student 겸용 |

### 12.5 Apple Silicon (Unified Memory) 학습 가능 사양

> Apple Silicon은 통합 메모리(unified memory)로 GPU가 시스템 RAM 대부분을 사용한다. 단, bitsandbytes NF4 QLoRA는 CUDA 전용이라 Apple Silicon에서는 **MLX 백엔드(mlx-lm LoRA, 4-bit)** 경로를 쓴다([ARCHITECTURE §13.3](./ARCHITECTURE.md)).

| 항목 | 최소 | 권장 |
|---|---:|---:|
| 칩 | Apple M1 이상 (M1~M5) | M2 Pro/Max 이상 |
| 통합 RAM | 16GB → 2~4B (G1) | 32GB → 7~8B (G2), 64GB+ → 그 이상 |
| Storage | 100GB | NVMe 200GB+ |
| 학습 백엔드 | MLX (mlx-lm LoRA, 4-bit) | MLX, seq_len ≤1024 |
| OS | macOS 14+ | macOS 최신 |
| 대상 | Router (v0 핵심), Extractor(v0.2+) | 고품질 specialist agent |

> **주의:** 통합 RAM은 OS·앱과 공유되므로 가용 학습 메모리는 명목 용량보다 작다(예: 16GB에서 실제 학습 가용 ~10~11GB). MLX 경로의 eval 지표는 CUDA 경로와 [EVAL_SPEC §17.3](./EVAL_SPEC.md) parity 게이트(M4) 통과 후 비교한다.
> **v0 포함 상태:** Apple Silicon(MLX)은 **v0 포함이되 M4 parity 게이트 조건부**다. parity 실패 시 v0는 CUDA-only로 출시되고 MLX는 v0.2 fast-follow(Dev Plan CTO 결정·IR11). base model은 [ARCHITECTURE §13.3.1](./ARCHITECTURE.md) 카탈로그를 따른다.
