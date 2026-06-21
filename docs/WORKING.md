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
phase_id: M6_002_DOCKER_EXPORT
milestone: M6_Export_RC
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-m6-002-docker-export
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
  gate: mib-studio-m6-002-docker-export
  implementation_commit: b6873f5
  pushed_to_origin_main: true
  objective: implement M6-002 Docker local API export for CUDA/lora_adapter packages, MLX docker 409 evidence, Dockerfile security checks, and focused Docker export tests
  summary:
    - unlocked docker export submission for CUDA/lora_adapter AgentPackages while preserving zip export behavior
    - Docker export requests for MLX/mlx_lora_adapter packages return 409 DOCKER_UNAVAILABLE with export_type details
    - added services/worker/handlers/export_docker.py to create a Docker build context artifact from the same exported runtime contract
    - Docker export writes manifest.json with export_type=docker, Dockerfile, README_DOCKER.md, context tar artifact, SBOM CycloneDX evidence, and CVE evidence
    - Dockerfile.cuda now enforces digest-pinned BASE_IMAGE_WITH_DIGEST, non-root mib user, explicit port, healthcheck, external /models cache, and no baked runtime/fallback/local-daemon tokens
    - exported runtime state validates MIB_RUNTIME_BEARER_TOKEN at startup/health before serving requests
    - focused tests cover CUDA docker acceptance, MLX docker 409, Docker context artifact/secret scan/SBOM/CVE evidence, Dockerfile security, and runtime token env failures

m6_previous_work:
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

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: m6_002_verified_and_pushed
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m py_compile services/api/app/services/export_service.py services/worker/handlers/export_docker.py packages/agent-runtime/templates/zip_runtime/agents/run.py packages/agent-runtime/templates/zip_runtime/agents/security.py packages/agent-runtime/tests/test_docker_export_security.py tests/export/test_docker_export_security.py tests/export/test_exported_runtime_smoke.py tests/export/test_export_api.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest packages/agent-runtime/tests/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --self-test
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_import_boundaries.py --json-output artifacts/review/import_boundary_report.json --rules rules/code_shape.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - git diff --check
  - git diff --cached --check
warnings:
  - focused API/export tests emit existing FastAPI ORJSONResponse deprecation warnings
  - default automated Docker export test validates deterministic Docker build context tar plus SBOM/CVE evidence; real docker build/save path is implemented behind MIB_DOCKER_EXPORT_REAL_BUILD=1 and requires MIB_DOCKER_BASE_IMAGE_WITH_DIGEST
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

active_gate:
  id: none
  cto_decision: ready_for_m6_rc_signoff_contract
  review_bundle: artifacts/review

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: create scoped PABCD contract for M6-RC sign-off
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers: []

security_deferred:
  - cuda pip-audit ignores 16 upstream-blocked Gradio/Pillow/Starlette advisories because llamafactory==0.9.5 requires gradio<=5.50.0
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports Gradio 6.x or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - M6-RC sign-off evidence bundle
  - FE v6 mockup implementation
  - DB schema/model/migration changes unless explicitly required by the next scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a new scoped PABCD task contract for M6-RC sign-off
  - read docs/handoffs/M6.md and docs/specs/IMPLEMENTATION_GUIDE.md M6-RC sections before edits
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. M1, M2, M3-000, M3-001, M3-002
CUDA wrapper, M3-003 MLX wrapper, M3-004 Cancel/resume, M3-005 Dry-run + OOM
isolation, M4-001 Eval set freeze hardening, M4-002 Eval runner, M4-003
Benchmark report, M5-001 Agent contract builder, M5-002 Verifier, and M5-003
Playground, M6-001 Zip export, and M6-002 Docker export are committed and pushed.
Do not start M6-RC until a new scoped PABCD task contract is created. Use .venv
for Python and COREPACK_HOME=/tmp/corepack for bootstrap checks.
```
