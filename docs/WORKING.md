# MIB Studio Working State

```yaml
doc_type: llm_operational_handoff
audience: llm_agents_only
purpose: read_before_each_task
format: machine_scannable_markdown_with_yaml_blocks
rule: keep_only_current_work_next_work_blockers_and_verification
ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
context: docs/CONTEXT.md
```

## 0. Agent Instructions

```yaml
read_policy:
  - read this file before starting work
  - read docs/CONTEXT.md for project-wide constraints
  - use docs/foundation/MIB_Studio_Dev_Plan_v0.3.md as canonical SSOT
  - use phase-specific specs only for the active task area
  - create or update .codex/tasks/current.json before edits

write_policy:
  - keep this file short and current
  - record only current phase, last completed work, next work, blockers, and verification
  - do not treat this file as a requirements source
```

## 1. Current Phase

```yaml
phase_id: V0_RELEASE_READINESS_AUDIT
milestone: M6_RC_Blocker_Remediation
phase_status: v0_release_readiness_audit_verified_not_go
active_slice: none
gate_id: mib-studio-v0-release-readiness-audit
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
  gate: mib-studio-v0-release-readiness-audit
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: add machine-readable v0 release readiness audit for final-program completion evidence and the remaining M6 real-adapter blocker
  evidence:
    v0_release_readiness_audit: artifacts/review/v0_release_readiness_audit_evidence.md
    v0_release_readiness_audit_json: artifacts/review/v0_release_readiness_audit.json
    desktop_e2e_route_repair: artifacts/review/desktop_e2e_route_repair_evidence.md
    fe_v6_evidence: artifacts/review/fe_v6_evidence.md
    m6_rc_evidence_verification: artifacts/review/m6_rc_evidence_verification.json
    real_adapter_prereq_audit: artifacts/review/real_adapter_prereq_audit_evidence.md
    real_adapter_prereq_audit_json: artifacts/review/m6_real_adapter_prereq_audit.json
  summary:
    - scripts/verify_v0_release_readiness.py now audits FE v6 evidence, desktop route repair evidence, M6-RC evidence verification, and real adapter prereq audit together
    - current v0 release readiness decision is NOT_GO, release_ready false, verification_ok true
    - current unexpected_blockers is empty
    - the only current release blocker is real_trained_adapter_no_fake_endpoint
    - current missing prereqs are adapter_dir_present, adapter_safetensors_present, adapter_config_present, adapter_manifest_present, docker_image_available, and host_cuda_visible
    - no backend, schema, training, export, runtime, UI behavior, or M6 evidence policy files changed

important_previous_commits:
  desktop_e2e_route_repair: cf2fdf5
  real_adapter_prereq_audit: ac34a7e
  real_adapter_rc_gate_runner: c26ffe4
  structured_endpoint_evidence: d3dfbc6
  real_adapter_artifact_intake: c4d0227
  real_adapter_endpoint_capture_tooling: a0d847b
  fe_v6_mockup: d7a68bf
  m6_rc_signoff: 841d620
  m6_002_docker_export: b6873f5
  m6_001_zip_export: 31971d7

do_not_start_without:
  - active PABCD task contract
  - relevant SSOT/spec sections
  - clear file scope
  - phase-specific allowed_edit_paths and verification commands
```

## 3. Verification State

```yaml
status: v0_release_readiness_audit_verified_not_go
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/verify_v0_release_readiness.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_verify_v0_release_readiness.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO
  - no real trained CUDA lora_adapter artifact was found in the repo or current /tmp artifacts
  - current host has no visible CUDA device; nvidia-smi is unavailable and torch.cuda.is_available() is false
  - previous endpoint evidence used fake backend because the temp fixture adapter is not a real trained adapter
failed: []
```

## 4. Gate State

```yaml
recorded_go:
  M0_Product_Lock: true
  M1_Final_Smoke_Verified: true
  M1_Smoke_Current_Environment: true
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
  Exported_Runtime_Real_Backend_Dependencies_Packaged: true
  Export_Adapter_Structural_Validation: true
  Export_Adapter_Lineage_Validation: true
  Exported_Runtime_Adapter_Load_Guard: true
  M6_RC_Evidence_Current_Not_Go: true
  Real_Adapter_Endpoint_Capture_Tooling: true
  Real_Adapter_Artifact_Intake_Tooling: true
  Structured_Real_Endpoint_Evidence_Tooling: true
  Real_Adapter_RC_Gate_Runner_Tooling: true
  Real_Adapter_Prereq_Audit_Tooling: true
  Desktop_E2E_Route_Repair: true
  V0_Release_Readiness_Audit: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true

last_completed_gate:
  id: mib-studio-v0-release-readiness-audit
  review_bundle: artifacts/review/v0_release_readiness_audit_evidence.md
  decision: not_go_real_trained_adapter_no_fake_endpoint

active_release_blocker:
  id: m6-real-trained-adapter-no-fake-endpoint-evidence
  cto_decision: waiting_for_real_trained_adapter_inference_evidence_or_release_policy
  next_required_check: provide/train a real CUDA lora_adapter and rerun no-fake-backend Docker endpoint transcripts, or explicitly scope release acceptance for fixture-adapter endpoint evidence
```

## 5. Blockers And Deferred Work

```yaml
operator_blockers:
  - real trained CUDA lora_adapter endpoint evidence is not yet present
  - no real trained CUDA lora_adapter artifact was found in repo or current /tmp artifacts
  - no-fake-backend endpoint transcripts are still missing after dependency packaging because no real adapter exists
  - export lineage validation cannot establish endpoint inference quality
  - Gemma remains gated without credentials, but Phi strict cache is available under /tmp/mib-strict-model-cache-phi

security_deferred:
  - cuda pip-audit ignores upstream-blocked training dependency advisories under the existing project exception policy
  - review artifacts/security/pip_audit_cuda_exceptions.json when LLaMA-Factory supports newer safe transitive dependency versions or the SSOT replaces the training wrapper
```

## 6. Next Work

```yaml
immediate:
  - provide or train a real CUDA lora_adapter with adapter.safetensors, adapter_config.json, and manifest.json
  - export or tag the matching Docker image and run on a host where nvidia-smi is available
  - rerun scripts/run_m6_real_adapter_rc_gate.py --preflight-only with the real paths until status is READY_TO_RUN
  - run scripts/run_m6_real_adapter_rc_gate.py without --preflight-only/--plan-only against the real adapter, exported Docker image, and model cache
  - rerun M6-RC sign-off only after that decision/evidence is complete
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md before edits. Use .venv for Python and
COREPACK_HOME=/tmp/corepack for frontend commands. The latest completed gate is
mib-studio-v0-release-readiness-audit. Use
scripts/verify_v0_release_readiness.py --expected-decision NOT_GO to audit the
current final-program completion state. The current JSON report is
artifacts/review/v0_release_readiness_audit.json: FE v6 and desktop route repair
evidence are present, M6-RC evidence verification is current, release_ready is
false, unexpected_blockers is empty, and the only release blocker is
real_trained_adapter_no_fake_endpoint.

Do not claim M6-RC GO. M6-RC remains NOT_GO until real trained CUDA
lora_adapter no-fake Docker endpoint evidence exists or release policy
explicitly accepts fixture-adapter endpoint evidence. Use
scripts/run_m6_real_adapter_rc_gate.py --preflight-only before any live M6-RC
attempt; current preflight is NOT_READY because the real adapter directory,
adapter files, manifest, Docker image, and host CUDA are missing.
```
