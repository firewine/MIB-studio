# Real Adapter Inference Evidence

Date: 2026-06-22
Gate: `mib-studio-real-adapter-inference-evidence`
Decision: `NOT_GO_REAL_ADAPTER_INFERENCE_BLOCKED`

## Scope

This evidence checks whether the remaining M6-RC blocker can be closed by
running Docker endpoint transcripts with a real trained CUDA `lora_adapter` and
without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.

No product code was changed. Repo edits in this gate are limited to evidence,
handoff state, and the PABCD task contract.

M6 acceptance still requires real adapter inference:

- `/healthz` must load the exported runtime state.
- `/agents/{agent_id}/run` must execute the adapter path and pass verifier
  validation.
- `/v1/chat/completions` must execute the same adapter path and return
  equivalent route/confidence JSON.
- Evidence using `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1` is endpoint-path evidence
  only. It is not trained-adapter acceptance.

## Existing Adapter Artifact Search

Command:

```text
find /home/firewine/MIB-studio /tmp -maxdepth 10 -type f \( -name 'adapter.safetensors' -o -name 'adapter_config.json' -o -name 'adapter_model.safetensors' -o -name 'adapter_model.bin' \) -printf '%s %p\n'
```

Result summary:

- No non-fixture adapter artifact was found in the repo or current `/tmp`
  work artifacts.
- All discovered `adapter.safetensors` files were 12 bytes.
- All discovered `adapter_config.json` files were 26 bytes.
- Matching paths were pytest/temp/export fixture paths, including the Phi Docker
  evidence fixture export under `/tmp/mib-phi-docker-export-_vgqfd4g`.
- Several system-owned `/tmp/systemd-private-*` paths returned permission
  denied; these are not MIB Studio artifact roots.

Representative hits:

```text
12 /tmp/mib-phi-docker-export-_vgqfd4g/adapters/3e01f8ab82ac4bf8ba65c013825cdef7/adapter.safetensors
26 /tmp/mib-phi-docker-export-_vgqfd4g/adapters/3e01f8ab82ac4bf8ba65c013825cdef7/adapter_config.json
12 /tmp/mib-phi-docker-export-_vgqfd4g/.mib-home/projects/f057829908224162825bea3e144201f0/exports/989c1bbe5246469a8a9839cf4c5340ef/docker_context/adapter/adapter.safetensors
26 /tmp/mib-phi-docker-export-_vgqfd4g/.mib-home/projects/f057829908224162825bea3e144201f0/exports/989c1bbe5246469a8a9839cf4c5340ef/docker_context/adapter/adapter_config.json
```

Conclusion:

```yaml
real_trained_adapter_found: false
fixture_adapter_only: true
m6_acceptance_closed_by_existing_artifact: false
```

## Hardware And Training Tooling Check

Commands:

```text
which nvidia-smi
nvidia-smi
which llamafactory-cli
```

Results:

```text
which nvidia-smi -> exit 1, no output
nvidia-smi -> exit 127, /bin/bash: line 1: nvidia-smi: command not found
which llamafactory-cli -> exit 1, no output
```

The project `.venv` does contain Python import modules that would be relevant
to local training/runtime work:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import importlib.util, json; mods=['torch','transformers','peft','bitsandbytes','llamafactory','accelerate','safetensors']; print(json.dumps({m: importlib.util.find_spec(m) is not None for m in mods}, sort_keys=True))"
```

Output:

```json
{"accelerate": true, "bitsandbytes": true, "llamafactory": true, "peft": true, "safetensors": true, "torch": true, "transformers": true}
```

Conclusion:

```yaml
visible_nvidia_cuda_cli: false
llamafactory_cli_on_path: false
python_training_modules_present_in_venv: true
local_trained_adapter_generation_feasible_in_this_gate: false
```

## Exported Runtime Dependency Check

The exported zip runtime template requirements currently contain only:

```text
fastapi==0.115.6
uvicorn==0.34.0
pydantic==2.10.4
PyYAML==6.0.2
jsonschema==4.23.0
```

Docker image dependency probe:

```text
docker run --rm mib-export-989c1bbe5246469a8a9839cf4c5340ef:latest python -c "import importlib.util, json; mods=['torch','transformers','peft','safetensors','accelerate','bitsandbytes']; print(json.dumps({m: importlib.util.find_spec(m) is not None for m in mods}, sort_keys=True))"
```

Output:

```json
{"accelerate": false, "bitsandbytes": false, "peft": false, "safetensors": false, "torch": false, "transformers": false}
```

Conclusion:

```yaml
exported_image_has_real_transformers_backend_dependencies: false
real_lora_loader_can_import_peft_in_exported_image: false
```

## No-Fake-Backend Docker Runtime Probe

The existing Phi export image from
`artifacts/review/phi_strict_cache_runtime_evidence.md` was run without
`MIB_RUNTIME_ALLOW_FAKE_BACKEND`.

Run command shape:

```text
docker run -d --name mib-phi-real-backend-989c \
  -p 127.0.0.1:18083:8000 \
  -v /tmp/mib-strict-model-cache-phi/model_cache:/models:ro \
  -e MIB_MODEL_CACHE_DIR=/models \
  -e MIB_RUNTIME_BEARER_TOKEN=<redacted-32-char-test-token> \
  mib-export-989c1bbe5246469a8a9839cf4c5340ef:latest
```

Health transcript:

```text
GET http://127.0.0.1:18083/healthz
HTTPError 500
Internal Server Error
```

Container log root cause:

```text
ModuleNotFoundError: No module named 'peft'
RuntimeError: TRANSFORMERS_BACKEND_UNAVAILABLE
```

Temporary container cleanup:

```text
docker rm -f mib-phi-real-backend-989c
```

Conclusion:

```yaml
healthz_without_fake_backend: failed
failure_class: TRANSFORMERS_BACKEND_UNAVAILABLE
first_missing_runtime_dependency: peft
endpoint_acceptance_transcripts_without_fake_backend_available: false
```

## Decision

```yaml
m6_rc_real_trained_adapter_inference: NOT_GO
primary_blockers:
  - no real trained CUDA lora_adapter artifact was found
  - current host exposes no nvidia-smi CUDA CLI
  - exported Docker runtime image lacks peft/transformers/torch/safetensors
  - no-fake-backend health check fails before endpoint inference
not_a_release_go_reason:
  - previous Phi endpoint evidence used fixture adapter plus MIB_RUNTIME_ALLOW_FAKE_BACKEND=1
```

Next required action before M6-RC GO:

1. Produce or provide a real trained CUDA `lora_adapter` AgentPackage for a
   locked v0 base model, or explicitly change release policy to accept
   fixture-adapter endpoint evidence for v0 RC.
2. Ensure the exported runtime image contains the real backend dependencies
   needed by `packages/agent-runtime/loaders/transformers_lora.py`.
3. Rerun Docker endpoint evidence without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Only then rerun M6-RC sign-off.
