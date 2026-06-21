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
phase_id: REAL_ADAPTER_INFERENCE_EVIDENCE
milestone: M6_RC_Blocker_Remediation
phase_status: real_adapter_evidence_blocker_recorded
active_slice: none
gate_id: mib-studio-real-adapter-inference-evidence
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
status: no_active_product_code_work
objective: none
source_gate_packet: .codex/tasks/current.json
review_tier: none

last_completed_work:
  gate: mib-studio-real-adapter-inference-evidence
  implementation_commit: pending_commit
  closeout_commit: pending_commit
  pushed_to_origin_main: pending
  objective: verify whether M6-RC can close with real trained CUDA lora_adapter inference evidence
  evidence:
    real_adapter: artifacts/review/real_adapter_inference_evidence.md
    phi_runtime: artifacts/review/phi_strict_cache_runtime_evidence.md
    gemma_cache_blocker: artifacts/review/strict_model_cache_evidence.md
    docker_runtime_remediation: artifacts/review/docker_runtime_remediation_evidence.md
  summary:
    - searched repo and /tmp for adapter.safetensors, adapter_config.json, adapter_model.safetensors, and adapter_model.bin
    - only 12-byte fixture adapter.safetensors and 26-byte fixture adapter_config.json files were found
    - no real trained CUDA lora_adapter artifact was found
    - nvidia-smi is not installed or visible on this host
    - llamafactory-cli is not on PATH, although relevant Python modules exist in .venv
    - exported Phi Docker image lacks torch, transformers, peft, safetensors, accelerate, and bitsandbytes
    - no-fake-backend /healthz returned HTTP 500 with TRANSFORMERS_BACKEND_UNAVAILABLE caused by missing peft
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
status: real_adapter_inference_blocked
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - adapter artifact search across /home/firewine/MIB-studio and /tmp
  - hardware/tooling checks for nvidia-smi and llamafactory-cli
  - .venv import availability check for torch/transformers/peft/bitsandbytes/llamafactory/accelerate/safetensors
  - Docker image import availability check for torch/transformers/peft/safetensors/accelerate/bitsandbytes
  - Docker run without MIB_RUNTIME_ALLOW_FAKE_BACKEND reached runtime loader and failed with TRANSFORMERS_BACKEND_UNAVAILABLE
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/verify_model_catalog.py --catalog presets/model_catalog.yaml --no-download --json-output artifacts/security/model_manifest_strict_report.json
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO
  - no real trained CUDA lora_adapter artifact was found
  - current exported Docker image does not include real transformers/peft runtime dependencies
  - previous endpoint evidence used fake backend because the temp fixture adapter is not a real trained adapter
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
  Real_Adapter_Evidence_Search_Completed: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true
  Exported_Runtime_Real_Backend_Dependencies: true

active_gate:
  id: mib-studio-real-adapter-inference-evidence
  cto_decision: waiting_for_real_trained_adapter_inference_evidence_or_release_policy
  review_bundle: artifacts/review/real_adapter_inference_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
  next_required_check: provide/train a real CUDA lora_adapter and package real backend dependencies into Docker, or explicitly scope release acceptance for fixture-adapter endpoint evidence
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers:
  - real trained CUDA lora_adapter endpoint evidence is not yet present
  - no real trained CUDA lora_adapter artifact was found in repo or current /tmp artifacts
  - exported Docker runtime image lacks peft/transformers/torch/safetensors for real adapter loading
  - fake-backend-disabled /healthz currently fails with TRANSFORMERS_BACKEND_UNAVAILABLE
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
  - decide whether to run/provide a real CUDA training artifact or change release policy for v0 RC
  - if real adapter evidence is still required, add/export real backend dependencies and rerun no-fake-backend Docker endpoints
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
real trained adapter. Real adapter evidence is recorded in
artifacts/review/real_adapter_inference_evidence.md: no real trained adapter was
found, nvidia-smi is unavailable, and the exported image fails /healthz without
fake backend due TRANSFORMERS_BACKEND_UNAVAILABLE from missing peft. M6-RC
remains NOT_GO until real trained adapter inference evidence exists or the
release policy explicitly accepts fixture-adapter endpoint evidence. Use .venv
for Python.
```
