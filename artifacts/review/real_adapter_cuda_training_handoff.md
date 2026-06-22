# CUDA LoRA Training Handoff

```yaml
date: 2026-06-22T02:15:02.017602+00:00
gate: mib-studio-cuda-real-adapter-training-handoff
status: PREPARED_NOT_RUN
release_claimed_go: false
m6_rc_claimed_go: false
```

This artifact prepares a real CUDA LLaMA-Factory QLoRA adapter run. It does not run training in the current host and does not claim M6-RC or v0 release GO.

## Inputs

```yaml
dataset_jsonl: examples/fixtures/router_20.jsonl
dataset_id: review_router_20
dataset_sha256: 3be5cdfe2f6b655eed0e9c11c8ec23b5778bf61798b4c8fb152be67a9953bd90
base_model: microsoft/Phi-3.5-mini-instruct
model_cache_dir: /tmp/mib-strict-model-cache/model_cache
output_root: /tmp/mib-real-adapter
training_preset: quick
seed: 42
max_seq_length: 1024
```

## Backend Config

```yaml
lora_rank: 4
lora_alpha: 8
lora_target: all
quantization_bit: 4
template: phi
output_dir: /tmp/mib-real-adapter/adapter
```

## Operator Rules

- Run on a host with NVIDIA CUDA visible to nvidia-smi.
- Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.
- Do not use fixture-sized or self-test adapters as release evidence.
- Do not claim M6-RC or v0 GO until the downstream real adapter handoff and verifiers return GO.

## Command Sequence

### train_real_adapter

```bash
llamafactory-cli train /tmp/mib-real-adapter/backend_config.yaml
```

### finalize_manifest

```bash
./.venv/bin/python scripts/prepare_cuda_lora_training_run.py --finalize-only --base-model microsoft/Phi-3.5-mini-instruct --output-root /tmp/mib-real-adapter --json-output artifacts/review/real_adapter_cuda_training_finalize.json
```

### verify_adapter_intake

```bash
./.venv/bin/python scripts/verify_real_adapter_artifact.py --adapter-dir /tmp/mib-real-adapter/adapter --base-model microsoft/Phi-3.5-mini-instruct --manifest /tmp/mib-real-adapter/manifest.json --json-output artifacts/review/real_adapter_artifact_intake.json
```

### run_rc_handoff

```bash
bash artifacts/review/real_adapter_cuda_handoff.sh
```
