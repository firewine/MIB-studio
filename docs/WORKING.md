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
phase_id: M1_003_PROJECT_API
milestone: M1_Core
phase_status: m1_003_complete
active_slice: project_api_crud_archive_guard
gate_id: mib-studio-m1-003-project-api
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment: python_venv
venv_path: .venv
venv_gitignored: true
```

## 2. Current Work

```yaml
mode: implement
status: m1_003_complete
objective: implement M1-003 Project API CRUD and archive guards
source_gate_packet: user_goal_final_program_development_docs_based_v6_fe
review_tier: focused

allowed_edit_paths:
  - docs/WORKING.md
  - .codex/tasks/current.json
  - .gitignore
  - services/api/app/main.py
  - services/api/app/core/config.py
  - services/api/app/core/errors.py
  - services/api/app/routes/
  - services/api/app/schemas/
  - services/api/app/services/
  - tests/api/test_auth_bootstrap.py
  - tests/api/test_projects.py
  - schemas/openapi.json
  - apps/desktop/src/lib/generated.ts
  - artifacts/review/
  - artifacts/security/
blocked_edit_paths:
  - docs/specs/
  - docs/foundation/
  - docs/mockup/
  - docs/handoffs/
  - docs/reviews/
  - services/shared/db/models/
  - services/shared/db/migrations/
  - services/worker/
  - packages/
  - apps/desktop/src/features/
  - apps/desktop/src/pages/
  - .github/
  - scripts/

changed:
  - .gitignore
  - services/api/app/core/config.py
  - services/api/app/core/errors.py
  - services/api/app/main.py
  - services/api/app/routes/
  - services/api/app/schemas/
  - services/api/app/services/
  - tests/api/test_auth_bootstrap.py
  - tests/api/test_projects.py
  - schemas/openapi.json
  - apps/desktop/src/lib/generated.ts
  - artifacts/review/file_size_report.json
local_uncommitted_context:
  note: M1-002 DB migration + seed was committed and pushed at 1020a90
  do_not_revert_without_user_request: true

result_so_far:
  - M0 is GO and M1 is authorized by the SSOT.
  - Local development environment policy is repo-local Python venv at .venv.
  - .venv is ignored by .gitignore and has been recreated with Python 3.11 for future dependency setup.
  - Day-0 Bootstrap readiness verification passed, committed, and pushed.
  - M1-001 API bootstrap is implemented, verified, committed, and pushed.
  - FastAPI now exposes /healthz, Host/Origin/CORS/body/auth middleware, standard errors, trace_id response headers, and locked future stubs.
  - Bootstrap token helpers support exactly one MIB_BOOTSTRAP line for daemon startup, and Tauri/FE helpers can pass Bearer tokens.
  - M1-002 DB migration + seed is implemented, verified, committed, and pushed.
  - SQLAlchemy metadata now covers the ARCHITECTURE section 24.2 canonical SQLite schema and indexes.
  - Alembic upgrade/downgrade, FK/integrity checks, router.basic.v1 seed, model_catalog load, and critical partial unique constraints are covered by tests/db.
  - M1-003 Project API is implemented and verified.
  - Project CRUD, preset existence check, route count/duplicate validation, include_archived list behavior, soft archive, archived mutation guard, and route taxonomy lock are covered by tests.
  - .gitignore may be repaired only to keep the default local sqlite runtime file out of git.
```

## 3. Verification State

```yaml
status: m1_003_complete
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - test -d .venv
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import fastapi, sqlalchemy, pydantic, httpx, pytest; print('m1-project-deps-ok')"
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile services/api/app/core/config.py services/api/app/core/errors.py services/api/app/main.py services/api/app/schemas/project.py services/api/app/services/project_service.py services/api/app/routes/projects.py tests/api/test_projects.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/api/test_auth_bootstrap.py tests/db tests/api/test_projects.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --verify-only --skip-install
  - git diff --check
failed: []
not_run: []
required_before_done:
  - explicit git stage, commit, and push for M1-003
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true

active_gate:
  id: mib-studio-m1-003-project-api
  cto_decision: m1_003_complete
  review_bundle:
    - tests/api/test_projects.py
    - artifacts/review/file_size_report.json

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: scoped M1-004 Preset API task contract
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

blocked_until_later_gate:
  - M1-004+ endpoint implementation before M1-003 is complete
  - frontend screen implementation beyond bootstrap API helpers
  - worker/training/eval/export runtime implementation
  - milestone review bundles
  - CTO decision artifacts
```

## 6. Next Work

```yaml
immediate:
  - stage explicit M1-003 files
  - commit and push M1-003
  - create a scoped M1-004 Preset API task contract before editing preset API files

do_not_start_without:
  - explicit user task or approved gate packet
  - relevant SSOT/spec sections
  - clear file scope
  - M1-001 allowed_edit_paths and verification commands
  - verification plan for phase closeout commit/push
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. Day-0 Bootstrap readiness, M1-001 API
bootstrap, M1-002 DB migration + seed, and M1-003 Project API have been
implemented, verified, committed/pushed except for the current M1-003 closeout
commit if it has not yet happened. Finish closeout, then create a scoped M1-004
Preset API task contract before editing preset API files. Do not start FE
screens, worker, training, eval, export, or teacher runtime work before the
proper gate. Use .venv for Python work.
```
