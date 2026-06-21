# Export Adapter Artifact Validation Evidence

Date: 2026-06-22
Gate: `mib-studio-export-adapter-artifact-validation`
Decision: `GO_STRUCTURAL_ADAPTER_VALIDATION`

## Scope

This gate hardens M6 zip/Docker export packaging so malformed fixture files
cannot be copied as valid adapter artifacts.

It does not prove that an adapter was trained, nor does it prove real adapter
inference. M6-RC remains `NOT_GO` until a real trained CUDA `lora_adapter`
exists and Docker endpoints pass without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.

## Change

`services/worker/handlers/export.py` now validates adapter files before copying
them into the export tree:

- `adapter_config.json` must be a JSON object.
- `adapter_config.json.format`, when present, must match the AgentContract
  adapter format.
- CUDA `lora_adapter` configs must declare either `format` or PEFT
  `peft_type`, and `peft_type` must be `LORA` when present.
- CUDA `adapter.safetensors` must be a valid safetensors container with at
  least one non-empty tensor.
- MLX `adapters.npz` must be a valid zip/npz container with at least one
  `.npy` array payload.

The export test fixture now generates temporary minimal structured adapters
instead of arbitrary bytes:

- CUDA: minimal safetensors file plus `{"format":"lora_adapter","peft_type":"LORA"}`
- MLX: minimal `.npz` file plus `{"format":"mlx_lora_adapter"}`

## Verification

Malformed/mismatch rejection and successful export manifest path:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_export_manifest.py -q
```

Result:

```text
4 passed, 12 warnings in 122.41s
```

Export API and Docker context export path:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_export_api.py tests/export/test_docker_export_security.py -q
```

Result:

```text
4 passed, 11 warnings in 142.24s
```

Runtime smoke and package/playground/export parity:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_runtime_smoke.py tests/export/test_package_playground_export_output_parity.py -q
```

Result:

```text
4 passed in 0.37s
```

Strict model catalog:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
```

Result:

```json
{"catalog_sha256":"5d77b1acef66ca73afcef6e8b772be91b10001d5b5275b62fe67e0fd64dffab1","errors":[],"model_count":2,"no_download":true}
```

## Decision

```yaml
export_rejects_malformed_cuda_safetensors: true
export_rejects_adapter_config_format_mismatch: true
export_accepts_structured_cuda_fixture_adapter: true
export_validates_mlx_npz_structure: true
trained_adapter_inference_proven: false
m6_rc: NOT_GO
```

Next required action before M6-RC GO:

1. Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
2. Export with the structurally valid real adapter.
3. Run `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
   without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Rerun M6-RC sign-off only after those endpoint transcripts pass.
