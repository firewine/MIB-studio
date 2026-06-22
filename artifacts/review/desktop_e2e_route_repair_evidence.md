# Desktop E2E Route Repair Evidence

```yaml
date: 2026-06-22
gate: mib-studio-desktop-e2e-route-repair
decision: GO_DESKTOP_E2E_ROUTE_REPAIR_M6_NOT_GO
scope: desktop_ui_copy_and_e2e_route_surface_only
backend_changed: false
m6_rc_changed: false
```

## Result

Desktop M1, FE v6 route-contract, and M2 teacher packet preview e2e checks pass in a real localhost/headless Chrome environment.

M6-RC remains `NOT_GO` because this gate does not provide real trained CUDA `lora_adapter` no-fake Docker endpoint evidence.

## Root Cause

The e2e tests navigate from `/projects` to `/projects/new` and wait for the project creation screen text:

```text
Create route contract project
```

The desktop project wizard rendered:

```text
Route contract project
```

This made the M1 happy path time out after navigation even though the route itself existed.

## Change

`apps/desktop/src/main.mjs` now renders the project wizard title as:

```text
Create route contract project
```

No backend, schema, training, export, runtime, or M6 evidence policy files were changed.

## Verification

```text
python3 -m json.tool .codex/tasks/current.json
PASS

COREPACK_HOME=/tmp/corepack corepack pnpm test
PASS - 2 tests passed

COREPACK_HOME=/tmp/corepack corepack pnpm e2e
PASS - M1 desktop shell happy path passed

COREPACK_HOME=/tmp/corepack node --test apps/desktop/e2e/fe_v6_route_contract.test.mjs
PASS - FE v6 route contract builder passed

COREPACK_HOME=/tmp/corepack node --test apps/desktop/e2e/m2_teacher_packet_preview.test.mjs
PASS - M2 teacher packet preview passed

git diff --check
PASS
```

`git diff --cached --check` is required after staging and is recorded in the PABCD task contract.
