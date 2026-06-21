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
phase_id: M4_003_BENCHMARK_REPORT
milestone: M4_Benchmark
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m4-003-benchmark-report
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
    command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
    status: passed
    note: bootstrap_dev.sh auto-prefers /tmp/mib-toolchain when present; skip-install records pip-audit as skipped if network-backed audit cannot complete
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-m4-003-benchmark-report
  implementation_commit: 5c3d3e7
  pushed_to_origin_main: true
  objective: implement M4-003 Benchmark report generation, hash verification, and benchmark read API
  summary:
    - added Benchmark DTOs, routes, service, and registered the OpenAPI-backed benchmark read/report endpoints
    - added report generation from terminal EvalRun rows with committed JSON Schema validation and canonical report_sha256 storage
    - completed targets aggregate seed mean, sample SD, and 95% CI for Router metrics, latency, cost, and effective cost
    - local_large SKIPPED_OPTIONAL reports seeds [0] and skip_reason without metric objects; report hash recompute returns VALID, MISMATCH, or MISSING
    - CUDA/MLX fine_tuned parity records PASS, FAIL, or NA from metric threshold checks; focused tests cover valid report, tamper mismatch, and parity FAIL

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

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m4_003_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/api/app/main.py services/api/app/routes/benchmarks.py services/api/app/schemas/benchmark.py services/api/app/services/benchmark_metrics.py services/api/app/services/benchmark_report.py services/api/app/services/benchmark_service.py tests/eval/test_benchmark_report.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/eval/test_benchmark_report.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/eval/test_eval_runner.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - git diff --check
  - git diff --cached --check
warnings:
  - focused benchmark report pytest emits existing FastAPI ORJSONResponse deprecation warnings
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

active_gate:
  id: none
  cto_decision: ready_for_m5_001_scoped_contract
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M5-001 Agent contract builder
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M5 AgentPackage contract builder work
  - DB schema/model/migration changes unless explicitly required by the next scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for M5-001 Agent contract builder
  - read docs/handoffs/M5.md and docs/specs/IMPLEMENTATION_GUIDE.md M5-001 sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, M3-001, M3-002
CUDA wrapper, M3-003 MLX wrapper, M3-004 Cancel/resume, M3-005 Dry-run + OOM
isolation, M4-001 Eval set freeze hardening, M4-002 Eval runner, and M4-003
Benchmark report are committed and pushed. Do not start M5-001 until a new scoped PABCD
task contract is created. Use .venv for
Python, COREPACK_HOME=/tmp/corepack, and COREPACK_DEFAULT_TO_LATEST=0 for bootstrap checks.
```
