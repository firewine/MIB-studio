# M0 CTO Decision

Decision: GO
Date: 2026-06-21
Integrator: Codex CTO Integrator

## Scope

M0 is approved as a documentation contract and Day-0 scaffold milestone. This GO does not claim the app is implemented; it means the locked spec, development plan, model catalog, API/export contracts, and scaffold artifacts are sufficient for M1 implementation to start.

## Decision Basis

- 2026-06-21 peer review initially found open P1 blockers across FE, DB/BE, LLM/Export, Security/DevEx, and model catalog; focused follow-up reviews closed the API/DTO, M6 export-contract, and strict catalog blockers.
- Local scaffold validation passes and is now paired with strict model catalog verification.
- Current remediation patches closed the scoped OpenAPI/generated DTO parity blockers; final focused API/DTO re-review returned GO.
- Networked strict model catalog fill succeeded for both `google/gemma-2b-it` and `microsoft/Phi-3.5-mini-instruct`.
- Strict verifier enforcement now rejects `M1_DAY0_FILL` placeholders anywhere in `presets/model_catalog.yaml` during strict mode.
- Strict verification now returns `errors: []` for `presets/model_catalog.yaml` with `catalog_sha256=5d77b1acef66ca73afcef6e8b772be91b10001d5b5275b62fe67e0fd64dffab1`.
- M6 exported runtime was reclassified correctly: M0 requires an implementation-ready paper contract, while real adapter loading/inference code is M6 acceptance evidence.

## Conditions

- OpenAPI/generated DTO parity must stay aligned for Dataset detail rows, cursor/filter params, retry/resume request bodies, Hardware Doctor disabled reasons, checkpoint resume, Playground fallback, credentials, teacher packet preview, and model catalog availability.
- Strict model manifest must contain no `M1_DAY0_FILL`, every v0 base model must have a pinned HF commit and required weight shard hashes, and gated model fill must use a terms-accepted HF token.
- M6 exported runtime contract must be implementation-ready on paper: endpoint shapes, loader responsibilities, base-model cache materialization, adapter file shapes, manifest/schema roles, auth/fallback/security, and tests that fail hardcoded or metadata-only runtimes. Real adapter loading/inference code is required for M6, not M0.
- Benchmark/Job/domain status terminology, retry/resume resource rebinding, phase-aware CI, PII holdout, and export security gates must remain internally consistent.

## Remaining P1

- None.

## M1 Entry Authorization

M1 is authorized. M1 implementation must preserve the locked contracts above and may only change M0 decisions through an ADR or CTO review update.
