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
phase_id: M1_FINAL_SMOKE
milestone: M1_Core
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m1-final-smoke
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  frontend_package_manager: corepack pnpm
  corepack_home: /tmp/corepack
  strict_toolchain_path:
    node: /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin
    rustc: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin
    cargo: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-m1-final-smoke
  verification_commit: c13fb6f
  pushed_to_origin_main: true
  objective: complete M1 final smoke closeout before M2
  summary:
    - added tests/smoke/test_m1_smoke.py covering M1 health, presets, project CRUD/archive guard, dataset/examples, hardware doctor, generated contracts, DB counts, and restart persistence
    - updated Python exact pins to clear patchable pip-audit findings
    - pinned CUDA Starlette separately from MLX because LLaMA-Factory keeps CUDA on gradio<=5.50.0
    - added CUDA pip-audit exception artifact for upstream-blocked Gradio/Pillow/Starlette advisories
    - restored strict m1-smoke bootstrap verification with Node 20.18.1, pnpm 9.15.0, Rust 1.83.0, Python 3.11, and SQLite 3.50

local_committed_context:
  day0_ready: 89b346f
  m1_001_api_bootstrap: 33a326f
  m1_002_db_migration_seed: 1020a90
  m1_003_project_api: 9606ef5
  m1_004_preset_api: d896b7f
  m1_005_dataset_builder: 1c45957
  m1_006_hardware_doctor: 260693d
  m1_007_desktop_shell: f45968f

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m1_final_smoke_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - bash -n scripts/bootstrap_dev.sh
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pip_audit -r requirements-mlx.txt -r requirements-dev.txt --format json
  - COREPACK_HOME=/tmp/corepack COREPACK_DEFAULT_TO_LATEST=0 PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python PATH=/tmp/mib-toolchain/node-v20.18.1-linux-x64/bin:/tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin:/tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin:$PATH ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - COREPACK_HOME=/tmp/corepack COREPACK_DEFAULT_TO_LATEST=0 PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python PATH=/tmp/mib-toolchain/node-v20.18.1-linux-x64/bin:/tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin:/tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin:$PATH ./scripts/bootstrap_dev.sh --phase m1-smoke
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile tests/smoke/test_m1_smoke.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/smoke/test_m1_smoke.py -q
  - ./.venv/bin/python -m pip check
  - git diff --check
warnings:
  - FastAPI 0.138 emits ORJSONResponse deprecation warnings in M1 smoke; behavior still passes and cleanup should be scoped separately.
not_available:
  - pwsh is not installed locally, so scripts/bootstrap_dev.ps1 was updated by parity inspection but not executed.
failed: []
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true
  M1_006_Complete: true
  M1_007_Complete: true
  M1_Final_Smoke_Verified: true

active_gate:
  id: none
  cto_decision: ready_for_m2_scoped_contract
  review_bundle: artifacts/review and artifacts/security

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M2-000 EvalSet freeze prework
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M2+ endpoint implementation without M2 PABCD contract
  - backend API behavior changes
  - DB schema/model/migration/seed changes
  - worker/training wrapper/eval/benchmark/package/export/teacher/credential runtime work
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new PABCD task contract for M2-000 EvalSet freeze prework
  - read docs/handoffs/M2.md and docs/specs/IMPLEMENTATION_GUIDE.md M2-000 sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1-001 through M1-007 and M1 final smoke
are committed and pushed. Do not start M2 until a new PABCD task contract is created
for M2-000 EvalSet freeze prework. Use .venv for Python and COREPACK_HOME=/tmp/corepack.
CUDA pip-audit has explicit upstream-blocked exceptions in
artifacts/security/pip_audit_cuda_exceptions.json.
```
