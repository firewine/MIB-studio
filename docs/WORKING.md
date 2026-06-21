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
  - update this file when real implementation work starts or ends

write_policy:
  - keep this file short
  - record only active work, next work, blockers, and verification state
  - do not use this file as a requirements source
```

## 1. Current Phase

```yaml
phase_id: M1_007_DESKTOP_SHELL
milestone: M1_Core
phase_status: m1_007_verified_ready_for_commit_push
active_slice: desktop_shell_core_screens_only
gate_id: mib-studio-m1-007-desktop-shell
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  frontend_package_manager: corepack pnpm
  corepack_home: /tmp/corepack
  dependency_policy: no package install in M1-007 because PABCD hook blocks npm/pnpm install
```

## 2. Current Work

```yaml
mode: implement
status: m1_007_verified_ready_for_commit_push
objective: implement M1-007 Desktop shell and core screens using v6 mockup
source_gate_packet: user_goal_final_program_development_docs_based_v6_fe
review_tier: focused

allowed_edit_paths:
  - .codex/tasks/current.json
  - docs/WORKING.md
  - package.json
  - pnpm-lock.yaml
  - apps/desktop/
  - tests/smoke/test_m1_restart_persistence.py
  - artifacts/review/
  - artifacts/security/

blocked_edit_paths:
  - docs/specs/
  - docs/foundation/
  - docs/mockup/
  - docs/handoffs/
  - docs/reviews/
  - services/api/
  - services/shared/db/
  - services/worker/
  - packages/
  - .github/
  - scripts/

reference_inputs:
  - docs/specs/IMPLEMENTATION_GUIDE.md M1-007 and 14.1-14.5
  - docs/handoffs/M1.md M1-007 row
  - docs/mockup/mib_fe_mockup_v6_routes_contract.html
  - apps/desktop/src/lib/api.ts
  - apps/desktop/src/lib/bootstrap.ts
  - apps/desktop/src/lib/generated.ts

local_committed_context:
  day0_ready: 89b346f
  m1_001_api_bootstrap: 33a326f
  m1_002_db_migration_seed: 1020a90
  m1_003_project_api: 9606ef5
  m1_004_preset_api: d896b7f
  m1_005_dataset_builder: 1c45957
  m1_006_hardware_doctor: 260693d

result_so_far:
  - M0 is GO and M1 is authorized by the SSOT.
  - Local development uses repo-local Python venv at .venv; .venv is gitignored.
  - M1-001 through M1-006 are implemented, verified, committed, and pushed.
  - Backend APIs currently available for M1-007 shell: healthz, projects, presets, datasets/examples, hardware-doctor.
  - Generated frontend client already contains M1+ operation IDs; future backend operations may return MILESTONE_LOCKED.
  - M1-007 may build shell/page states and tests only; backend behavior changes remain blocked.
  - Dependency installation is blocked by the PABCD pre-tool hook, so M1-007 uses a no-install static desktop shell and Node/Chrome-CDP tests.
  - M1-007 Desktop shell is implemented and verified.
  - Shell screens cover ProjectList, ProjectCreateWizard, ProjectDashboard, RouteTaxonomyEditor, ExampleGrid, DatasetBuildResult, HardwareDoctorPanel, JobMonitor, SettingsHome, and locked future routes.
  - No backend API behavior, DB schema/model/migration, worker, or spec/mockup files were changed.
```

## 3. Verification State

```yaml
status: m1_007_passed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack corepack pnpm --version
  - COREPACK_HOME=/tmp/corepack corepack pnpm test
  - COREPACK_HOME=/tmp/corepack corepack pnpm e2e
  - COREPACK_HOME=/tmp/corepack corepack pnpm build
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/smoke/test_m1_restart_persistence.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --verify-only --skip-install
  - git diff --check
failed: []
not_run: []
required_before_done:
  - explicit git stage, commit, and push for M1-007
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true
  M1_006_Complete: true

active_gate:
  id: mib-studio-m1-007-desktop-shell
  cto_decision: m1_007_authorized_by_m1_handoff
  review_bundle: none

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: explicit M1-007 stage, commit, and push
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

blocked_until_later_gate:
  - M2+ endpoint implementation
  - backend API behavior changes
  - DB schema/model/migration/seed changes
  - worker/training wrapper/eval/benchmark/package/export/teacher/credential runtime work
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - stage explicit M1-007 files
  - commit feat: implement m1 desktop shell
  - push main to origin
  - after push, prepare next scoped task contract before starting M2

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1-001 through M1-006 are committed
and pushed; M1-006 Hardware Doctor API is at 260693d. M1-007 Desktop shell is
implemented and verified, with explicit closeout commit/push pending. Do not start
M2 backend, DB, worker, package/export/training, credential, or spec docs work before
the proper gate. Use .venv for Python and COREPACK_HOME=/tmp/corepack for pnpm commands.
```
