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
phase_id: M3_001_TRAINING_PREFLIGHT
milestone: M3_Training_Runtime
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m3-001-training-preflight
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
  gate: mib-studio-m3-001-training-preflight
  implementation_commit: c52a76e
  pushed_to_origin_main: true
  objective: implement M3-001 Training preflight
  summary:
    - added TrainParams validation for train job submit payloads
    - added ModelRunRead and ModelRunPage API DTOs
    - added TrainingStore for atomic ModelRun, train Job, and current JobResource insertion
    - added TrainingService preflight checks for project/preset, approved dataset, strict model catalog, hardware backend enablement, and route snapshot consistency
    - train submit writes ModelRun(status=QUEUED), Job(type=train, resource_class=gpu_exclusive), and JobResource(resource_type=model_run, is_current=1) in one transaction
    - Job.params_json includes server-owned model_run_id
    - JobAcceptedResponse returns created_resource_type=model_run and created_resource_id=model_run.id
    - added GET /projects/{id}/model-runs and GET /model-runs/{id}
    - preserved dataset_gen job submit behavior after route dispatch change
    - added focused tests for train submit resource creation, idempotency replay, model-run read/list, approved dataset guard, hardware backend guard, and route snapshot mismatch guard

m3_previous_work:
  m3_000_model_cache_service: c683a2b
  m3_000_closeout: 96c9042
  m2_004_hard_negative_generation: 34a848e
  m2_004_closeout: 464c06c
  m2_003_teacher_synthetic_generation: d1f15fd
  m2_003_closeout: de14577

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
  m3_001_training_preflight: c52a76e

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m3_001_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/api/app/main.py services/api/app/routes/jobs.py services/api/app/routes/model_runs.py services/api/app/schemas/job.py services/api/app/schemas/training.py services/api/app/services/training_service.py services/shared/db/repositories/training_store.py tests/training/test_training_preflight.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/training/test_training_preflight.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/dataset/test_teacher_synthetic_min200_schema_valid.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - git diff --check
  - git diff --cached --check
warnings:
  - focused M3-001 pytest emits existing FastAPI ORJSONResponse deprecation warnings
  - focused M3-001 pytest took 181.99s because tests prepare isolated SQLite migrations and ASGI clients
  - dataset_gen regression pytest took 61.26s and emits the same existing ORJSONResponse deprecation warning
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

active_gate:
  id: none
  cto_decision: ready_for_m3_002_scoped_contract
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M3-002 CUDA wrapper
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M3-002 CUDA wrapper
  - M3-003 MLX wrapper
  - checkpoint/resume and job control
  - DB schema/model/migration changes unless explicitly required by the next scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for M3-002 CUDA wrapper
  - read docs/handoffs/M3.md and docs/specs/IMPLEMENTATION_GUIDE.md M3-002 sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, and M3-001 Training
preflight are committed and pushed. Do not start M3-002 until a new scoped
PABCD task contract is created. Use .venv for Python and COREPACK_HOME=/tmp/corepack.
```
