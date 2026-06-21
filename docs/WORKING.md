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
phase_id: M2_000_EVALSET_FREEZE
milestone: M2_Eval_Teacher_Pipeline
phase_status: verified_ready_to_commit_and_push
active_slice: M2-000
gate_id: mib-studio-m2-000-evalset-freeze
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
objective: implement M2-000 EvalSet freeze prework
source_gate_packet: docs/handoffs/M2.md
review_tier: focused_api_service_test

implemented:
  - added EvalSet DTO validation for teacher_guard, benchmark_gold, and finance_reference quality gates
  - added EvalSet repository artifact writer for immutable JSONL freeze files under .mib-home/projects/{project_id}/eval_sets/{version}/eval_set.jsonl
  - added EvalSet service guards for project/dataset ownership, approval state, pre-teacher teacher_guard source, benchmark overlap, frozen_at, sha256, purpose, labeler_ids, kappa, and route_snapshot_sha256
  - added POST /projects/{id}/eval-sets, GET /projects/{id}/eval-sets, and GET /eval-sets/{id}
  - added focused tests in tests/eval/test_eval_set_freeze.py

last_completed_work:
  gate: mib-studio-m1-final-smoke
  verification_commit: c13fb6f
  closeout_commit: ccb21eb
  pushed_to_origin_main: true

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m2_000_verified_ready_to_push
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/api/app/routes/eval_sets.py services/api/app/schemas/eval.py services/api/app/services/eval_service.py services/shared/db/repositories/eval_store.py tests/eval/test_eval_set_freeze.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/eval/test_eval_set_freeze.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - git diff --check
warnings:
  - focused EvalSet pytest emits existing FastAPI ORJSONResponse deprecation warnings
  - focused EvalSet pytest took 121.66s because tests prepare isolated SQLite migrations and ASGI clients
failed: []
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true
  M1_Final_Smoke_Verified: true
  M2_000_Verified: true

active_gate:
  id: mib-studio-m2-000-evalset-freeze
  cto_decision: verified_ready_to_commit_and_push
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: after push, create scoped PABCD contract for M2-001 Credential storage
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M2-001 credential storage
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
  - stage explicit M2-000 files
  - commit and push M2-000
  - after push, update this file to pushed_complete or create the next scoped PABCD contract for M2-001
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1 is pushed. M2-000 EvalSet freeze is
implemented and verified but must be committed and pushed if not already present
on origin/main. Do not start M2-001 until a new scoped PABCD task contract is
created. Use .venv for Python and COREPACK_HOME=/tmp/corepack.
```
