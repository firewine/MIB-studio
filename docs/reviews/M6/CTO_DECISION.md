# M6 CTO Decision

Decision: NOT_GO
Date: 2026-06-22
Integrator: Codex CTO Integrator

## Scope

This decision covers the M6 Export / v0 RC gate. It does not mark the full product complete. The active thread objective still requires final program completion and FE implementation using the v6 mockup under `docs/mockup/`.

## Decision Basis

- M6-001 zip export is implemented and pushed in `31971d7`.
- M6-002 docker export is implemented and pushed in `b6873f5`.
- Current M6 export tests pass, including zip export, exported runtime native/OpenAI-compatible behavior, Docker request acceptance/rejection, Dockerfile security, SBOM/CVE evidence wiring, and export secret scan self-test.
- The release-candidate rule requires all agents GO without WAIVED.

## Blocking Issues

- P1 FE: FE v6 mockup implementation and Playwright/a11y evidence are missing.
- P1 Security/DevEx: RC-level real digest-pinned Docker image build/save/run transcript is missing. The default automated evidence validates deterministic Docker build context tar plus SBOM/CVE wiring, but it is not a substitute for a saved image run transcript.

## Required Before Re-Review

- Implement the v6 FE mockup in `apps/desktop` and produce FE evidence: state matrix, API/SSE mapping, Playwright happy path, and accessibility/keyboard check.
- Run real Docker export evidence with `MIB_DOCKER_EXPORT_REAL_BUILD=1` and `MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=<image>@sha256:<digest>`, then capture `/agents/{agent_id}/run` and `/v1/chat/completions` transcript with a read-only model-cache mount.

## Remaining P1

- FE v6 implementation evidence.
- Real Docker image runtime evidence.

## Next Gate

Start a scoped FE v6 implementation gate, then rerun M6-RC sign-off after FE and real Docker runtime evidence are available.
