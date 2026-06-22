# CUDA LoRA Training Handoff

```yaml
date: 2026-06-22T14:19:51.251122+00:00
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
model_cache_dir: /tmp/mib-strict-model-cache-phi/model_cache
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
- If MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is unset, resolve a local CUDA/PyTorch base image with scripts/resolve_cuda_base_image.py before preflight.
- Do not use fixture-sized or self-test adapters as release evidence.
- Do not claim M6-RC or v0 GO until the downstream real adapter handoff and verifiers return GO.

## Package Readiness Checks

The generated shell refuses to run until these package prerequisites are present:

- `dataset_jsonl_present`: `examples/fixtures/router_20.jsonl` - Training dataset JSONL exists on the CUDA host.
- `python_executable_present`: `./.venv/bin/python` - Repo virtualenv Python exists and is executable.
- `llamafactory_cli_present`: `./.venv/bin/llamafactory-cli` - LLaMA-Factory CLI exists and is executable.
- `model_cache_dir_present`: `/tmp/mib-strict-model-cache-phi/model_cache` - Strict base-model cache directory is present on the CUDA host.
- `backend_config_present`: `/tmp/mib-real-adapter/backend_config.yaml` - Generated LLaMA-Factory backend_config.yaml is present under the adapter output root.
- `rc_handoff_shell_present`: `artifacts/review/real_adapter_cuda_handoff.sh` - Downstream real-adapter RC handoff shell is present before endpoint evidence capture.

## Command Sequence

### resolve_cuda_base_image

```bash
./.venv/bin/python scripts/resolve_cuda_base_image.py --json-output artifacts/review/real_adapter_cuda_base_image_resolution.json --env-output artifacts/review/real_adapter_cuda_base_image.env --expected-status CUDA_BASE_IMAGE_RESOLVED --candidate pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
```

### preflight_cuda_training

```bash
./.venv/bin/python scripts/check_cuda_lora_training_prereqs.py --dataset-jsonl examples/fixtures/router_20.jsonl --base-model microsoft/Phi-3.5-mini-instruct --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --output-root /tmp/mib-real-adapter --backend-config /tmp/mib-real-adapter/backend_config.yaml --image mib-export:test --llamafactory-cli ./.venv/bin/llamafactory-cli --verify-model-cache-hashes --json-output artifacts/review/real_adapter_cuda_training_prereq_preflight.json
```

### train_real_adapter

```bash
./.venv/bin/llamafactory-cli train /tmp/mib-real-adapter/backend_config.yaml
```

### finalize_manifest

```bash
./.venv/bin/python scripts/prepare_cuda_lora_training_run.py --finalize-only --base-model microsoft/Phi-3.5-mini-instruct --output-root /tmp/mib-real-adapter --json-output artifacts/review/real_adapter_cuda_training_finalize.json
```

### verify_adapter_intake

```bash
./.venv/bin/python scripts/verify_real_adapter_artifact.py --adapter-dir /tmp/mib-real-adapter/adapter --base-model microsoft/Phi-3.5-mini-instruct --manifest /tmp/mib-real-adapter/manifest.json --json-output artifacts/review/real_adapter_artifact_intake.json
```

### prepare_docker_image

```bash
./.venv/bin/python scripts/prepare_real_adapter_docker_image.py --adapter-root /tmp/mib-real-adapter --base-model microsoft/Phi-3.5-mini-instruct --agent-id finance.router.v1 --image mib-export:test --context-output /tmp/mib-real-adapter/docker_context --cuda-base-image-json-output artifacts/review/real_adapter_cuda_base_image_resolution.json --cuda-base-image-env-output artifacts/review/real_adapter_cuda_base_image.env --json-output artifacts/review/real_adapter_docker_image_handoff.json --markdown-output artifacts/review/real_adapter_docker_image_handoff.md --shell-output artifacts/review/real_adapter_docker_image_handoff.sh --cuda-base-image-candidate pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
```

### run_rc_handoff

```bash
bash artifacts/review/real_adapter_cuda_handoff.sh
```
