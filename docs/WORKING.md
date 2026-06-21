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
phase_id: M3_004_CANCEL_RESUME
milestone: M3_Training_Runtime
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m3-004-cancel-resume
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
  gate: mib-studio-m3-004-cancel-resume
  implementation_commit: b44221b
  pushed_to_origin_main: true
  objective: implement M3-004 Cancel/resume
  summary:
    - added services/worker/checkpoint_writer.py for atomic temp-to-rename checkpoint artifact writes
    - checkpoint metrics include step, loss, adapter_sha256_at_step, optimizer_state_present, rng_state_present, and trainer_backend
    - TrainingStore now records Checkpoint rows, marks queued train cancellation, records cancel requests, exposes cooperative cancel checks, and rebinds ModelRun current JobResource
    - added services/api/app/services/job_control_service.py for cancel and resume transactions
    - DELETE /jobs/{job_id} now cancels QUEUED jobs or sets cancel_requested_at for RUNNING jobs
    - POST /jobs/{job_id}/resume validates checkpoint dataset/version/config/artifact guards before creating a child train Job
    - resume child Job copies model_run_id and checkpoint_id, increments attempt_count, rebinds current JobResource, writes JobEvent resume_started, and records AuditEvent(job_control, action=resume)
    - focused tests cover queued cancel, running cancel request, checkpoint artifact/metrics persistence, dataset/config/missing-artifact resume guards, optimizer/RNG warning audit, and successful child-job rebind

m3_previous_work:
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

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m3_004_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/worker/checkpoint_writer.py services/shared/db/repositories/training_store.py services/api/app/services/job_control_service.py services/api/app/routes/jobs.py services/api/app/schemas/job.py tests/training/test_checkpoint_resume.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/training/test_checkpoint_resume.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/training/test_training_preflight.py tests/training/test_cuda_wrapper.py tests/training/test_mlx_wrapper.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - git diff --check
  - git diff --cached --check
warnings:
  - file_size_report has soft warnings only; no hard file-size violations remain
  - FastAPI ORJSONResponse deprecation warnings remain in existing training preflight tests
failed:
  - initial checkpoint_resume pytest failed due test fixture FK flush order; fixture was fixed and focused pytest passed
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

active_gate:
  id: none
  cto_decision: ready_for_m3_005_scoped_contract
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M3-005 Dry-run + OOM isolation
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - dry-run estimate and OOM isolation
  - DB schema/model/migration changes unless explicitly required by the next scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for M3-005 Dry-run + OOM isolation
  - read docs/handoffs/M3.md and docs/specs/IMPLEMENTATION_GUIDE.md M3-005 sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, M3-001, M3-002
CUDA wrapper, M3-003 MLX wrapper, and M3-004 Cancel/resume are committed and
pushed. Do not start M3-005 until a new scoped PABCD task contract is created.
Use .venv for Python, COREPACK_HOME=/tmp/corepack, and COREPACK_DEFAULT_TO_LATEST=0 for bootstrap checks.
```
