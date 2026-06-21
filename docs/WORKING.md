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
phase_id: DOCKER_RUNTIME_REMEDIATION
milestone: M6_RC_Blocker_Remediation
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-docker-runtime-evidence-remediation
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  gitignored:
    - .venv/
  frontend_package_manager: cached pnpm 9.15.0 via strict Node
  corepack_home: /tmp/corepack
  strict_toolchain_path:
    node: /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin
    rustc: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/rustc/bin
    cargo: /tmp/mib-toolchain/rust-1.83.0-x86_64-unknown-linux-gnu/cargo/bin
  last_bootstrap_smoke:
    command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
    status: passed
    note: toolchain versions passed; cuda pip-audit was skipped by project policy and recorded under artifacts/security
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-docker-runtime-evidence-remediation
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: fix real Docker runtime import and image-tar scan blockers, then restore the m1-smoke Route contract guard
  evidence:
    previous_blocker_evidence: artifacts/review/docker_runtime_evidence.md
    remediation_evidence: artifacts/review/docker_runtime_remediation_evidence.md
  summary:
    - Dockerfile.cuda now sets PYTHONPATH=/app/runtime so uvicorn agents.run:app imports inside the image
    - scan_export_artifact.py now validates Docker image tar manifest.json lists separately from MIB export manifest objects
    - Docker export test now validates context tar structure in default mode and image tar structure in real-build mode
    - desktop main.mjs restores exact Route contract smoke text expected by m1-smoke
    - real Docker build/save passed with digest-pinned getbeta-backend base image
    - remediated container starts Uvicorn and imports agents.run successfully
    - endpoint success remains blocked by missing strict external model cache; no M6-RC GO was claimed

m6_previous_work:
  docker_runtime_evidence_not_go: 860f5d6
  fe_v6_mockup: d7a68bf
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
  m3_002_cuda_wrapper: e8c8fc9
  m3_001_training_preflight: c52a76e
  m3_000_model_cache_service: c683a2b

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: docker_runtime_remediation_verified
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest packages/agent-runtime/tests/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --self-test
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/check_file_size.py --config rules/code_shape.json --json-output artifacts/review/file_size_report.json --fail-on-hard-limit
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - MIB_DOCKER_EXPORT_REAL_BUILD=1 MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --artifact <saved-image-tar> --sbom <sbom> --cve-report <cve-report> --require-docker-evidence
  - docker run remediated image with read-only empty /models mount
  - docker exec remediated container python -c "import agents.run"
  - curl -i http://127.0.0.1:18081/healthz
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO until strict model cache exists and endpoint transcripts pass in a scoped re-review
  - /healthz currently returns HTTP 500 with RuntimeError MODEL_CACHE_MISSING: config.json when /models is empty
  - file_size_report has existing soft warnings only; no hard file-size violations remain
  - cuda pip-audit remains skipped by project policy because upstream CUDA training dependency constraints still apply
failed: []
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Final_Smoke_Verified: true
  M2_000_to_M2_004_Verified: true
  M3_000_to_M3_005_Verified: true
  M4_001_to_M4_003_Verified: true
  M5_001_to_M5_003_Verified: true
  M6_001_Verified: true
  M6_002_Verified: true
  FE_V6_Mockup_Verified: true
  Docker_Runtime_Import_And_ImageTarScan_Remediated: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Endpoint_Success_With_Strict_Model_Cache: true

active_gate:
  id: none
  cto_decision: ready_for_strict_model_cache_provisioning_then_runtime_endpoint_evidence_and_m6_rc_rereview
  review_bundle: artifacts/review/docker_runtime_remediation_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: provide strict Gemma cache, rerun Docker runtime endpoint transcripts, then rerun M6-RC sign-off
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers:
  - strict external model cache is missing under a read-only MIB_MODEL_CACHE_DIR mount

security_deferred:
  - cuda pip-audit ignores upstream-blocked training dependency advisories under the existing project exception policy
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports newer safe transitive dependency versions or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - successful /healthz transcript with strict model cache
  - successful /agents/{agent_id}/run transcript with strict model cache
  - successful /v1/chat/completions transcript with strict model cache
  - M6-RC re-review after endpoint runtime evidence is complete
  - DB schema/model/migration changes unless explicitly required by a scoped gate
  - spec/foundation/mockup/handoff/review edits
```

## 6. Next Work

```yaml
immediate:
  - create a scoped PABCD contract for strict model cache provisioning or discovery
  - mount the required Gemma cache read-only at MIB_MODEL_CACHE_DIR
  - rerun the remediated Docker image and capture /healthz, /agents/{agent_id}/run, and /v1/chat/completions transcripts
  - rerun M6-RC sign-off after endpoint runtime evidence is complete
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. The FE v6 mockup is committed at
d7a68bf. Real Docker evidence at 860f5d6 found NOT_GO blockers. The current
remediation fixed Docker agents.run import and saved Docker image tar scanning,
and evidence is in artifacts/review/docker_runtime_remediation_evidence.md.
M6-RC remains NOT_GO because strict external Gemma model cache is still missing;
do not claim endpoint success until /healthz, /agents/{agent_id}/run, and
/v1/chat/completions pass with a read-only MIB_MODEL_CACHE_DIR mount. Use .venv
for Python. Frontend commands should use the cached strict Node/pnpm toolchain
recorded above.
```
