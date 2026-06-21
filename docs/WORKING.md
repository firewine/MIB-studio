# MIB Studio Working State

```yaml
doc_type: llm_operational_handoff
audience: llm_agents_only
purpose: read_before_each_task
format: machine_scannable_markdown_with_yaml_blocks
rule: keep_only_current_work_next_work_and_active_blockers
ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
context: docs/CONTEXT.md
```

## 0. Agent Instructions

```yaml
read_policy:
  - read this file before starting work
  - if current_work.status is no_active_work, do not infer a task from old notes
  - use docs/CONTEXT.md for project-wide constraints
  - use the SSOT/spec docs only for the active task area
  - create or update .codex/tasks/current.json before edits

write_policy:
  - keep this file short
  - record only active work, next work, blockers, and verification state
  - do not use this file as a requirements source
```

## 1. Current Phase

```yaml
phase_id: FE_V6_MOCKUP
milestone: FE_v6_RC_Blocker_Remediation
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-fe-v6-mockup
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  frontend_package_manager: cached pnpm 9.15.0 via strict Node
  corepack_home: /tmp/corepack
  strict_toolchain_path:
    node: /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin
    rustc: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin
    cargo: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin
  last_bootstrap_smoke:
    command: COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build
    status: passed
    note: plain pnpm is not on PATH and Corepack shim signature verification fails; use cached pnpm CLI path above
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-fe-v6-mockup
  implementation_commit: d7a68bf
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: apply docs/mockup v6 route-contract mockup to the desktop FE and produce verification evidence
  summary:
    - implemented v6 route-contract builder in apps/desktop with toolbox categories, block canvas, route board, inspector tabs, contract preview, presets, compile/test/download actions
    - moved route-contract rendering into apps/desktop/src/lib/routeContractView.mjs to keep main app orchestration smaller
    - added apps/desktop/e2e/fe_v6_route_contract.test.mjs browser e2e with keyboard and accessibility smoke checks
    - updated docs/mockup/README.md and docs/specs/UX_SPEC.md so mib_fe_mockup_v6_routes_contract.html is the canonical current mockup
    - recorded FE state matrix, API/SSE mapping, and verification evidence in artifacts/review/fe_v6_evidence.md
    - did not change backend, DB, worker, schema, export, benchmark, or M6-RC sign-off logic

m6_previous_work:
  fe_v6_mockup: d7a68bf
  m6_rc_signoff: 841d620
  m6_002_docker_export: b6873f5
  m6_001_zip_export: 31971d7

m5_previous_work:
  m5_003_playground: 269a63a
  m5_002_verifier: c311e4d
  m5_001_agent_contract_builder: 614184b

m4_previous_work:
  m4_003_benchmark_report: 5c3d3e7
  m4_002_eval_runner: ff058d1
  m4_001_eval_set_freeze: e51f197

m3_previous_work:
  m3_005_dry_run_oom_isolation: 5c0fd10
  m3_004_cancel_resume: b44221b
  m3_003_mlx_wrapper: 103f99e
  m3_001_training_preflight: c52a76e
  m3_001_closeout: ab1b0a6
  m3_000_model_cache_service: c683a2b
  m3_000_closeout: 96c9042
  m2_004_hard_negative_generation: 34a848e
  m2_004_closeout: 464c06c

local_committed_context:
  day0_ready: 89b346f
  m1_001_api_bootstrap: 33a326f
  m1_002_db_migration_seed: 1020a90
  m1_003_project_api: 9606ef5
  m1_004_preset_api: d896b7f
  m1_005_dataset_builder: 1c45957
  m1_006_hardware_doctor: 260693d
  m1_007_desktop_shell: f45968f
  m1_final_smoke_verification: c13fb6f
  m1_final_smoke_closeout: ccb21eb
  m3_002_cuda_wrapper: e8c8fc9
  m3_003_mlx_wrapper: 103f99e
  m3_004_cancel_resume: b44221b
  m3_005_dry_run_oom_isolation: 5c0fd10
  m4_001_eval_set_freeze: e51f197
  m4_002_eval_runner: ff058d1
  m4_003_benchmark_report: 5c3d3e7
  m5_001_agent_contract_builder: 614184b
  m5_002_verifier: c311e4d
  m5_003_playground: 269a63a
  m6_001_zip_export: 31971d7
  m6_002_docker_export: b6873f5
  m6_rc_signoff: 841d620
  fe_v6_mockup: d7a68bf

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: fe_v6_mockup_verified
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run e2e
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/m2_teacher_packet_preview.test.mjs
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/fe_v6_route_contract.test.mjs
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO until a scoped re-review is run
  - real digest-pinned Docker image build/save/run transcript evidence is missing
  - plain pnpm is not on PATH and Corepack shim signature verification fails; use cached pnpm CLI path
  - file_size_report has existing soft warnings only; no hard file-size violations remain
failed: []
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true
  M1_Final_Smoke_Verified: true
  M2_000_Verified: true
  M2_001_Verified: true
  M2_002_Verified: true
  M2_003_Verified: true
  M2_004_Verified: true
  M3_000_Verified: true
  M3_001_Verified: true
  M3_002_Verified: true
  M3_003_Verified: true
  M3_004_Verified: true
  M3_005_Verified: true
  M4_001_Verified: true
  M4_002_Verified: true
  M4_003_Verified: true
  M5_001_Verified: true
  M5_002_Verified: true
  M5_003_Verified: true
  M6_001_Verified: true
  M6_002_Verified: true
  FE_V6_Mockup_Verified: true

recorded_not_go:
  M6_RC_Signoff: true

active_gate:
  id: none
  cto_decision: ready_for_real_docker_runtime_evidence_then_m6_rc_rereview
  review_bundle: artifacts/review/fe_v6_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for real digest-pinned Docker runtime evidence
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - real digest-pinned Docker image build/save/run evidence
  - M6-RC re-review after Docker runtime evidence is complete
  - DB schema/model/migration changes unless explicitly required by a scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for real digest-pinned Docker image build/save/run evidence
  - run MIB_DOCKER_EXPORT_REAL_BUILD=1 with MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=<image>@sha256:<digest> for at least one CUDA/lora_adapter package
  - capture /agents/{agent_id}/run and /v1/chat/completions transcript with read-only model-cache mount
  - rerun M6-RC sign-off after Docker runtime evidence is complete
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, M3-001, M3-002
CUDA wrapper, M3-003 MLX wrapper, M3-004 Cancel/resume, M3-005 Dry-run + OOM
isolation, M4-001 Eval set freeze hardening, M4-002 Eval runner, M4-003
Benchmark report, M5-001 Agent contract builder, M5-002 Verifier, and M5-003
Playground, M6-001 Zip export, and M6-002 Docker export are committed and pushed.
M6-RC sign-off evidence is recorded at 841d620 with final CTO decision NOT_GO.
FE v6 mockup implementation is committed at d7a68bf and evidence is in
artifacts/review/fe_v6_evidence.md. Do not rerun sign-off as GO until real
digest-pinned Docker image build/save/run evidence is complete. Next work is a
new scoped Docker runtime evidence PABCD. Use .venv for Python. For frontend
commands, use cached pnpm via:
COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs
```
