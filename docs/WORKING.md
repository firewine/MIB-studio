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
phase_id: M6_RC_SIGNOFF
milestone: M6_Export_RC
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m6-rc-signoff
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  frontend_package_manager: corepack pnpm
  corepack_home: /tmp/corepack
  strict_toolchain_path:
    node: /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin
    rustc: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin
    cargo: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin
  last_bootstrap_smoke:
    command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --skip-install --verify-only
    status: passed
    note: scaffold verify-only records toolchain_report.strict=false by design; skip-install records pip-audit as skipped if isolated pip upgrade cannot complete
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-m6-rc-signoff
  signoff_commit: 841d620
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: create M6-RC evidence bundle and CTO decision from current M6 export evidence
  summary:
    - recorded FE, DB, BE/API, LLM/Training, Eval/QC, Security, Architecture/Code Quality, and DevEx review files under docs/reviews/M6
    - recorded M6 export evidence from M6-001 and M6-002 without changing product code or specs
    - CTO decision is NOT_GO for v0 RC because FE v6 mockup implementation evidence is missing
    - Security and DevEx are also NOT_GO until real digest-pinned Docker image build/save/run evidence is collected
    - next implementation gate must be FE v6 mockup application, not another sign-off pass

m6_previous_work:
  m6_rc_signoff: 841d620
  m6_002_docker_export: b6873f5
  m6_001_zip_export: 31971d7

m5_previous_work:
  m5_003_playground: 269a63a
  m5_002_verifier: c311e4d
  m5_001_agent_contract_builder: 614184b

m4_previous_work:
  m4_003_benchmark_report: 5c3d3e7
  m4_002_eval_runner: ff058d1
  m4_001_eval_set_freeze: e51f197

m3_previous_work:
  m3_005_dry_run_oom_isolation: 5c0fd10
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
  m3_005_dry_run_oom_isolation: 5c0fd10
  m4_001_eval_set_freeze: e51f197
  m4_002_eval_runner: ff058d1
  m4_003_benchmark_report: 5c3d3e7
  m5_001_agent_contract_builder: 614184b
  m5_002_verifier: c311e4d
  m5_003_playground: 269a63a
  m6_001_zip_export: 31971d7
  m6_002_docker_export: b6873f5
  m6_rc_signoff: 841d620

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m6_rc_signoff_verified_not_go
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase scaffold --skip-install --verify-only
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest packages/agent-runtime/tests/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --self-test
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision is NOT_GO, not GO
  - FE v6 mockup implementation evidence is missing
  - real digest-pinned Docker image build/save/run transcript evidence is missing
  - tests/export emits existing FastAPI ORJSONResponse deprecation warnings
  - bootstrap scaffold verify-only records toolchain_report.strict=false by design
  - file_size_report has existing soft warnings only; no hard file-size violations remain
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
  M3_002_Verified: true
  M3_003_Verified: true
  M3_004_Verified: true
  M3_005_Verified: true
  M4_001_Verified: true
  M4_002_Verified: true
  M4_003_Verified: true
  M5_001_Verified: true
  M5_002_Verified: true
  M5_003_Verified: true
  M6_001_Verified: true
  M6_002_Verified: true

recorded_not_go:
  M6_RC_Signoff: true

active_gate:
  id: none
  cto_decision: m6_rc_not_go
  review_bundle: docs/reviews/M6

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for FE v6 mockup implementation
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - FE v6 mockup implementation
  - real digest-pinned Docker image build/save/run evidence
  - M6-RC re-review after FE v6 and Docker runtime evidence are complete
  - DB schema/model/migration changes unless explicitly required by a scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for FE v6 mockup implementation
  - read docs/CONTEXT.md, docs/foundation/MIB_Studio_Dev_Plan_v0.3.md, docs/mockup, and relevant frontend app files before edits
  - after FE v6 is verified, collect real Docker image evidence and rerun M6-RC sign-off
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, M3-001, M3-002
CUDA wrapper, M3-003 MLX wrapper, M3-004 Cancel/resume, M3-005 Dry-run + OOM
isolation, M4-001 Eval set freeze hardening, M4-002 Eval runner, M4-003
Benchmark report, M5-001 Agent contract builder, M5-002 Verifier, and M5-003
Playground, M6-001 Zip export, and M6-002 Docker export are committed and pushed.
M6-RC sign-off evidence is recorded at 841d620 with final CTO decision NOT_GO.
Do not rerun sign-off as GO until FE v6 mockup implementation and real
digest-pinned Docker image build/save/run evidence are complete. Next work is a
new scoped FE v6 implementation PABCD. Use .venv for Python and
COREPACK_HOME=/tmp/corepack for bootstrap checks.
```
