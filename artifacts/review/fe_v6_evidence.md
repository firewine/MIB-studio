# FE v6 Route Contract Evidence

Date: 2026-06-22
Gate: `mib-studio-fe-v6-mockup`
Canonical mockup: `docs/mockup/mib_fe_mockup_v6_routes_contract.html`

## Implementation Scope

- Implemented the v6 route-contract builder in `apps/desktop` without backend/API/DB/schema changes.
- Preserved the existing M1 project, dataset, teacher packet, hardware, and job monitor flows.
- Updated canonical mockup references in `docs/mockup/README.md` and `docs/specs/UX_SPEC.md`.
- Did not change M6-RC sign-off status; RC remains blocked until real Docker runtime evidence is collected.

## Screen State Matrix

| Screen | loading | empty | ready | locked | validation_error | api_error | offline_daemon | unauthorized | retrying/cancelling/resuming | hash_mismatch | success |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ProjectList | first refresh | no projects | project rows | n/a | n/a | banner + retry | blocking API banner | API error banner | n/a | n/a | create/open |
| ProjectCreateWizard | presets/projects refresh | n/a | route validation OK | n/a | create disabled | banner | blocking API banner | API error banner | n/a | n/a | navigate project |
| RouteTaxonomyEditor / v6 Define | project load | no project routes use initial router routes | toolbox/canvas/inspector active | backend route lock remains API-owned | save disabled if route checks fail | banner | blocking API banner | API error banner | n/a | n/a | contract saved/compiled |
| ExampleGrid | dataset route load | 0 examples invalid | 20 schema-valid examples | project required | build disabled <20 | banner | blocking API banner | API error banner | n/a | n/a | dataset created |
| DatasetBuildResult | dataset load | no rows | rows visible | approval prerequisites | row errors visible through validation fields | banner | blocking API banner | API error banner | n/a | n/a | approved/packet preview |
| HardwareDoctorPanel | scan/result load | no profile | profile visible | train disabled on G0 | n/a | banner | blocking API banner | API error banner | scan job polling | n/a | G1/G2 train enabled |
| JobMonitor | job poll | no snapshot | latest snapshot | unavailable job shows event gap | n/a | EVENT_GAP notice | polling fallback banner | API error banner | poll action only | n/a | terminal job status |
| TeacherSettings | credentials load | no credential | keychain metadata visible | n/a | n/a | banner | blocking API banner | API error banner | n/a | n/a | credential saved/revoked |
| TeacherPacketPreview | packet load | no packet | sent/not-sent preview | requires approved examples | approve disabled <20 approved | banner | blocking API banner | API error banner | n/a | n/a | approval accepted |

## API And SSE Mapping

| UI Area | API/SSE Used | FE Behavior |
|---|---|---|
| App bootstrap/topbar | `get_api_bootstrap` Tauri invoke or `window.MIB_BOOTSTRAP`, `GET /healthz` | local daemon/offline state shown; bearer client created once |
| Project list/create/dashboard | `GET /projects`, `POST /projects`, `GET /projects/{id}/datasets` | empty/ready summaries; project route count drives Define link |
| v6 Define route taxonomy | `PATCH /projects/{id}` | saves route taxonomy fields supported by API while FE previews full v6 agent/input/output/rules contract locally |
| Example grid/dataset | `POST /projects/{id}/datasets`, `GET /datasets/{id}`, `PATCH /datasets/{id}` | build disabled until 20 schema-valid examples; approval updates dataset |
| Teacher packet | `POST /projects/{id}/teacher-packets/preview`, `POST /teacher-packets/{id}/approve` | sent/not-sent lists visible; raw paths/secrets remain hidden |
| Credentials | `GET /credentials`, `PUT /credentials/{provider}`, `DELETE /credentials/{provider}` | key never echoed; only keychain metadata rendered |
| Hardware Doctor | `POST /hardware-doctor/scan`, `GET /hardware-doctor/result` | G0/G1/G2 gate and disabled train CTA rendered |
| Job monitor | `GET /jobs/{job_id}` plus future `/jobs/{job_id}/events` SSE | current e2e validates poll fallback and EVENT_GAP notice |

## Browser Verification Evidence

- `COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test`: passed.
- `COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build`: passed.
- `COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run e2e`: passed.
- `COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/m2_teacher_packet_preview.test.mjs`: passed.
- `COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/fe_v6_route_contract.test.mjs`: passed.

The v6 route-contract e2e starts the static desktop app, mock API, and headless Chrome through CDP. It verifies toolbox category switching, route preset insertion, contract output preview, compile/test actions, accessible button names, active `aria-current`, live status region, and keyboard focus on the compile action.

## 2026-06-23 Workflow Order Alignment

- Gate: `mib-studio-fe-v6-workflow-order-alignment`
- Source head before change: `006cc89`
- Canonical workflow order: `Workbench -> Hardware -> Define -> Data -> Train -> Benchmark -> Package -> Export`
- App workflow order after change: `Workbench -> Hardware -> Define -> Data -> Train -> Benchmark -> Package -> Export`
- Unit coverage: `apps/desktop/src/lib/appModel.test.mjs` asserts the exact workflow label order.
- Browser coverage: `apps/desktop/e2e/fe_v6_route_contract.test.mjs` asserts the visible sidebar workflow order before route-contract edit/persistence checks.
- `release_claimed_go: false`
- M6-RC and v0 release remain NOT_GO; current release blocker remains `real_trained_adapter_no_fake_endpoint`.

## Remaining Non-FE RC Blocker

Real digest-pinned Docker image build/save/run transcript evidence remains outstanding and is outside this FE gate.
