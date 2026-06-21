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
phase_id: EXPORTED_ADAPTER_LOAD_GUARD
milestone: M6_RC_Blocker_Remediation
phase_status: adapter_load_guard_verified
active_slice: none
gate_id: mib-studio-exported-adapter-load-guard
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
  gate: mib-studio-exported-adapter-load-guard
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: close the M6 exported adapter-load acceptance test gap
  evidence:
    exported_adapter_load_guard: artifacts/review/exported_adapter_load_guard_evidence.md
    m1_smoke_recertification: artifacts/review/m1_smoke_recertification_evidence.md
    toolchain_report: artifacts/review/toolchain_report.json
    file_size_report: artifacts/review/file_size_report.json
    pip_audit_cuda: artifacts/security/pip_audit_cuda.json
  related_m6_evidence:
    export_adapter_lineage: artifacts/review/export_adapter_lineage_evidence.md
    export_adapter_validation: artifacts/review/export_adapter_validation_evidence.md
    docker_real_backend_deps: artifacts/review/docker_real_backend_deps_evidence.md
    real_adapter: artifacts/review/real_adapter_inference_evidence.md
    phi_runtime: artifacts/review/phi_strict_cache_runtime_evidence.md
    gemma_cache_blocker: artifacts/review/strict_model_cache_evidence.md
    docker_runtime_remediation: artifacts/review/docker_runtime_remediation_evidence.md
  summary:
    - tests/export/test_exported_adapter_load.py now guards M6 adapter-load acceptance
    - fake backend behavior requires explicit MIB_RUNTIME_ALLOW_FAKE_BACKEND opt-in
    - native and OpenAI exported runtime routes are tested to invoke the loaded adapter object
    - Transformers and MLX metadata-only adapter objects are tested to fail without loaded backend objects
    - exported runtime smoke and package/playground/export parity tests still pass
    - no real trained CUDA lora_adapter artifact is still available in this environment
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
status: adapter_load_guard_verified
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_adapter_load.py -q
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_exported_runtime_smoke.py tests/export/test_package_playground_export_output_parity.py -q
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO
  - no real trained CUDA lora_adapter artifact was found
  - current host has no visible CUDA device; nvidia-smi is unavailable and torch.cuda.is_available() is false
  - adapter-load guard tests prove invocation/failure behavior but do not prove real endpoint inference quality
  - m1-smoke --skip-install records pip-audit cuda as skipped; run without --skip-install for full network-backed audit
  - file_size_report records soft LOC warnings including services/worker/handlers/export.py, with no hard failures
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

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true

active_gate:
  id: mib-studio-exported-adapter-load-guard
  cto_decision: waiting_for_real_trained_adapter_inference_evidence_or_release_policy
  review_bundle: artifacts/review/exported_adapter_load_guard_evidence.md

known_project_state:
  ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  context: docs/CONTEXT.md
  current_product_work_started: true
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

blocked_until_new_gate:
  - successful Docker endpoint transcripts without MIB_RUNTIME_ALLOW_FAKE_BACKEND if real adapter evidence is required
  - M6-RC re-review after endpoint runtime evidence policy is satisfied
```

## 6. Next Work

```yaml
immediate:
  - decide whether to run/provide a real CUDA training artifact or change release policy for v0 RC
  - if real adapter evidence is still required, export a new Docker image with a real adapter and rerun no-fake-backend Docker endpoints
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
fake backend due TRANSFORMERS_BACKEND_UNAVAILABLE from missing peft. Docker real
backend dependency packaging is recorded in
artifacts/review/docker_real_backend_deps_evidence.md: requirements-runtime.txt
now includes torch/transformers/peft/safetensors/accelerate/bitsandbytes and a
temp Docker image import probe passed. Export adapter structural validation is
recorded in artifacts/review/export_adapter_validation_evidence.md: malformed
adapter.safetensors and adapter_config format mismatches are rejected before
packaging. Export adapter lineage validation is recorded in
artifacts/review/export_adapter_lineage_evidence.md: adapter files are checked
against ModelRun.adapter_sha256 and artifact_manifest_sha256 before packaging.
M1 smoke recertification is recorded in
artifacts/review/m1_smoke_recertification_evidence.md. The command
COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python
./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install passes in the current
.venv environment, and the previous toolchain mismatch no longer reproduces.
Exported adapter-load guard evidence is recorded in
artifacts/review/exported_adapter_load_guard_evidence.md. The runtime tests now
fail if fake backend is implicit, if native/OpenAI routes bypass the adapter
object, or if Transformers/MLX metadata-only adapters infer without loaded
backend objects. This is test coverage only, not real trained adapter endpoint
evidence.
M6-RC remains NOT_GO until real trained adapter inference evidence exists or the
release policy explicitly accepts fixture-adapter endpoint evidence. Use .venv
for Python.
```
