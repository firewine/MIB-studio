# MIB Studio Working State

```yaml
doc_type: llm_operational_handoff
audience: llm_agents_only
purpose: read_before_each_task
format: machine_scannable_markdown
ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
context: docs/CONTEXT.md
rule: keep_current_state_next_work_blockers_and_verification_only
```

## 0. Agent Instructions

```yaml
read_before_work:
  - docs/CONTEXT.md
  - docs/WORKING.md
  - docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  - .codex/tasks/current.json

edit_policy:
  - create_or_update_pabcd_contract_before_edits: true
  - respect_allowed_edit_paths: true
  - use_apply_patch_for_manual_edits: true
  - keep_release_go_claims_false_until_real_adapter_evidence_exists: true
  - do_not_edit_docs_reviews_M6_to_GO_without_accepted_real_endpoint_evidence: true

environment:
  python_venv: .venv
  gitignored:
    - .venv/
  frontend_corepack_home: /tmp/corepack
  phase_completion_git_policy: stage_commit_push_after_verified_phase_completion
```

## 1. Current Phase

```yaml
phase_id: FINAL_VERIFICATION_TEST_HARNESS
milestone: Final_Program_Development_Closeout
phase_status: final_verification_pytest_and_fe_e2e_verified_not_go
gate_id: mib-studio-final-verification-pytest-collection
mode: implement
product_code_changed: false
release_claimed_go: false

current_decision:
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

## 2. Latest Work

```yaml
gate: mib-studio-final-verification-pytest-collection
objective: make full Python and FE verification runnable for final completion checks

files:
  pytest_config: pytest.ini
  frontend_scripts: package.json
  runner: scripts/run_v0_release_blocker_recertification.py
  tests: tests/scripts/test_run_v0_release_blocker_recertification.py
  summary: artifacts/review/v0_release_blocker_recertification.json
  refreshed:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh

runner_contract:
  command: scripts/run_v0_release_blocker_recertification.py
  delegates_to_existing_strict_checks:
    - scripts/find_real_adapter_candidates.py
    - scripts/check_cuda_lora_training_prereqs.py
    - scripts/run_m6_real_adapter_rc_gate.py --preflight-only
    - scripts/verify_real_adapter_evidence_bundle.py
    - scripts/verify_v0_release_readiness.py
    - scripts/build_real_adapter_handoff.py
  current_status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false

summary:
  - full pytest now collects duplicate-basename tests safely through pytest importlib mode
  - full Python regression passes: 193 passed
  - FE unit, build, M1 e2e, and FE v6 route-contract e2e pass with the strict local Node/pnpm toolchain
  - pnpm run e2e now invokes Node with --experimental-websocket, which is required by the Chrome CDP client
  - host Docker daemon access is confirmed by docker ps and docker_daemon_available ok:true in the CUDA preflight artifact
  - host-access recertification refreshes candidate scan, CUDA training preflight, M6 RC preflight, real-adapter bundle verification, v0 readiness, and CUDA handoff artifacts
  - Docker-related evidence now records actual missing image/base-image state instead of sandbox permission denial
  - mib-export:test is currently missing on the host: Error response from daemon: No such image: mib-export:test
  - the current local state remains NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
  - FE v6 remains verified through docs/mockup/mib_fe_mockup_v6_routes_contract.html and artifacts/review/fe_v6_evidence.md
  - current scan found 2 fixture-like candidates and 0 GO candidates
  - current CUDA training preflight is NOT_READY_CUDA_LORA_TRAINING with blockers docker_base_image_env_digest, cuda_visible, and docker_base_image_available
  - current M6 real-adapter preflight is NOT_READY_PRECHECK_FAILED
  - current real-adapter bundle verification is NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE
  - current handoff decision is WAITING_FOR_REAL_ADAPTER_INPUTS
```

## 3. Release State

```yaml
recorded_go_markers_required_by_v0_verifier:
  M1_Final_Smoke_Verified: true
  M1_Smoke_Current_Environment: true
  M2_000_to_M2_004_Verified: true
  M3_000_to_M3_005_Verified: true
  M4_001_to_M4_003_Verified: true
  M5_001_to_M5_003_Verified: true
  M6_001_Verified: true
  M6_002_Verified: true
  FE_V6_Mockup_Verified: true
  V0_Release_Readiness_Audit: true

recorded_tooling_ready:
  V0_Release_Blocker_Recertification: true
  V0_Release_Closeout_From_Bundle: true
  Real_Adapter_Evidence_Bundle_Archive: true
  Real_Adapter_Evidence_Bundle_Promotion: true
  Real_Adapter_Evidence_Bundle_Assembly: true
  Real_Adapter_CUDA_Handoff: true
  Real_Adapter_CUDA_Training_Handoff: true
  Real_Adapter_Docker_Image_Handoff: true
  Real_Adapter_RC_Gate_Runner_Tooling: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true
