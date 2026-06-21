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
phase_id: M2_001_CREDENTIAL_STORAGE
milestone: M2_Eval_Teacher_Pipeline
phase_status: verified_ready_to_commit_and_push
active_slice: M2-001
gate_id: mib-studio-m2-001-credential-storage
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
mode: implement
status: verification_passed
objective: implement M2-001 Credential storage
source_gate_packet: docs/handoffs/M2.md
review_tier: focused_security_api_service_test

implemented:
  - added keyring-backed credential store adapter with SECURITY_SPEC keychain ref format
  - added Credential DTOs for upsert/list without returning api_key
  - added credentials route/service for GET /credentials, PUT /credentials/{provider}, and DELETE /credentials/{provider}
  - stores only Credential.keychain_ref/base_url metadata in SQLite and writes sanitized credential_access audit events
  - returns 503 KEYCHAIN_UNAVAILABLE without DB writes when OS keychain storage is unavailable
  - added focused tests in tests/security/test_credentials.py

last_completed_work:
  gate: mib-studio-m2-000-evalset-freeze
  implementation_commit: a8b0846
  closeout_commit: 5975108
  pushed_to_origin_main: true

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
  m2_000_evalset_freeze: a8b0846
  m2_000_closeout: 5975108

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m2_001_verified_ready_to_push
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/api/app/routes/credentials.py services/api/app/schemas/credential.py services/api/app/services/credential_service.py services/shared/security/credential_store.py tests/security/test_credentials.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/security/test_credentials.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - git diff --check
warnings:
  - focused credential pytest emits existing FastAPI ORJSONResponse deprecation warnings on error responses
  - focused credential pytest took 81.55s because tests prepare isolated SQLite migrations and ASGI clients
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

active_gate:
  id: mib-studio-m2-001-credential-storage
  cto_decision: verified_ready_to_commit_and_push
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: after push, create scoped PABCD contract for M2-002 Teacher Packet Preview
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M2-002 teacher packet preview
  - M2-003 teacher synthetic generation
  - M2-004 hard negative generation
  - worker/training wrapper/benchmark/package/export/teacher runtime work
  - DB schema/model/migration changes
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - stage explicit M2-001 files
  - commit and push M2-001
  - after push, update this file to pushed_complete or create the next scoped PABCD contract for M2-002
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1 and M2-000 are pushed. M2-001
Credential storage is implemented and verified but must be committed and pushed
if not already present on origin/main. Do not start M2-002 until a new scoped
PABCD task contract is created. Use .venv for Python and COREPACK_HOME=/tmp/corepack.
```
