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
phase_id: M2_004_HARD_NEGATIVE_GENERATION
milestone: M2_Eval_Teacher_Pipeline
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m2-004-hard-negative-generation
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
  gate: mib-studio-m2-004-hard-negative-generation
  implementation_commit: 34a848e
  pushed_to_origin_main: true
  objective: implement M2-004 Hard negative generation
  summary:
    - added hard_negative_min_count to DatasetGenParams and generated API contract
    - teacher_synthetic dataset_gen output now persists source=hard_negative rows from teacher responses
    - default fake teacher fixture emits 200 generated rows with 40 hard negatives for M2/M3 dataset readiness
    - worker fails before dataset resource creation when schema-valid hard negatives are below the required count
    - DatasetGenResult and dataset_gen JobEvent metrics now include hard_negative_count
    - generated hard negatives use the same PENDING review lifecycle and dataset approval guard as teacher examples
    - JobEvent and teacher_egress AuditEvent payloads stay count/hash-only and exclude raw prompts/examples/input/output text
    - added focused tests for hard-negative min count, shortfall failure, review lifecycle, and event payload redaction

m2_previous_work:
  m2_003_teacher_synthetic_generation: d1f15fd
  m2_003_closeout: de14577
  m2_002_teacher_packet_preview: 430b32a
  m2_002_closeout: 9a1fe8e
  m2_001_credential_storage: 30bf114
  m2_001_closeout: e816fce
  m2_000_evalset_freeze: a8b0846
  m2_000_closeout: 5975108

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
  m2_004_hard_negative_generation: 34a848e

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m2_004_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/worker/handlers/dataset_gen.py services/api/app/schemas/job.py services/api/app/services/dataset_service.py services/shared/db/repositories/dataset_store.py tests/dataset/teacher_synthetic_helpers.py tests/dataset/test_teacher_synthetic_min200_schema_valid.py tests/dataset/test_hard_negative_min_count.py tests/dataset/test_hard_negative_review_lifecycle.py tests/dataset/test_dataset_gen_event_payload_redaction.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/dataset/test_teacher_synthetic_min200_schema_valid.py tests/dataset/test_hard_negative_min_count.py tests/dataset/test_hard_negative_review_lifecycle.py tests/dataset/test_dataset_gen_event_payload_redaction.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - COREPACK_HOME=/tmp/corepack corepack pnpm test
  - git diff --check
  - git diff --cached --check
warnings:
  - focused M2-004 pytest emits existing FastAPI ORJSONResponse deprecation warnings
  - focused M2-004 pytest took 282.62s because tests prepare isolated SQLite migrations and ASGI clients
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

active_gate:
  id: none
  cto_decision: ready_for_m3_000_scoped_contract
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M3-000 Model cache service
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M3 training work
  - worker/training wrapper/benchmark/package/export/runtime work beyond the next scoped gate
  - DB schema/model/migration changes unless explicitly required by the M3 gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for M3-000 Model cache service
  - read docs/handoffs/M3.md and docs/specs/IMPLEMENTATION_GUIDE.md M3-000 sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1 and M2 are committed and pushed
through M2-004 Hard negative generation. Do not start M3-000 until a new scoped
PABCD task contract is created. Use .venv for Python and COREPACK_HOME=/tmp/corepack.
```