```

## 4. Verification State

```yaml
status: final_verification_pytest_and_fe_e2e_verified_not_go
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run e2e
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/fe_v6_route_contract.test.mjs
  - docker ps
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - python3 -m json.tool artifacts/review/real_adapter_cuda_training_prereq_preflight.json
  - python3 -m json.tool artifacts/review/m6_real_adapter_prereq_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - rg -n -- "docker_daemon_available|No such image|permission denied|NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION|real_trained_adapter_no_fake_endpoint|mib-export:test" artifacts/review/v0_release_blocker_recertification.json artifacts/review/real_adapter_cuda_training_prereq_preflight.json artifacts/review/m6_real_adapter_prereq_audit.json artifacts/review/v0_release_readiness_audit.json docs/WORKING.md
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - git diff --check
  - git diff --cached --check

fixed_verification_blockers:
  - full_pytest_import_file_mismatch_from_duplicate_test_basenames
  - fe_e2e_missing_node_experimental_websocket_flag

warnings:
  - M6-RC remains NOT_GO.
  - v0 release remains NOT_GO.
  - Current host has no verified real trained CUDA lora_adapter no-fake endpoint evidence.
  - Do not claim GO from fixture adapter evidence or self-test evidence.
```

## 5. Active Blockers

```yaml
release_blocker:
  id: real_trained_adapter_no_fake_endpoint
  reason: real trained CUDA lora_adapter no-fake Docker endpoint evidence is missing
  required_before_go:
    - adapter.safetensors under /tmp/mib-real-adapter/adapter
    - adapter_config.json under /tmp/mib-real-adapter/adapter
    - manifest.json for the real adapter artifact
    - digest-pinned CUDA/Python Docker base image available on the CUDA host
    - mib-export:test image built with the real adapter
    - no-fake-backend live endpoint transcript evidence
    - M6 review docs updated to GO only after accepted evidence review
    - GO_REAL_ADAPTER_EVIDENCE_BUNDLE promoted into artifacts/review
    - v0 readiness decision GO

local_missing_inputs:
  - /tmp/mib-real-adapter/adapter/adapter.safetensors
  - /tmp/mib-real-adapter/adapter/adapter_config.json
  - /tmp/mib-real-adapter/manifest.json
  - nvidia-smi_cuda_visibility
  - MIB_DOCKER_BASE_IMAGE_WITH_DIGEST
  - local_digest_pinned_cuda_python_base_image
  - mib-export:test_real_adapter_image
```

## 6. Next Work

```yaml
recertify_current_state:
  command: >
    PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
    scripts/run_v0_release_blocker_recertification.py
    --expected-readiness-decision NOT_GO
    --expected-bundle-decision NOT_GO
    --expected-training-status NOT_READY_CUDA_LORA_TRAINING
    --expected-rc-status NOT_READY_PRECHECK_FAILED

external_cuda_host_flow:
  - run artifacts/review/real_adapter_cuda_training_handoff.sh on a CUDA host
  - run artifacts/review/real_adapter_docker_image_handoff.sh after a real adapter exists
  - run scripts/run_m6_real_adapter_rc_gate.py --endpoint-evidence-only for live no-fake endpoint evidence
  - review endpoint evidence before changing M6 review docs
  - update docs/reviews/M6/SIGNOFF_MATRIX.md and docs/reviews/M6/CTO_DECISION.md to GO only if evidence is accepted
  - run scripts/run_m6_real_adapter_rc_gate.py --m6-verification-only
  - run scripts/build_real_adapter_evidence_bundle.py --archive-output artifacts/review/real_adapter_evidence_bundle.tar.gz

local_closeout_after_bundle_transfer:
  command: >
    PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
    scripts/run_v0_release_closeout_from_bundle.py
    --bundle-archive <copied_real_adapter_evidence_bundle.tar.gz>
    --expected-bundle-decision GO
    --expected-readiness-decision GO
  expected_success_status: GO_V0_RELEASE_CLOSEOUT
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md, docs/WORKING.md, and .codex/tasks/current.json before
edits. Use .venv for Python and COREPACK_HOME=/tmp/corepack for frontend
commands. The active closeout tool is
scripts/run_v0_release_blocker_recertification.py. It refreshes the current
candidate scan, CUDA training preflight, M6 RC preflight, real-adapter bundle
verification, v0 readiness, and CUDA handoff artifacts with one command.
The latest host-access recertification confirmed docker_daemon_available ok:true
and mib-export:test missing as "No such image", so Docker permission denial is
not the current release blocker.

Do not claim M6-RC GO or v0 GO from the current local artifacts. The current
release blocker is real_trained_adapter_no_fake_endpoint. M6 review docs must
stay NOT_GO until accepted real trained CUDA lora_adapter no-fake Docker endpoint
evidence exists.

The current recertification status is NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION:
0 GO adapter candidates, CUDA training preflight NOT_READY_CUDA_LORA_TRAINING,
M6 real-adapter preflight NOT_READY_PRECHECK_FAILED, evidence bundle NOT_GO, v0
readiness NOT_GO with no unexpected blockers, and handoff decision
WAITING_FOR_REAL_ADAPTER_INPUTS.
```
