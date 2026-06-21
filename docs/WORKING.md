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
phase_id: STRICT_MODEL_CACHE_EVIDENCE
milestone: M6_RC_Blocker_Evidence
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-strict-model-cache-runtime-evidence
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
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-strict-model-cache-runtime-evidence
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: determine whether strict Gemma cache can be used for exported Docker endpoint evidence
  evidence:
    strict_model_cache: artifacts/review/strict_model_cache_evidence.md
    docker_runtime_remediation: artifacts/review/docker_runtime_remediation_evidence.md
  summary:
    - strict model catalog verification passed with errors=[]
    - required Gemma cache subdir is google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad
    - local searches found no matching strict cache and no Hugging Face cache directory
    - only fake 0000... fixture caches were found under /tmp and must not be used as evidence
    - HF_TOKEN, HUGGING_FACE_HUB_TOKEN, HUGGINGFACE_TOKEN, HF token files, and netrc are absent
    - network HEAD request to Gemma config returned HTTP 401 GatedRepo
    - model_cache.ensure_model in offline mode returns MODEL_CACHE_MISS_OFFLINE with all five required files missing
    - endpoint success transcripts remain blocked by missing authenticated Gemma access or user-provided strict cache
    - no product code, model catalog, runtime, loader, API, DB, FE, benchmark, or release sign-off files were changed

m6_previous_work:
  docker_runtime_remediation: caf9c0f
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
status: strict_model_cache_access_blocked
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
  - local search for matching Gemma cache root
  - HF credential presence check without printing secrets
  - MIB_OFFLINE=1 model_cache.ensure_model miss check
  - network HEAD check to Gemma config returned authenticated-gated response
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO until strict model cache exists and endpoint transcripts pass in a scoped re-review
  - /healthz success, /agents/{agent_id}/run success, and /v1/chat/completions success are not proven
  - Gemma requires authenticated HF access with accepted terms, or an externally supplied strict cache
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
  Strict_Model_Catalog_Verified: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Endpoint_Success_With_Strict_Model_Cache: true
  Strict_Gemma_Model_Cache_Available: true

active_gate:
  id: none
  cto_decision: waiting_for_authenticated_gemma_access_or_user_supplied_strict_cache
  review_bundle: artifacts/review/strict_model_cache_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: provide strict Gemma cache, rerun Docker runtime endpoint transcripts, then rerun M6-RC sign-off
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers:
  - no HF token or local HF credential exists in this environment
  - Hugging Face returns HTTP 401 GatedRepo for google/gemma-2b-it without authentication
  - no strict external Gemma cache root is present

security_deferred:
  - cuda pip-audit ignores upstream-blocked training dependency advisories under the existing project exception policy
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports newer safe transitive dependency versions or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - materialize google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad outside repo with exact strict catalog hashes
  - successful /healthz transcript with strict model cache
  - successful /agents/{agent_id}/run transcript with strict model cache
  - successful /v1/chat/completions transcript with strict model cache
  - M6-RC re-review after endpoint runtime evidence is complete
```

## 6. Next Work

```yaml
immediate:
  - get an HF token for an account that accepted google/gemma-2b-it terms, or provide a prebuilt strict cache root
  - create a scoped PABCD contract for cache materialization and endpoint evidence
  - run services.worker.model_cache.ensure_model for google/gemma-2b-it cuda runtime_evidence with the cache outside git
  - mount the cache root read-only into the remediated Docker image
  - capture /healthz, /agents/{agent_id}/run, and /v1/chat/completions transcripts
  - rerun M6-RC sign-off only after endpoint runtime evidence passes
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. FE v6 mockup is committed at d7a68bf.
Docker runtime import/image-tar scan remediation is committed at caf9c0f. Strict
model cache evidence is in artifacts/review/strict_model_cache_evidence.md.
M6-RC remains NOT_GO because the environment has no authenticated Gemma access
and no strict cache root. Do not fake cache files or claim endpoint success.
Next work requires HF_TOKEN/HUGGING_FACE_HUB_TOKEN/HUGGINGFACE_TOKEN for an
account with accepted google/gemma-2b-it terms, or a user-provided cache root
containing google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad with
strict catalog hashes. Use .venv for Python.
```
