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
phase_id: CONTEXT_CURRENT_STATE_ALIGNMENT
milestone: Final_Program_Development_Closeout
phase_status: context_current_state_alignment_verified_not_go
gate_id: mib-studio-context-current-state-alignment
mode: implement
product_code_changed: false
release_claimed_go: false
latest_commit_policy: stage_commit_push_after_verified_phase_completion

current_decision:
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

## 2. Latest Completed Work

```yaml
gate: mib-studio-v0-release-closeout-from-bundle
objective: add local closeout runner for externally supplied real-adapter evidence bundle directory or tar.gz archive

files:
  runner: scripts/run_v0_release_closeout_from_bundle.py
  tests: tests/scripts/test_run_v0_release_closeout_from_bundle.py
  refreshed_readiness_report: artifacts/review/v0_release_readiness_audit.json

runner_contract:
  command: scripts/run_v0_release_closeout_from_bundle.py
  accepts:
    - --bundle-dir
    - --bundle-archive
  source_path_resolution: relative_bundle_paths_are_resolved_against_--root
  promotion_dependency: scripts/promote_real_adapter_evidence_bundle.py
  readiness_dependency: scripts/verify_v0_release_readiness.py
  canonical_bundle_verification_written_before_readiness: true
  output_summary_default: artifacts/review/v0_release_closeout_from_bundle.json
  statuses:
    - GO_V0_RELEASE_CLOSEOUT
    - NOT_GO_BUNDLE_PROMOTION
    - NOT_GO_V0_READINESS
    - DRY_RUN_V0_RELEASE_CLOSEOUT

summary:
  - docs/CONTEXT.md is being aligned with the current v0 closeout state so future LLMs do not restart from stale M1 startup instructions.
  - current context alignment keeps FE v6 as verified via docs/mockup/mib_fe_mockup_v6_routes_contract.html and artifacts/review/fe_v6_evidence.md.
  - run_v0_release_closeout_from_bundle promotes a verified external evidence bundle into artifacts/review using the existing strict promotion verifier.
  - It writes artifacts/review/real_adapter_evidence_bundle_verification.json before running v0 readiness, so readiness evaluates the promoted bundle in the same command.
  - It reports GO_V0_RELEASE_CLOSEOUT only when bundle promotion succeeds and v0 readiness verifies GO.
  - It reports NOT_GO_BUNDLE_PROMOTION when the bundle cannot be promoted as GO.
  - It reports NOT_GO_V0_READINESS when bundle promotion succeeds but v0 readiness remains blocked.
  - Current local state remains NOT_GO because real trained adapter no-fake Docker endpoint evidence is still absent.
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
status: context_current_state_alignment_verified_not_go
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - rg -n -- "current_development_state|FE_V6_Mockup_Verified|mib_fe_mockup_v6_routes_contract|V0_RELEASE_CLOSEOUT_FROM_BUNDLE|real_trained_adapter_no_fake_endpoint|authorized_milestone|product_code_started" docs/CONTEXT.md docs/WORKING.md
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - git diff --check
  - git diff --cached --check

warnings:
  - M6-RC remains NOT_GO.
  - v0 release remains NOT_GO.
  - Current host has no verified real trained CUDA lora_adapter no-fake endpoint evidence.
  - Do not claim GO from fixture adapter evidence or self-test evidence.
  - bootstrap skip-install still skips cuda pip-audit after isolated pip upgrade failure per script policy.
```

## 5. Active Blockers

```yaml
release_blocker:
  id: real_trained_adapter_no_fake_endpoint
  reason: real trained CUDA lora_adapter no-fake Docker endpoint evidence is missing
  required_before_go:
    - real adapter directory with adapter.safetensors and adapter_config.json
    - manifest.json for the real adapter artifact
    - digest-pinned CUDA/Python Docker base image available on the CUDA host
    - mib-export:test image built with the real adapter
    - no-fake-backend live endpoint transcript evidence
    - M6 review docs updated to GO only after accepted evidence review
    - GO_REAL_ADAPTER_EVIDENCE_BUNDLE promoted into artifacts/review
    - v0 readiness decision GO

local_missing_inputs:
  - /tmp/mib-real-adapter/adapter
  - /tmp/mib-real-adapter/manifest.json
  - nvidia-smi_cuda_visibility
  - local_digest_pinned_cuda_python_base_image
  - mib-export:test_real_adapter_image
```

## 6. Next Work

```yaml
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
  expected_failure_without_real_bundle: NOT_GO_BUNDLE_PROMOTION_or_NOT_GO_V0_READINESS
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md, docs/WORKING.md, and .codex/tasks/current.json before
edits. Use .venv for Python and COREPACK_HOME=/tmp/corepack for frontend
commands. The latest completed gate is
mib-studio-v0-release-closeout-from-bundle.

Do not claim M6-RC GO or v0 GO from the current local artifacts. The current
release blocker is real_trained_adapter_no_fake_endpoint. M6 review docs must
stay NOT_GO until accepted real trained CUDA lora_adapter no-fake Docker endpoint
evidence exists.

For a transferred external CUDA evidence bundle, prefer:
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
scripts/run_v0_release_closeout_from_bundle.py
--bundle-archive <copied_real_adapter_evidence_bundle.tar.gz>
--expected-bundle-decision GO
--expected-readiness-decision GO

The runner first delegates to scripts/promote_real_adapter_evidence_bundle.py,
which verifies the bundle with scripts/verify_real_adapter_evidence_bundle.py and
copies only fixed verifier-required evidence files into artifacts/review. Then it
writes the canonical bundle verification report and runs
scripts/verify_v0_release_readiness.py. GO_V0_RELEASE_CLOSEOUT is valid only when
both bundle promotion and v0 readiness are GO. Current local readiness is still
NOT_GO with no unexpected blockers.
```
