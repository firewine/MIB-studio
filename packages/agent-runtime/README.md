# Agent Runtime Templates

This package owns the exported runtime templates used by M6.

M0 status: these files are scaffold contract placeholders. They prove the export
artifact shape, but they do not satisfy M6 until the runtime loads the exported
adapter and performs backend inference through the CUDA/MLX loaders.

Base model weights are never bundled into v0 zip/Docker exports and the runtime
does not download from Hugging Face. M6 runtime code must read
`manifest.json.base_model`, require `MIB_MODEL_CACHE_DIR`, verify the strict
cache files by SHA256, and only then load the adapter.

Required implementation files after M6-001:

- `templates/zip_runtime/agents/run.py`
- `templates/zip_runtime/agents/verifier.py`
- `templates/zip_runtime/agents/fallback.py`
- `templates/zip_runtime/agents/security.py`
- `templates/zip_runtime/requirements-runtime.txt`
- `templates/docker/Dockerfile.cuda`
- `loaders/transformers_lora.py`
- `loaders/mlx_lora.py`
- `tests/test_exported_runtime_smoke.py`

The local daemon copies these templates into the export work directory, injects
the immutable AgentContract, route catalog, schemas, adapter metadata, and then
validates `manifest.json` with `schemas/export_manifest.schema.json`.
