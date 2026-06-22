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
phase_id: REAL_ADAPTER_RC_GATE_RUNNER
milestone: M6_RC_Blocker_Remediation
phase_status: real_adapter_rc_gate_runner_tooling_verified
active_slice: none
gate_id: mib-studio-real-adapter-rc-gate-runner
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
  gate: mib-studio-real-adapter-rc-gate-runner
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: add a single-command runner for the remaining real adapter M6-RC evidence gate
  evidence:
    real_adapter_rc_gate_runner: artifacts/review/real_adapter_rc_gate_runner_evidence.md
    structured_real_endpoint_evidence: artifacts/review/structured_real_endpoint_evidence.md
    real_adapter_artifact_intake: artifacts/review/real_adapter_artifact_intake_evidence.md
    real_adapter_endpoint_capture_tooling: artifacts/review/real_adapter_endpoint_capture_tooling_evidence.md
    m6_rc_evidence_verification: artifacts/review/m6_rc_evidence_verification.json
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
    - scripts/run_m6_real_adapter_rc_gate.py chains adapter intake, live endpoint capture, and M6-RC GO verification for the real adapter closeout path
    - runner plan-only output records the exact command sequence without executing live Docker evidence or claiming GO
    - focused tests prove the runner stops before endpoint capture on intake failure, refuses MIB_RUNTIME_ALLOW_FAKE_BACKEND, and redacts bearer tokens
    - scripts/capture_real_adapter_endpoint_evidence.py now writes markdown plus structured JSON sidecar evidence
    - structured endpoint JSON records source, self_test, adapter/intake hashes, endpoint status codes, output equivalence, fake-backend absence, and read-only model-cache mount state
    - live capture requires GO adapter artifact intake and lowercase SHA-256 adapter/artifact manifest hashes
    - scripts/verify_m6_rc_evidence.py now rejects markdown-only endpoint evidence and self-test JSON sidecars for M6-RC GO
    - current m6_rc_evidence_verification.json remains NOT_GO with only real_trained_adapter_no_fake_endpoint as acceptable blocker
    - scripts/verify_real_adapter_artifact.py verifies PEFT LoRA metadata, locked base model, safetensors LoRA tensors, non-fixture size, and optional manifest lineage
    - fixture/minimal adapter rejection and real-like PEFT LoRA acceptance are covered by focused tests
    - scripts/capture_real_adapter_endpoint_evidence.py now requires a GO adapter intake report for live endpoint evidence
    - scripts/verify_m6_rc_evidence.py now requires adapter_intake_verified true in real endpoint evidence
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
status: real_adapter_rc_gate_runner_tooling_verified
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/run_m6_real_adapter_rc_gate.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_run_m6_real_adapter_rc_gate.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --plan-only --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --token 12345678901234567890123456789012 --json-output /tmp/mib-real-adapter-rc-gate-plan.json
  - python3 -m json.tool /tmp/mib-real-adapter-rc-gate-plan.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json
  - python3 -m json.tool artifacts/review/m6_rc_evidence_verification.json
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
  M6_RC_Evidence_Current_Not_Go: true
  Real_Adapter_Endpoint_Capture_Tooling: true
  Real_Adapter_Artifact_Intake_Tooling: true
  Structured_Real_Endpoint_Evidence_Tooling: true
  Real_Adapter_RC_Gate_Runner_Tooling: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true

active_gate:
  id: mib-studio-real-adapter-rc-gate-runner
  cto_decision: waiting_for_real_trained_adapter_inference_evidence_or_release_policy
  review_bundle: artifacts/review/real_adapter_rc_gate_runner_evidence.md

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
  - provide or train a real CUDA lora_adapter and strict external model cache
  - run scripts/run_m6_real_adapter_rc_gate.py without --plan-only against the real adapter, exported Docker image, and model cache
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
M6 RC evidence verification is recorded in
artifacts/review/m6_rc_evidence_verification.json. The current verifier decision
is NOT_GO, verification_ok is true, unexpected_blockers is empty, and the only
acceptable blocker is real_trained_adapter_no_fake_endpoint. FE v6 review is now
GO; LLM/Training, Security, DevEx, and CTO remain blocked by missing real
adapter no-fake endpoint evidence.
Real adapter endpoint capture tooling is recorded in
artifacts/review/real_adapter_endpoint_capture_tooling_evidence.md. Use
scripts/capture_real_adapter_endpoint_evidence.py against a real exported CUDA
lora_adapter image and strict model cache to generate
artifacts/review/real_trained_adapter_endpoint_evidence.md. The script refuses
MIB_RUNTIME_ALLOW_FAKE_BACKEND and verifies health/native/OpenAI endpoints,
output equivalence, and read-only model-cache mount. Its self-test output is
rejected by verify_m6_rc_evidence.py as RC GO evidence.
Real adapter artifact intake tooling is recorded in
artifacts/review/real_adapter_artifact_intake_evidence.md. Use
scripts/verify_real_adapter_artifact.py on the real adapter directory/manifest
first, then pass its GO JSON report to
scripts/capture_real_adapter_endpoint_evidence.py with --adapter-intake-report.
verify_m6_rc_evidence.py now requires adapter_intake_verified: true in endpoint
evidence.
Structured real endpoint evidence tooling is recorded in
artifacts/review/structured_real_endpoint_evidence.md. The endpoint capture
script now writes a structured JSON sidecar next to the markdown evidence. The
M6-RC verifier requires that sidecar for real endpoint GO evidence and rejects
markdown-only evidence or self_test JSON. The sidecar must have
source=live_docker_capture, self_test=false, GO adapter intake hashes, no fake
backend, a read-only model-cache mount, 200 health/native/OpenAI statuses, and
native/OpenAI output equivalence.
Real adapter RC gate runner tooling is recorded in
artifacts/review/real_adapter_rc_gate_runner_evidence.md. Use
scripts/run_m6_real_adapter_rc_gate.py without --plan-only to chain real adapter
intake, live endpoint capture, and M6-RC GO verification after a real trained
CUDA lora_adapter, exported Docker image, strict model cache, and bearer token
are available. The runner refuses MIB_RUNTIME_ALLOW_FAKE_BACKEND and redacts
bearer tokens in its JSON summary. Current plan-only verification does not run
Docker evidence and does not claim GO.
M6-RC remains NOT_GO until real trained adapter inference evidence exists or the
release policy explicitly accepts fixture-adapter endpoint evidence. Use .venv
for Python.
```
