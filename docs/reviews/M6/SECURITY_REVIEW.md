# M6 Security Review

Decision: NO_GO
Reviewer: Codex Security Agent
Date: 2026-06-22
Scope: Export artifact secrets, bearer token behavior, SBOM/CVE evidence, Docker runtime security, and no-fake endpoint evidence.

## Blocking Issues

- P1: RC-level no-fake Docker endpoint transcript with a real trained adapter is
  missing. Fixture adapter evidence with `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1` does
  not prove the production runtime path.

## Evidence

- Export secret scan self-test passes in M1 smoke evidence.
- Docker image tar scanner remediation is recorded in
  `artifacts/review/docker_runtime_remediation_evidence.md`.
- Docker real backend dependency packaging and temp image import probe are
  recorded in `artifacts/review/docker_real_backend_deps_evidence.md`.
- Runtime startup validates `MIB_RUNTIME_BEARER_TOKEN` before health succeeds.
- Phi fixture endpoint evidence records read-only model-cache mount behavior,
  but explicitly uses `MIB_RUNTIME_ALLOW_FAKE_BACKEND=1`.

## Non-Blocking Issues

- Existing CUDA pip-audit exceptions remain governed by
  `artifacts/security/pip_audit_cuda_exceptions.json`.

## Missing Tests

- Container run transcript for `/agents/{agent_id}/run` without
  `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
- Container run transcript for `/v1/chat/completions` without
  `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
- Container run evidence showing the mounted model cache is read-only for the
  real adapter runtime path.

## Spec Updates Required

- None.

## Assumptions

- No runtime, fallback, Local Daemon, or teacher API tokens are baked into
  exported artifacts.
