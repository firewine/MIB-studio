# M6 CTO Decision

Decision: NOT_GO
Date: 2026-06-22
Integrator: Codex CTO Integrator

## Scope

This decision covers the M6 Export / v0 RC gate. It does not mark the full
product complete. The active thread objective still requires final program
completion and FE implementation using the v6 mockup under `docs/mockup/`.

## Current Decision Basis

- M6-001 zip export is implemented and pushed in `31971d7`.
- M6-002 Docker export is implemented and pushed in `b6873f5`.
- FE v6 route-contract mockup is implemented and evidence is recorded in
  `artifacts/review/fe_v6_evidence.md`.
- Strict Phi model cache and fixture endpoint path evidence are recorded in
  `artifacts/review/phi_strict_cache_runtime_evidence.md`.
- Docker runtime dependency packaging for the real Transformers/PEFT backend is
  recorded in `artifacts/review/docker_real_backend_deps_evidence.md`.
- Adapter structural validation, lineage validation, and adapter-load guard
  evidence are recorded in:
  `artifacts/review/export_adapter_validation_evidence.md`,
  `artifacts/review/export_adapter_lineage_evidence.md`, and
  `artifacts/review/exported_adapter_load_guard_evidence.md`.
- Current M1 smoke recertification passes in `.venv`.

## Blocking Issues

- P1 LLM/Training/Security/DevEx: no real trained CUDA `lora_adapter` endpoint
  transcript exists without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
- Existing successful Docker endpoint transcript used fixture adapter files and
  `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1`; this proves endpoint wiring only, not
  real trained adapter inference.
- Current host evidence still shows no visible CUDA device and no real trained
  adapter artifact in the repo or current `/tmp` evidence roots.

## Required Before Re-Review

- Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
- Export a Docker image with that adapter and strict external model cache.
- Capture `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
  transcripts without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`, including read-only
  model-cache mount evidence.
- Rerun M6-RC sign-off only after those endpoint transcripts pass, or explicitly
  change release policy to accept fixture-adapter endpoint evidence.

## Remaining P1

- Real trained adapter no-fake Docker runtime evidence.

## Next Gate

Start a scoped real-adapter endpoint evidence gate when a real CUDA
`lora_adapter` is available, or start a release-policy gate if fixture-adapter
endpoint evidence is intentionally accepted for v0 RC.
