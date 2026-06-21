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
  - move completed historical detail elsewhere only when a ledger exists
  - do not use this file as a requirements source
```

## 1. Current Phase

```yaml
phase_id: M1_002_DB_MIGRATION_SEED
milestone: M1_Core
phase_status: m1_002_complete
active_slice: db_migration_seed
gate_id: mib-studio-m1-002-db-migration-seed
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment: python_venv
venv_path: .venv
venv_gitignored: true
```

## 2. Current Work

```yaml
mode: implement
status: m1_002_complete
objective: implement M1-002 DB migration and router preset seed
source_gate_packet: user_goal_final_program_development_docs_based_v6_fe
review_tier: focused

allowed_edit_paths:
  - docs/WORKING.md
  - .codex/tasks/current.json
  - .gitignore
  - alembic.ini
  - services/shared/db/models/
  - services/shared/db/session.py
  - services/shared/db/seed.py
  - services/shared/db/migrations/env.py
  - services/shared/db/migrations/versions/0001_initial.py
  - tests/db/
  - artifacts/review/
  - artifacts/security/
blocked_edit_paths:
  - docs/specs/
  - docs/foundation/
  - docs/mockup/
  - docs/handoffs/
  - docs/reviews/
  - services/api/app/routes/
  - services/api/app/services/
  - services/worker/
  - packages/
  - apps/desktop/
  - .github/
  - scripts/

changed:
  - .gitignore
  - alembic.ini
  - services/shared/db/models/
  - services/shared/db/session.py
  - services/shared/db/seed.py
  - services/shared/db/migrations/env.py
  - services/shared/db/migrations/versions/0001_initial.py
  - tests/db/test_migration_seed.py
  - artifacts/review/file_size_report.json
local_uncommitted_context:
  note: M1-001 API bootstrap was committed and pushed at 33a326f
  do_not_revert_without_user_request: true

result_so_far:
  - M0 is GO and M1 is authorized by the SSOT.
  - Local development environment policy is repo-local Python venv at .venv.
  - .venv is ignored by .gitignore and has been recreated with Python 3.11 for future dependency setup.
  - Day-0 Bootstrap readiness verification passed, committed, and pushed.
  - M1-001 API bootstrap is implemented, verified, committed, and pushed.
  - FastAPI now exposes /healthz, Host/Origin/CORS/body/auth middleware, standard errors, trace_id response headers, and locked future stubs.
  - Bootstrap token helpers support exactly one MIB_BOOTSTRAP line for daemon startup, and Tauri/FE helpers can pass Bearer tokens.
  - M1-002 DB migration + seed is implemented and verified.
  - SQLAlchemy metadata now covers the ARCHITECTURE section 24.2 canonical SQLite schema and indexes.
  - Alembic upgrade/downgrade, FK/integrity checks, router.basic.v1 seed, model_catalog load, and critical partial unique constraints are covered by tests/db.
  - .gitignore may be repaired only to keep root model artifacts ignored while allowing services/shared/db/models source files to be tracked.
```

## 3. Verification State

```yaml
status: m1_002_complete
passed:
  - uv pip install --python .venv/bin/python SQLAlchemy==2.0.40 alembic==1.15.2 PyYAML==6.0.2
  - python3 -m json.tool .codex/tasks/current.json
  - test -d .venv
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import sqlalchemy, alembic, yaml; print('m1-db-deps-ok')"
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile services/shared/db/models/base.py services/shared/db/models/preset.py services/shared/db/models/project.py services/shared/db/models/dataset.py services/shared/db/models/eval.py services/shared/db/models/hardware.py services/shared/db/models/credential.py services/shared/db/models/job.py services/shared/db/models/training.py services/shared/db/models/package.py services/shared/db/models/audit.py services/shared/db/models/migration.py services/shared/db/models/__init__.py services/shared/db/session.py services/shared/db/seed.py tests/db/test_migration_seed.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/db -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --verify-only --skip-install
  - git diff --check
failed: []
not_run: []
required_before_done:
  - explicit git stage, commit, and push for M1-002
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true

active_gate:
  id: mib-studio-m1-002-db-migration-seed
  cto_decision: m1_002_complete
  review_bundle:
    - tests/db/test_migration_seed.py
    - artifacts/review/file_size_report.json

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: scoped M1-003 Project API task contract
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

blocked_until_later_gate:
  - M1-003+ API route/service implementation before M1-002 is complete
  - frontend screen implementation beyond bootstrap API helpers
  - worker/training/eval/export runtime implementation
  - milestone review bundles
  - CTO decision artifacts
```

## 6. Next Work

```yaml
immediate:
  - stage explicit M1-002 files
  - commit and push M1-002
  - create a scoped M1-003 Project API task contract before editing API route/service files

do_not_start_without:
  - explicit user task or approved gate packet
  - relevant SSOT/spec sections
  - clear file scope
  - M1-001 allowed_edit_paths and verification commands
  - verification plan for phase closeout commit/push
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. Day-0 Bootstrap readiness and M1-001
API bootstrap have both been committed and pushed. M1-002 DB migration + seed is
implemented and verified. Finish closeout by ensuring the M1-002 commit is
pushed, then create a scoped M1-003 Project API task contract before editing API
route/service files. Do not start FE screens, worker, training, eval, export, or
teacher runtime work before the proper gate. Use .venv for Python work.
```
