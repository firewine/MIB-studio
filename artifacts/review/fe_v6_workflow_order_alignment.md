# FE v6 Workflow Order Alignment Evidence

Date: 2026-06-23
Gate: `mib-studio-fe-v6-workflow-order-alignment`
Source head before change: `006cc89`

## Scope

This phase aligns the desktop sidebar workflow ordering with the canonical FE v6
mockup and `docs/specs/UX_SPEC.md`.

No backend, API, DB, schema, release-readiness, packet, adapter, Docker, or M6
review behavior was changed.

## Workflow Order

```yaml
previous_app_order:
  - Project
  - Define
  - Data
  - Hardware
  - Train
  - Benchmark
  - Package
  - Export

current_app_order:
  - Workbench
  - Hardware
  - Define
  - Data
  - Train
  - Benchmark
  - Package
  - Export
```

The current order matches the v6 mockup/UX flow: Hardware before Define/Data,
then Train, Benchmark, Package, and Export.

## Verification

```yaml
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --test apps/desktop/src/lib/appModel.test.mjs
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/fe_v6_route_contract.test.mjs
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build
```

## Release Boundary

```yaml
release_claimed_go: false
m6_rc_claimed_go: false
v0_release_ready: false
current_release_blocker: real_trained_adapter_no_fake_endpoint
```

M6-RC and v0 release remain NOT_GO until accepted real trained CUDA
`lora_adapter` no-fake Docker endpoint evidence exists.
