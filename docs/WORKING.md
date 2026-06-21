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
phase_id: PHI_STRICT_CACHE_RUNTIME_EVIDENCE
milestone: M6_RC_Blocker_Remediation
phase_status: pushed_complete
active_slice: none
gate_id: mib-studio-phi-strict-cache-runtime-evidence
commit_policy: stage_commit_push_after_verified_phase_completion
dev_environment:
  python: .venv
  gitignored:
    - .venv/
  frontend_package_manager: cached pnpm 9.15.0 via strict Node
  corepack_home: /tmp/corepack
```

## 2. Current Work

```yaml
mode: none
status: no_active_work
objective: none
source_gate_packet: none
review_tier: none

last_completed_work:
  gate: mib-studio-phi-strict-cache-runtime-evidence
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: use accessible locked Phi model to prove strict-cache Docker endpoint path after Gemma access was blocked
  evidence:
    phi_runtime: artifacts/review/phi_strict_cache_runtime_evidence.md
    gemma_cache_blocker: artifacts/review/strict_model_cache_evidence.md
    docker_runtime_remediation: artifacts/review/docker_runtime_remediation_evidence.md
  summary:
    - Phi pinned config HEAD returned HTTP 200 with expected repo commit
    - strict Phi cache materialized under /tmp/mib-strict-model-cache-phi and offline cache-hit verification passed
    - Phi-based Docker export image built/saved from a temp product-path fixture package
    - image tar secret scan/SBOM/CVE evidence passed with findings=[]
    - Docker run used read-only /models mount with RW=false
    - /healthz returned 200
    - /agents/eval_runner_project.v1/run returned 200 and verifier_status PASS
    - /v1/chat/completions returned 200 with equivalent assistant JSON
    - endpoint evidence used MIB_RUNTIME_ALLOW_FAKE_BACKEND=1 because the fixture AgentPackage adapter is not a real trained adapter
    - M6-RC remains NOT_GO until real trained adapter inference evidence or an explicit release policy accepts fixture-adapter endpoint evidence

m6_previous_work:
  strict_gemma_cache_blocker: 57353ef
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
status: phi_strict_cache_endpoint_path_verified_with_fixture_adapter
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
  - Phi config HEAD request to pinned HF revision returned HTTP 200
  - Phi strict cache materialization through services.worker.model_cache.ensure_model
  - MIB_OFFLINE=1 Phi cache-hit verification
  - Phi Docker build/save via run_docker_export_job
  - scripts/scan_export_artifact.py --artifact <phi-image-tar> --sbom <sbom> --cve-report <cve> --require-docker-evidence
  - docker run with /tmp/mib-strict-model-cache-phi/model_cache:/models:ro
  - docker inspect mount RW=false
  - curl -i /healthz returned 200
  - curl -i /agents/eval_runner_project.v1/run returned 200
  - curl -i /v1/chat/completions returned 200
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO
  - endpoint evidence used fake backend because the temp fixture adapter is not a real trained adapter
  - Gemma remains blocked without authenticated HF access or a user-provided Gemma strict cache
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
  Phi_Strict_Cache_Materialized: true
  Phi_Docker_Endpoint_Path_With_Fixture_Adapter: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true

active_gate:
  id: none
  cto_decision: waiting_for_real_trained_adapter_inference_evidence_or_release_policy
  review_bundle: artifacts/review/phi_strict_cache_runtime_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: produce real trained adapter endpoint evidence or explicitly scope release acceptance for fixture-adapter endpoint evidence
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers:
  - real trained CUDA lora_adapter endpoint evidence is not yet present
  - Gemma remains gated without credentials, but Phi strict cache is available under /tmp/mib-strict-model-cache-phi

security_deferred:
  - cuda pip-audit ignores upstream-blocked training dependency advisories under the existing project exception policy
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports newer safe transitive dependency versions or the SSOT replaces the training wrapper

blocked_until_new_gate:
  - successful Docker endpoint transcripts without MIB_RUNTIME_ALLOW_FAKE_BACKEND if real adapter evidence is required
  - M6-RC re-review after endpoint runtime evidence policy is satisfied
```

## 6. Next Work

```yaml
immediate:
  - create scoped PABCD for real adapter inference evidence or release-policy review
  - inspect whether an existing training artifact can provide a real CUDA lora_adapter
  - if no real adapter exists, decide whether fixture-adapter endpoint evidence is acceptable for current v0 RC or whether a real train job must be run
  - rerun M6-RC sign-off only after that decision/evidence is complete
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md. FE v6 mockup is committed at d7a68bf.
Docker runtime import/image-tar scan remediation is committed at caf9c0f. Gemma
strict cache is blocked by gated unauthenticated access. Phi strict cache was
materialized outside the repo and Phi Docker endpoint path evidence is recorded
in artifacts/review/phi_strict_cache_runtime_evidence.md. The endpoints passed
with MIB_RUNTIME_ALLOW_FAKE_BACKEND=1 because the temp fixture adapter is not a
real trained adapter. M6-RC remains NOT_GO until real trained adapter inference
evidence exists or the release policy explicitly accepts fixture-adapter endpoint
evidence. Use .venv for Python.
```
