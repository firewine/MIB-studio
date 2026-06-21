# M0 DevEx/Environment Review

Decision: GO
Reviewer: Codex DevEx/Environment Agent
Date: 2026-06-21
Scope: `.venv` vs Docker policy, requirements files, IDE tasks/launch, bootstrap scripts, Day-0 scaffold vs post-M1 smoke.

## Blocking Issues

None.

## Non-Blocking Issues

- Daily development is repo-local `.venv`; Docker is export verification only.
- CUDA and MLX runtime requirements are exact-pinned separately and audited profile-by-profile in CI/non-skip bootstrap environments.
- VS Code tasks include POSIX and Windows commands for scaffold and m1-smoke on CUDA and MLX.
- Day-0 scaffold artifacts exist in the repository and verify-only passes for both CUDA and MLX.
- Day-0 scaffold verification is separated from post-M1 smoke; M1 smoke remains gated on M1 API/DB/app scaffolding.
- POSIX bootstrap runs profile-specific pip-audit when the audit tool is installed and writes an explicit `artifacts/security/pip_audit_{profile}.json` skip artifact in local `--verify-only --skip-install` mode.
- PyYAML-free model catalog fallback parser can read the filled strict catalog before requirements are installed.
- Local `.env` is ignored; `.env.example` contains only an empty HF token placeholder for Day-0 gated catalog fill.

## Missing Tests

None blocking for M0. DevEx acceptance tests are listed in `DEV_ENVIRONMENT_SPEC §36.9`.

## Spec Updates Required

None.

## Assumptions

Windows native is smoke-only for v0 training; NVIDIA training development uses WSL2.
