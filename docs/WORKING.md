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
phase_id: M1_DEVELOPMENT_PREP
milestone: M1_Core
phase_status: day0_readiness_complete
active_slice: day0_bootstrap_readiness
gate_id: mib-studio-day0-readiness-audit
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment: python_venv
venv_path: .venv
venv_gitignored: true
```

## 2. Current Work

```yaml
mode: audit
status: day0_readiness_complete
objective: verify Day-0 Bootstrap readiness before starting M1-001 API bootstrap
source_gate_packet: user_goal_final_program_development_docs_based_v6_fe
review_tier: none

allowed_edit_paths:
  - docs/WORKING.md
  - artifacts/review/
  - artifacts/security/
  - .codex/tasks/current.json
blocked_edit_paths:
  - app/
  - backend/
  - frontend/
  - scripts/
  - tests/
  - alembic/
  - .github/

changed: []
local_uncommitted_context:
  note: repository may contain setup/documentation files from prior bootstrap work
  do_not_revert_without_user_request: true

result_so_far:
  - M0 is GO and M1 is authorized by the SSOT.
  - Local development environment policy is repo-local Python venv at .venv.
  - .venv is ignored by .gitignore and has been recreated with Python 3.11 for future dependency setup.
  - Day-0 Bootstrap readiness verification passed with non-strict toolchain mismatches recorded.
  - Bootstrap verifier was repaired to use Python sqlite3 during scaffold verification instead of requiring a system sqlite3 CLI.
  - Product code implementation has not started from this handoff.
  - Verified phase closeout should stage explicit files, commit, and push.
```

## 3. Verification State

```yaml
status: day0_readiness_complete
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - test -d .venv
  - test -f docs/CONTEXT.md
  - test -f docs/WORKING.md
  - PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --verify-only --skip-install
  - git diff --check
failed: []
not_run: []
required_before_done:
  - explicit git stage, commit, and push for the completed phase
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Authorized: true

active_gate:
  id: mib-studio-day0-readiness-audit
  cto_decision: day0_readiness_complete
  review_bundle: artifacts/review/toolchain_report.json

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: false
  next_required_check: scoped M1-001 API bootstrap task contract
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

blocked_until_later_gate:
  - M1-002+ product implementation before M1-001 is complete
  - DB migration/model/repository implementation
  - frontend screen implementation
  - worker/training/eval/export runtime implementation
  - milestone review bundles
  - CTO decision artifacts
```

## 6. Next Work

```yaml
immediate:
  - run final closeout verification for this Day-0 readiness phase
  - stage explicit changed files for the completed phase
  - commit and push the completed phase
  - create a scoped M1-001 API bootstrap task contract before product code edits

do_not_start_without:
  - explicit user task or approved gate packet
  - relevant SSOT/spec sections
  - clear file scope
  - M1-001 allowed_edit_paths and verification commands
  - verification plan for phase closeout commit/push
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1 development is authorized and
Day-0 Bootstrap readiness verification has passed in scaffold verify-only mode.
Product code has not started. Close out the Day-0 readiness phase by running
verification, staging explicit files, committing, and pushing. Then scope
M1-001 API bootstrap only. Do not jump to later M1 tickets. Use .venv for Python
work.
```
