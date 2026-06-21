# Exported Adapter Load Guard Evidence

Date: 2026-06-22
Gate: `mib-studio-exported-adapter-load-guard`
Decision: `GO_TEST_GUARD_ONLY_M6_NOT_GO`

## Scope

This gate closes the M6 acceptance-test gap called out by
`docs/specs/IMPLEMENTATION_GUIDE.md`: exported runtime tests must fail if the
runtime returns hardcoded routes or if a loader only returns metadata without
invoking backend inference.

No model weights or adapter artifacts were created. This evidence strengthens
test coverage only. It does not provide real trained adapter endpoint
transcripts, so M6-RC remains `NOT_GO`.

## Current Environment Check

The current host still cannot produce local CUDA adapter evidence:

```yaml
nvidia_smi_on_path: false
nvidia_smi_command: command not found
torch:
  version: 2.4.1+cu121
  cuda_available: false
  cuda_device_count: 0
  cuda_version: "12.1"
```

Current repo and `/tmp` adapter search still found fixture-sized artifacts
only. Representative fixture files are 12-byte `adapter.safetensors` and
26-byte `adapter_config.json` files under pytest/temp export directories.

## Change

Added `tests/export/test_exported_adapter_load.py` with focused M6 guard tests:

```yaml
tests:
  - test_exported_runtime_fake_backend_requires_explicit_env
  - test_exported_runtime_invokes_loaded_adapter_for_native_and_openai_requests
  - test_exported_transformers_adapter_cannot_infer_with_metadata_only
  - test_exported_mlx_adapter_cannot_infer_with_metadata_only
```

Coverage intent:

- The exported runtime does not silently use fake backend behavior unless
  `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1` is explicitly set.
- `/agents/{agent_id}/run` invokes the loaded adapter object's `infer()` method.
- `/v1/chat/completions` invokes the same adapter path through the native route.
- `TransformersLoraAdapter` cannot infer with only adapter metadata and no
  loaded tokenizer/model.
- `MlxLoraAdapter` cannot infer with only adapter metadata and no loaded
  tokenizer/model.

## Verification

New focused test:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_adapter_load.py -q
```

Result:

```text
4 passed, 2 warnings in 3.40s
```

Runtime smoke/parity regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_runtime_smoke.py tests/export/test_package_playground_export_output_parity.py -q
```

Result:

```text
4 passed in 0.36s
```

## Decision

```yaml
exported_adapter_load_guard: GO
fake_backend_requires_explicit_env: true
native_endpoint_invokes_adapter_infer: true
openai_endpoint_invokes_same_adapter_path: true
metadata_only_transformers_adapter_rejected: true
metadata_only_mlx_adapter_rejected: true
real_trained_adapter_available: false
no_fake_docker_endpoint_transcripts: false
m6_rc: NOT_GO
```

Next required action before M6-RC GO remains unchanged:

1. Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
2. Export a Docker image with that real adapter and strict external model cache.
3. Run `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
   without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Rerun M6-RC sign-off only after those transcripts pass, or explicitly
   change release policy to accept fixture-adapter endpoint evidence.
