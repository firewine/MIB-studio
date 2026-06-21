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
phase_id: M1_001_API_BOOTSTRAP
milestone: M1_Core
phase_status: m1_001_complete
active_slice: api_bootstrap_auth_client
gate_id: mib-studio-m1-001-api-bootstrap
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment: python_venv
venv_path: .venv
venv_gitignored: true
```

## 2. Current Work

```yaml
mode: implement
status: m1_001_complete
objective: implement M1-001 API bootstrap with local bearer auth and desktop bootstrap client
source_gate_packet: user_goal_final_program_development_docs_based_v6_fe
review_tier: focused

allowed_edit_paths:
  - docs/WORKING.md
  - .codex/tasks/current.json
  - services/api/app/main.py
  - services/api/app/core/
  - services/shared/security/
  - apps/desktop/src/lib/api.ts
  - apps/desktop/src/lib/bootstrap.ts
  - apps/desktop/src-tauri/src/bootstrap.rs
  - tests/api/
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
  - services/worker/
  - services/shared/db/
  - packages/
  - .github/
  - scripts/

changed:
  - services/api/app/main.py
  - services/api/app/core/
  - services/shared/security/
  - apps/desktop/src/lib/api.ts
  - apps/desktop/src/lib/bootstrap.ts
  - apps/desktop/src-tauri/src/bootstrap.rs
  - tests/api/test_auth_bootstrap.py
  - artifacts/review/file_size_report.json
local_uncommitted_context:
  note: Day-0 readiness phase was committed and pushed at 89b346d
  do_not_revert_without_user_request: true

result_so_far:
  - M0 is GO and M1 is authorized by the SSOT.
  - Local development environment policy is repo-local Python venv at .venv.
  - .venv is ignored by .gitignore and has been recreated with Python 3.11 for future dependency setup.
  - Day-0 Bootstrap readiness verification passed, committed, and pushed.
  - M1-001 API bootstrap is implemented and verified.
  - FastAPI now exposes /healthz, Host/Origin/CORS/body/auth middleware, standard errors, trace_id response headers, and locked future stubs.
  - Bootstrap token helpers support exactly one MIB_BOOTSTRAP line for daemon startup, and Tauri/FE helpers can pass Bearer tokens.
  - Auth tests cover healthz, missing/invalid token, Host/Origin reject, CORS preflight, body limit, token_file, bypass-in-prod rejection, bootstrap line, and locked stubs.
  - Full UI implementation remains deferred to M1-007, but FE bootstrap helpers are in scope for M1-001.
```

## 3. Verification State

```yaml
status: m1_001_complete
passed:
  - uv pip install --python .venv/bin/python fastapi==0.115.12 uvicorn==0.34.2 pydantic==2.10.6 pydantic-settings==2.8.1 httpx==0.28.1 pytest==8.3.5 pytest-asyncio==0.25.3 orjson==3.10.16
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import fastapi, pydantic, httpx, pytest; print('m1-deps-ok')"
  - ./.venv/bin/python -m py_compile services/api/app/main.py services/api/app/core/config.py services/api/app/core/errors.py services/shared/security/auth.py services/shared/security/origin.py services/shared/security/redaction.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/api/test_auth_bootstrap.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/export_openapi.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --verify-only --skip-install
  - git diff --check
failed: []
not_run:
  - corepack pnpm test: package.json intentionally defers UI tests until M1-007
  - cargo/tauri build: Tauri scaffold is intentionally deferred until M1-007
required_before_done:
  - explicit git stage, commit, and push for M1-001
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true

active_gate:
  id: mib-studio-m1-001-api-bootstrap
  cto_decision: m1_001_complete
  review_bundle:
    - tests/api/test_auth_bootstrap.py
    - artifacts/review/file_size_report.json

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: scoped M1-002 DB migration + seed task contract
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

blocked_until_later_gate:
  - M1-002+ product implementation before M1-001 is complete
  - DB migration/model/repository implementation
  - frontend screen implementation beyond bootstrap API helpers
  - worker/training/eval/export runtime implementation
  - milestone review bundles
  - CTO decision artifacts
```

## 6. Next Work

```yaml
immediate:
  - stage explicit M1-001 files
  - commit and push M1-001
  - create a scoped M1-002 DB migration + seed task contract before editing DB files

do_not_start_without:
  - explicit user task or approved gate packet
  - relevant SSOT/spec sections
  - clear file scope
  - M1-001 allowed_edit_paths and verification commands
  - verification plan for phase closeout commit/push
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. Day-0 Bootstrap readiness was
committed and pushed at 89b346d. M1-001 API bootstrap is implemented and
verified. Finish closeout by ensuring the M1-001 commit is pushed, then create a
scoped M1-002 DB migration + seed task contract before editing DB files. Do not
start FE screens, worker, training, eval, export, or M1-003+ work before the
proper gate. Use .venv for Python work.
```
