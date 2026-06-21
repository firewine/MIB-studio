# M6 BE/API Review

Decision: GO
Reviewer: Codex BE/API Agent
Date: 2026-06-22
Scope: Export API, worker handoff, job/resource state, and artifact serving.

## Blocking Issues

- None for backend/API export scope.

## Non-Blocking Issues

- Real Docker image run smoke is still tracked as an RC evidence gap, but the API and worker contract now expose the required zip/docker paths.

## Missing Tests

- None for API wiring. `tests/export` covers zip lifecycle, docker job acceptance for CUDA, MLX `DOCKER_UNAVAILABLE`, artifact hash serving, and export worker evidence.

## Spec Updates Required

- None.

## Assumptions

- The default M6-002 Docker artifact is a deterministic build-context tar with SBOM/CVE evidence; real image build/save can be run with `MIB_DOCKER_EXPORT_REAL_BUILD=1` and `MIB_DOCKER_BASE_IMAGE_WITH_DIGEST`.
