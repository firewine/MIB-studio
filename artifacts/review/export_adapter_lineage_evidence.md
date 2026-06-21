# Export Adapter Lineage Evidence

Date: 2026-06-22
Gate: `mib-studio-export-adapter-lineage-verification`
Decision: `GO_EXPORT_LINEAGE_VALIDATION`

## Scope

This gate hardens M6 export provenance. Zip and Docker exports now verify that
the adapter files being packaged still match the `ModelRun` adapter artifact
hashes recorded when training completed.

This does not prove that the adapter performs useful inference, and it does not
produce a real trained CUDA adapter in this environment. M6-RC remains `NOT_GO`
until no-fake-backend endpoint transcripts pass with a real trained adapter.

## Change

`services/worker/handlers/export.py` now validates the adapter lineage before
copying adapter files into the export tree:

- `ModelRun.adapter_sha256` and `ModelRun.artifact_manifest_sha256` must both
  be present.
- `manifest.json` must exist next to the adapter directory, matching the
  training writer layout where `adapter_path` points to `<run_dir>/adapter`.
- The current `manifest.json` SHA256 must match
  `ModelRun.artifact_manifest_sha256`.
- The current adapter file rows must hash to `ModelRun.adapter_sha256`.
- `manifest.json.adapter_sha256` and `manifest.json.files` must match the
  current adapter files.

The export fixture now creates adapter files and writes their manifest before
AgentPackage creation, matching the product sequence more closely:

```text
benchmark complete
  -> write structured temporary adapter files
  -> write adapter manifest
  -> store ModelRun.adapter_path / adapter_sha256 / artifact_manifest_sha256
  -> create AgentPackage
  -> export
```

## Verification

Adapter lineage, manifest, and rejection tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_export_manifest.py -q
```

Result:

```text
6 passed, 18 warnings in 182.97s
```

Export API and Docker export tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_export_api.py tests/export/test_docker_export_security.py -q
```

Result:

```text
4 passed, 11 warnings in 142.23s
```

Runtime smoke and package/playground/export parity:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_runtime_smoke.py tests/export/test_package_playground_export_output_parity.py -q
```

Result:

```text
4 passed in 0.39s
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
export_requires_model_run_adapter_hashes: true
export_rejects_adapter_file_hash_mismatch: true
export_rejects_adapter_manifest_hash_mismatch: true
export_accepts_valid_current_adapter_lineage: true
trained_adapter_inference_proven: false
m6_rc: NOT_GO
```

Next required action before M6-RC GO:

1. Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
2. Export with matching adapter manifest/hash lineage.
3. Run `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
   without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Rerun M6-RC sign-off only after those endpoint transcripts pass.
