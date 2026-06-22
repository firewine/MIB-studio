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
  strict_toolchain_helper: scripts/prepare_strict_toolchain.py
  strict_toolchain_defaults:
    MIB_TOOLCHAIN_ROOT: /tmp/mib-toolchain
    COREPACK_HOME: /tmp/corepack
  phase_completion_git_policy: stage_commit_push_after_verified_phase_completion
```

## 1. Current Phase

```yaml
phase_id: EXTERNAL_CUDA_HANDOFF_READINESS_AUDIT_AFTER_C103FCE_PACKET
milestone: Final_Program_Development_Closeout
phase_status: complete_pending_commit_push
gate_id: mib-studio-current-head-external-cuda-handoff-readiness-audit-after-c103fce-packet
mode: development
product_code_changed: false
frontend_code_changed: false
verification_tooling_changed: false
training_handoff_artifacts_refreshed: false
external_operator_packet_refreshed: false
external_operator_packet_refresh_required_after_phase_commit: false
external_cuda_handoff_readiness_refreshed: true
llm_context_synced_after_readiness_push: true
operator_packet_ready: true
strict_model_cache_ready: true
cuda_base_image_resolved: true
docker_daemon_available: true
release_claimed_go: false

current_decision:
  strict_m1_smoke: passed
  current_head_v0_recertification: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  external_cuda_operator_packet_verification: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  external_cuda_operator_transfer_status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  external_cuda_handoff_readiness: WAITING_FOR_EXTERNAL_CUDA_HOST
  current_workspace_head: c103fce
  latest_readiness_audit_checkout_head: c103fce
  current_recertification_head: c7acb56
  current_packet_source_commit: c7acb56
  current_phase_changes_make_packet_stale_until_follow_up_refresh: false
  training_handoff_command_order_suffix:
    - prepare_docker_image
    - run_docker_image_handoff
    - run_rc_handoff
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

## 2. Latest Work

```yaml
gate: mib-studio-current-head-external-cuda-handoff-readiness-audit-after-c103fce-packet
objective: refresh current-head external CUDA handoff readiness after packet refresh commit c103fce

checkout_head: c103fce
packet_source_commit: c7acb56

readiness_audit:
  status: WAITING_FOR_EXTERNAL_CUDA_HOST
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  current_release_blocker: real_trained_adapter_no_fake_endpoint

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  live_reverification_json: /tmp/mib-c103fce-external-cuda-operator-packet-verification.json
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at c7acb56
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: c7acb56
  json_output: /tmp/mib-c103fce-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

strict_model_cache:
  status: READY_STRICT_MODEL_CACHE
  download_allowed: false
  required_file_count: 5
  json_output: /tmp/mib-c103fce-strict-model-cache-readiness.json

ready_requirements:
  - GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  - READY_STRICT_MODEL_CACHE
  - backend_config_present
  - docker_daemon_available
  - docker_base_image_available

blocking_requirements:
  - nvidia_smi_available
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - mib_export_test_image_available
  - runtime_bearer_token_present

local_host_checks:
  nvidia_smi_available: false
  docker_daemon_available: true
  docker_server_version: 29.6.0
  docker_base_image_available: true
  mib_export_test_image_available: false
  backend_config_present: true
  adapter_root_present: true
  adapter_dir_present: true
  adapter_safetensors_present: false
  adapter_config_present: false
  adapter_manifest_present: false
  runtime_bearer_token_present: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after c103fce, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: readiness audit does not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-c7acb56-recertification
objective: refresh external CUDA operator packet after current-head recertification commit c7acb56

source_head: c7acb56
packet_source_commit: c7acb56

packet:
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  required_committed_files: 18

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at c7acb56
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: c7acb56
  json_output: /tmp/mib-c7acb56-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: refresh current-head external CUDA handoff readiness audit after this packet-refresh commit, then run bash artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host
  host: external CUDA host with full repository checkout after this packet refresh commit, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: packet GO and transfer READY do not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-current-head-v0-recertification-after-13964c0-readiness-audit
objective: refresh strict smoke and v0 release blocker evidence after pushed readiness audit closeout

baseline_head: 13964c0
latest_readiness_audit_checkout_head: 50d67bf
packet_source_commit: 3e9f3ea

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  unexpected_blockers: []
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

strict_m1_smoke:
  command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  result: passed
  pytest: tests/smoke/test_m1_smoke.py 1 passed

cuda_host_diagnostics:
  strict_model_cache_files: ok
  docker_daemon_available: ok
  docker_base_image_available: ok
  cuda_visible: false
  docker_image_available: false
  adapter_files_present: false

phase_outputs:
  artifact_files_changed: true
  product_code_changed: false
  packet_refresh_required_after_commit: true
  packet_refresh_reason: recertification refreshed source-pinned release/handoff artifacts

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: refresh external CUDA operator packet from the current recertification commit, then run bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout after the packet refresh, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: recertification does not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-handoff-readiness-audit-after-50d67bf-packet
objective: refresh current-head external CUDA handoff readiness after packet refresh commit 50d67bf

checkout_head: 50d67bf
packet_source_commit: 3e9f3ea

readiness_audit:
  status: WAITING_FOR_EXTERNAL_CUDA_HOST
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  current_release_blocker: real_trained_adapter_no_fake_endpoint

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at 3e9f3ea
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: 3e9f3ea
  json_output: /tmp/mib-50d67bf-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

strict_model_cache:
  status: READY_STRICT_MODEL_CACHE
  download_allowed: false
  required_file_count: 5
  json_output: /tmp/mib-50d67bf-strict-model-cache-readiness.json

ready_requirements:
  - GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  - READY_STRICT_MODEL_CACHE
  - backend_config_present
  - docker_daemon_available
  - docker_base_image_available

blocking_requirements:
  - nvidia_smi_available
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - mib_export_test_image_available
  - runtime_bearer_token_present

local_host_checks:
  nvidia_smi_available: false
  docker_daemon_available: true
  docker_server_version: 29.6.0
  docker_base_image_available: true
  mib_export_test_image_available: false
  backend_config_present: true
  adapter_root_present: true
  adapter_dir_present: true
  adapter_safetensors_present: false
  adapter_config_present: false
  adapter_manifest_present: false
  runtime_bearer_token_present: false

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after 50d67bf, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: do not build or tag mib-export:test from fake or self-test adapter material; readiness audit does not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-3e9f3ea-recertification
objective: refresh source-pinned external CUDA operator packet after current-head recertification

source_head: 3e9f3ea

packet:
  status: PREPARED_NOT_RUN
  source_commit: 3e9f3ea
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files: 18
  training_handoff_command_order_contains:
    - run_docker_image_handoff
  release_claimed_go: false
  m6_rc_claimed_go: false

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at 3e9f3ea
  forbidden_tracked_artifacts: []
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: 3e9f3ea
  json_output: /tmp/mib-3e9f3ea-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after 3e9f3ea, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: packet verification GO and transfer READY are operator handoff readiness results, not M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-current-head-post-merge-smoke-v0-recertification
objective: refresh strict smoke and v0 release blocker evidence after updated remote HEAD

baseline_head: 7091a10

strict_m1_smoke:
  command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  result: passed
  pytest: tests/smoke/test_m1_smoke.py 1 passed
  openapi_export: ok
  pip_audit_cuda: skipped_by_skip_install_environment

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  unexpected_blockers: []
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

cuda_host_diagnostics:
  strict_model_cache_files: ok
  docker_daemon_available: ok
  docker_base_image_available: ok
  cuda_visible: false
  docker_image_available: false
  adapter_files_present: false

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after the next packet refresh commit, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths

follow_up_required:
  - refresh artifacts/review/external_cuda_operator_packet.json after this recertification source commit exists
  - rerun operator packet verifier and transfer manifest before external CUDA operator execution

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-5dfb80f-training-handoff
objective: refresh source-pinned external CUDA operator packet after training handoff docker-image run step

source_head: 5dfb80f

packet:
  status: PREPARED_NOT_RUN
  source_commit: 5dfb80f
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files: 18
  training_handoff_command_order_contains:
    - run_docker_image_handoff
  release_claimed_go: false
  m6_rc_claimed_go: false

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at 5dfb80f
  forbidden_tracked_artifacts: []
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: 5dfb80f
  json_output: /tmp/mib-5dfb80f-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after 5dfb80f, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: packet verification GO and transfer READY are operator handoff readiness results, not M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-training-handoff-docker-build-before-rc
objective: run generated real-adapter Docker image handoff before RC handoff

baseline_head: 6017721

source_changes:
  - scripts/prepare_cuda_lora_training_run.py inserts run_docker_image_handoff after prepare_docker_image
  - scripts/verify_external_cuda_operator_packet.py requires run_docker_image_handoff in training_handoff command_order
  - focused tests assert prepare_docker_image -> run_docker_image_handoff -> run_rc_handoff ordering

training_handoff_artifacts:
  status: PREPARED_NOT_RUN
  dataset_id: review_router_20
  training_preset: quick
  command_order_suffix:
    - prepare_docker_image
    - run_docker_image_handoff
    - run_rc_handoff
  docker_handoff_shell: artifacts/review/real_adapter_docker_image_handoff.sh
  rc_handoff_shell: artifacts/review/real_adapter_cuda_handoff.sh
  release_claimed_go: false
  m6_rc_claimed_go: false

verification:
  focused_pytest: 14 passed
  py_compile: passed
  training_handoff_json: valid
  training_handoff_shell_syntax: valid

follow_up_resolved:
  - external CUDA operator packet refreshed at source commit 5dfb80f
  - packet verifier returned GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - transfer manifest returned READY_EXTERNAL_CUDA_OPERATOR_TRANSFER

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-5239f8d-recertification
objective: refresh source-pinned external CUDA operator packet after current-head recertification

source_head: 5239f8d

packet:
  status: PREPARED_NOT_RUN
  source_commit: 5239f8d
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files: 18
  release_claimed_go: false
  m6_rc_claimed_go: false

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at 5239f8d
  forbidden_tracked_artifacts: []
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: 5239f8d
  json_output: /tmp/mib-5239f8d-external-cuda-transfer-readiness.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after 5239f8d, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: packet verification GO and transfer READY are operator handoff readiness results, not M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-current-head-v0-recertification-after-dda74a5-readiness-audit
objective: refresh current-head v0 release blocker recertification after readiness audit

baseline_head: dda74a5

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  expected_readiness_decision: NOT_GO
  expected_bundle_decision: NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE

v0_readiness:
  decision: NOT_GO
  release_ready: false
  verification_ok: true
  unexpected_blockers: []
  acceptable_not_go_blockers:
    - real_trained_adapter_no_fake_endpoint
  blockers:
    - real_trained_adapter_no_fake_endpoint

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  blockers:
    - cuda_visible
  docker_base_image_env_digest: true
  docker_base_image_available: true
  strict_model_cache_files: true

m6_prereq:
  status: NOT_READY_PRECHECK_FAILED
  missing_prereq_ids:
    - adapter_safetensors_present
    - adapter_config_present
    - adapter_manifest_present
    - docker_image_available
    - host_cuda_visible

handoff:
  decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh

packet_refresh_required:
  required: true
  reason: recertification and real-adapter handoff artifacts are source-pinned operator-packet inputs
  resolved_by: 5239f8d_packet_refresh_follow_up

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-current-head-external-cuda-handoff-readiness-audit-after-2e3a70b
objective: refresh current-head external CUDA handoff readiness after packet refresh

checkout_head: 2e3a70b
packet_source_commit: cbd6074

readiness_audit:
  status: WAITING_FOR_EXTERNAL_CUDA_HOST
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  current_release_blocker: real_trained_adapter_no_fake_endpoint

ready_requirements:
  - GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  - READY_STRICT_MODEL_CACHE
  - backend_config_present
  - docker_daemon_available
  - docker_base_image_available

blocking_requirements:
  - nvidia_smi_available
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - mib_export_test_image_available
  - runtime_bearer_token_present

local_host_checks:
  nvidia_smi_available: false
  docker_daemon_available: true
  docker_server_version: 29.6.0
  docker_base_image_available: true
  mib_export_test_image_available: false
  backend_config_present: true
  adapter_root_present: true
  adapter_dir_present: true
  adapter_safetensors_present: false
  adapter_config_present: false
  adapter_manifest_present: false
  runtime_bearer_token_present: false

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after 2e3a70b, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, real runtime token, and real adapter output paths
  note: do not build or tag mib-export:test from fake or self-test adapter material; readiness audit does not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-cbd6074-launcher-guard
objective: refresh source-pinned external CUDA operator packet after verified launcher transfer-manifest guard

baseline_head: cbd6074

packet:
  status: PREPARED_NOT_RUN
  source_commit: cbd6074
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files: 18
  release_claimed_go: false
  m6_rc_claimed_go: false

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at cbd6074
  forbidden_tracked_artifacts: []
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  packet_handoff_source_commit: cbd6074
  json_output: /tmp/mib-cbd6074-external-cuda-operator-transfer-manifest.json
  transfer_model: full_repository_checkout_required
  committed_to_repo: false

strict_bootstrap:
  command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  result: PASS
  toolchain_mismatch: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after cbd6074, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, and real adapter output paths
  note: packet verification GO and transfer READY are operator handoff readiness results, not M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-verified-external-cuda-launcher-transfer-manifest-guard
objective: require transfer-manifest readiness inside the verified external CUDA launcher before training

baseline_head: c79f7d0

launcher_command_order:
  - verify_external_cuda_operator_packet
  - build_external_cuda_operator_transfer_manifest
  - run_real_adapter_cuda_training_handoff

new_guard:
  command: ./.venv/bin/python scripts/build_external_cuda_operator_transfer_manifest.py --packet-json artifacts/review/external_cuda_operator_packet.json --packet-verification-json artifacts/review/external_cuda_operator_packet_verification.json --json-output artifacts/review/external_cuda_operator_transfer_manifest.json --markdown-output artifacts/review/external_cuda_operator_transfer_manifest.md --expected-status READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  enforced_before: artifacts/review/real_adapter_cuda_training_handoff.sh
  expected_status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER

guardrails_preserved:
  - MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset
  - release_claimed_go remains false
  - m6_rc_claimed_go remains false

generated_artifacts_refreshed:
  - artifacts/review/verified_external_cuda_training_launcher.json
  - artifacts/review/verified_external_cuda_training_launcher.md
  - artifacts/review/verified_external_cuda_training_launcher.sh

follow_up_required:
  external_cuda_operator_packet_refresh_required: true
  reason: launcher generator and committed launcher artifact changed, so packet required_committed_files hashes must be refreshed from the launcher guard commit

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-current-head-external-cuda-handoff-readiness-audit-after-e5d761f
objective: refresh current-head external CUDA handoff readiness after packet refresh

checkout_head: e5d761f
packet_source_commit: b3efba2

readiness_audit:
  status: WAITING_FOR_EXTERNAL_CUDA_HOST
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  current_release_blocker: real_trained_adapter_no_fake_endpoint

ready_requirements:
  - GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  - READY_STRICT_MODEL_CACHE
  - backend_config_present
  - docker_daemon_available
  - docker_base_image_available

blocking_requirements:
  - nvidia_smi_available
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - mib_export_test_image_available
  - runtime_bearer_token_present

local_host_checks:
  nvidia_smi_available: false
  docker_daemon_available: true
  docker_server_version: 29.6.0
  docker_base_image_available: true
  mib_export_test_image_available: false
  adapter_safetensors_present: false
  adapter_config_present: false
  adapter_manifest_present: false
  runtime_bearer_token_present: false

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout at or after e5d761f, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, and real adapter output paths
  note: readiness audit does not claim M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-external-cuda-operator-packet-refresh-after-b3efba2-recertification
objective: refresh source-pinned external CUDA operator packet after b3efba2 recertification

source_head: b3efba2

packet:
  status: PREPARED_NOT_RUN
  source_commit: b3efba2
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files: 18

packet_verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at b3efba2
  forbidden_tracked_artifacts: []
  warnings: []

strict_model_cache:
  status: READY_STRICT_MODEL_CACHE
  no_download: true
  json_output: /tmp/mib-b3efba2-strict-model-cache-preparation.json

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  json_output: /tmp/mib-b3efba2-external-cuda-operator-transfer-manifest.json
  transfer_model: full_repository_checkout_required

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

operator_next_step:
  run: bash artifacts/review/verified_external_cuda_training_launcher.sh
  host: external CUDA host with full repository checkout, .venv, nvidia-smi, strict model cache, digest-pinned CUDA base image, Docker daemon, and real adapter output paths
  note: packet verification GO is an operator handoff readiness result, not M6-RC GO or v0 release GO
```

```yaml
gate: mib-studio-current-head-v0-recertification-after-fe-v6-order
objective: refresh tracked v0 release blocker recertification after FE v6 workflow order commit

source_head: f57f3ff

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  release_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_unexpected_blockers: []
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  blockers:
    - cuda_visible
  digest_pinned_base_image_ready: true
  strict_model_cache_ready: true
  docker_daemon_available: true

m6_prereq:
  status: NOT_READY_PRECHECK_FAILED
  missing_prereq_ids:
    - adapter_safetensors_present
    - adapter_config_present
    - adapter_manifest_present
    - docker_image_available
    - host_cuda_visible

handoff:
  decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh

packet_state:
  current_packet_source_head: f31050c
  current_packet_verification_after_recertification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  stale_hash_paths:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
  packet_refresh_required: true
  next_gate: refresh external CUDA operator packet from the recertification commit

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-fe-v6-workflow-order-alignment
objective: align desktop sidebar workflow ordering with canonical FE v6 mockup and UX_SPEC

source_head: 006cc89
canonical_sources:
  - docs/specs/UX_SPEC.md
  - docs/mockup/mib_fe_mockup_v6_routes_contract.html

previous_app_order:
  - Project
  - Define
  - Data
  - Hardware
  - Train
  - Benchmark
  - Package
  - Export

current_app_order:
  - Workbench
  - Hardware
  - Define
  - Data
  - Train
  - Benchmark
  - Package
  - Export

changed_files:
  - apps/desktop/src/lib/appModel.mjs
  - apps/desktop/src/lib/appModel.test.mjs
  - apps/desktop/e2e/fe_v6_route_contract.test.mjs

verification_completed:
  - python3 -m json.tool .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --test apps/desktop/src/lib/appModel.test.mjs
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node --experimental-websocket --test apps/desktop/e2e/fe_v6_route_contract.test.mjs
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs test
  - COREPACK_HOME=/tmp/corepack /tmp/mib-toolchain/node-v20.18.1-linux-x64/bin/node /tmp/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs run build

verification_pending:
  - stage/commit/push

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-handoff-readiness-audit
objective: capture current local readiness and blockers before external CUDA host handoff

source_head: b79322a
readiness_artifacts:
  - artifacts/review/external_cuda_handoff_readiness_audit.json
  - artifacts/review/external_cuda_handoff_readiness_audit.md

packet:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  packet_handoff_source_commit: f31050c
  warnings: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  full_checkout_required: true
  partial_file_archive_allowed: false

strict_model_cache:
  status: READY_STRICT_MODEL_CACHE
  download_allowed: false
  required_file_count: 5

local_host_checks:
  nvidia_smi_available: false
  docker_daemon_available: true
  docker_server_version: "29.6.0"
  docker_base_image_available: true
  mib_export_test_image_available: false
  backend_config_present: true
  adapter_root_present: true
  adapter_dir_present: true
  adapter_safetensors_present: false
  adapter_config_present: false
  adapter_manifest_present: false
  runtime_bearer_token_present: false

next_required_action:
  status: WAITING_FOR_EXTERNAL_CUDA_HOST
  command: bash artifacts/review/verified_external_cuda_training_launcher.sh
  requirements:
    - full repository checkout at or after b79322a
    - nvidia-smi succeeds
    - real MIB_RUNTIME_BEARER_TOKEN with at least 32 characters
    - MIB_RUNTIME_ALLOW_FAKE_BACKEND unset
    - /tmp/mib-real-adapter/adapter/adapter.safetensors after training
    - /tmp/mib-real-adapter/adapter/adapter_config.json after training
    - /tmp/mib-real-adapter/manifest.json after training
    - mib-export:test built with the same real adapter hash

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-post-recertification-external-cuda-packet-refresh
objective: refresh external CUDA operator packet verification after current-head recertification changed source-pinned artifacts

source_head: f31050c
previous_packet_source_head: 5fc0a75

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_hash_paths:
    - artifacts/review/real_adapter_cuda_handoff.json:sha256
    - artifacts/review/real_adapter_cuda_handoff.md:sha256
    - artifacts/review/v0_release_blocker_recertification.json:sha256

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: f31050c
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 18
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - scripts/prepare_strict_model_cache.py
    - scripts/build_external_cuda_operator_transfer_manifest.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: f31050c
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at f31050c
  forbidden_tracked_artifacts: []

transfer_manifest:
  status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  full_checkout_required: true
  partial_file_archive_allowed: false
  packet_handoff_source_commit: f31050c

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-current-head-159a00a-v0-blocker-recertification
objective: refresh current-head local NOT_GO release blocker diagnostics after external CUDA packet refresh

source_head: 159a00a
recertification_timestamp_utc: "2026-06-22T21:00:25.554548+00:00"

files:
  refreshed_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  docker_base_image_env_digest_ok: true
  docker_base_image_available_ok: true
  docker_base_image_cuda_python_runtime_ok: true
  docker_daemon_available_ok: true
  strict_model_cache_files_ok: true
  blockers:
    - cuda_visible

m6_prereq:
  status: NOT_READY_PRECHECK_FAILED
  errors:
    - adapter_safetensors_present
    - adapter_config_present
    - adapter_manifest_present
    - docker_image_available: No such image: mib-export:test
    - host_cuda_visible: nvidia-smi not found

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh

post_recert_packet_check:
  decision: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  expected_decision: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_hash_paths:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
  follow_up_packet_refresh_required: true

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false
  packet_artifacts_refreshed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-post-transfer-manifest-external-cuda-packet-refresh
objective: refresh external CUDA operator packet verification after transfer manifest tooling changed the packet required-file contract

source_head: 5fc0a75
previous_packet_source_head: 7e6c545

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  missing_marker: scripts/build_external_cuda_operator_transfer_manifest.py:not_in_required_files
  old_required_committed_files_count: 17

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: 5fc0a75
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 18
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - scripts/prepare_strict_model_cache.py
    - scripts/build_external_cuda_operator_transfer_manifest.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: 5fc0a75
  required_file_hashes: verified 18 required file hashes
  required_commit_blobs: verified 18 required file blobs at 5fc0a75
  forbidden_tracked_artifacts: []
  transfer_manifest_post_refresh: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-transfer-manifest-tooling
objective: add a full-checkout transfer/readiness manifest builder for external CUDA operators without claiming release GO

source_head: a61cbd3
packet_artifact_source_head_before_phase: 7e6c545

files:
  tooling:
    - scripts/build_external_cuda_operator_transfer_manifest.py
    - scripts/build_external_cuda_operator_packet.py
    - scripts/verify_external_cuda_operator_packet.py
  tests:
    - tests/scripts/test_build_external_cuda_operator_transfer_manifest.py
    - tests/scripts/test_build_external_cuda_operator_packet.py
    - tests/scripts/test_verify_external_cuda_operator_packet.py
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

transfer_manifest_builder:
  schema_version: mib_external_cuda_operator_transfer_manifest.v1
  ready_status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  not_ready_status: NOT_READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  transfer_model: full_repository_checkout_required
  full_checkout_required: true
  partial_file_archive_allowed: false
  release_claimed_go: false
  m6_rc_claimed_go: false
  ready_conditions:
    - packet verification decision is GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
    - packet verification_ok and operator_packet_ready are true
    - packet verification warnings are empty
    - forbidden tracked artifacts list is empty
    - packet and verification do not claim release GO or M6-RC GO
    - packet.git.head matches packet_handoff_source_commit
    - primary handoff is artifacts/review/verified_external_cuda_training_launcher.sh
    - packet-required checkout files exist

packet_contract_change:
  new_required_committed_file_after_follow_up_refresh: scripts/build_external_cuda_operator_transfer_manifest.py
  existing_packet_artifact_required_file_count: 17
  expected_required_file_count_after_follow_up_refresh: 18
  current_phase_regenerates_packet_artifacts: false
  follow_up_packet_refresh_required: true

verification:
  focused_tests: "15 passed in 0.14s"
  py_compile: passed
  live_transfer_manifest_generation: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
  live_transfer_manifest_json: /tmp/mib-external-cuda-operator-transfer-manifest.json
  live_transfer_manifest_blockers: []
  diff_check: passed
  cached_diff_check: passed
  strict_m1_smoke_after_toolchain_fix: already_passed_at_head_a61cbd3_before_this_tooling_phase

scope:
  product_code_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-post-cuda-base-image-external-cuda-packet-refresh
objective: refresh external CUDA operator packet verification after CUDA base-image recertification changed source-pinned handoff artifact hashes

source_head: 7e6c545
previous_packet_source_head: 63d72ab
packet_timestamp_utc: "2026-06-22T20:31:21.958180+00:00"
verification_timestamp_utc: "2026-06-22T20:31:26.410051+00:00"

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_source_commit: 63d72ab

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: 7e6c545
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
    - scripts/resolve_cuda_base_image.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: 7e6c545
  required_file_hashes: verified 17 required file hashes
  required_commit_blobs: verified 17 required file blobs at 7e6c545
  forbidden_tracked_artifacts: []

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-cuda-base-image-resolution-recertification
objective: resolve a digest-pinned CUDA/Python Docker base image and rerun v0 blocker recertification without changing release acceptance rules

source_head: 5e7cc94
cuda_base_image_timestamp_utc: "2026-06-22T20:22:52.791337+00:00"
recertification_timestamp_utc: "2026-06-22T20:23:32.702207+00:00"

pre_audit:
  docker_daemon_host_access: ok
  prior_cuda_base_image_resolution: NOT_READY_CUDA_BASE_IMAGE
  default_candidate: pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

files:
  refreshed_artifacts:
    - artifacts/review/real_adapter_cuda_base_image_resolution.json
    - artifacts/review/real_adapter_cuda_base_image.env
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
    - artifacts/review/v0_release_blocker_recertification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

cuda_base_image:
  status: CUDA_BASE_IMAGE_RESOLVED
  selected: pytorch/pytorch@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126
  env_file: artifacts/review/real_adapter_cuda_base_image.env
  release_claimed_go: false
  m6_rc_claimed_go: false

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  docker_base_image_env_digest_ok: true
  docker_base_image_available_ok: true
  docker_base_image_cuda_python_runtime_ok: true
  docker_daemon_available_ok: true
  strict_model_cache_files_ok: true
  blockers:
    - cuda_visible

m6_prereq:
  status: NOT_READY_PRECHECK_FAILED
  errors:
    - adapter_safetensors_present
    - adapter_config_present
    - adapter_manifest_present
    - docker_image_available: No such image: mib-export:test
    - host_cuda_visible: nvidia-smi not found

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  blocking_reasons_removed:
    - docker_base_image_env_digest
    - docker_base_image_available

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false
  docker_image_layers_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

follow_up:
  external_cuda_operator_packet_refresh_required: false
  resolved_by: mib-studio-post-cuda-base-image-external-cuda-packet-refresh
```

```yaml
gate: mib-studio-post-host-docker-recert-external-cuda-packet-refresh
objective: refresh external CUDA operator packet verification after host-access recertification changed source-pinned handoff artifact hashes

source_head: 63d72ab
previous_packet_source_head: 29392d5
packet_timestamp_utc: "2026-06-22T20:13:23.739676+00:00"
verification_timestamp_utc: "2026-06-22T20:13:28.398697+00:00"

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_source_commit: 29392d5

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: 63d72ab
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
    - scripts/prepare_strict_model_cache.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: 63d72ab
  required_file_hashes: verified 17 required file hashes
  required_commit_blobs: verified 17 required file blobs at 63d72ab
  forbidden_tracked_artifacts: []

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-host-docker-access-v0-recertification
objective: refresh current v0 release blocker recertification with host Docker access so local NOT_GO blockers reflect the real release workstation state

source_head: ce422a4
recertification_timestamp_utc: "2026-06-22T20:08:59.121771+00:00"

pre_audit:
  docker_daemon_host_access: ok
  docker_server_version: "29.6.0"
  mib_export_test_image: absent
  nvidia_smi: not_found
  proc_driver_nvidia_version: absent
  adapter_dir: /tmp/mib-real-adapter/adapter
  adapter_files_present: false
  strict_model_cache_ready: true

files:
  refreshed_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
    - artifacts/review/v0_release_blocker_recertification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  docker_daemon_available_ok: true
  strict_model_cache_files_ok: true
  blockers:
    - docker_base_image_env_digest
    - cuda_visible
    - docker_base_image_available

m6_prereq:
  status: NOT_READY_PRECHECK_FAILED
  errors:
    - adapter_safetensors_present
    - adapter_config_present
    - adapter_manifest_present
    - docker_image_available: No such image: mib-export:test
    - host_cuda_visible: nvidia-smi not found

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  blocking_reasons_removed:
    - docker_daemon_available

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

follow_up:
  external_cuda_operator_packet_refresh_required: true
  reason: this recertification changed source-pinned handoff and blocker artifacts after packet source commit 29392d5
```

```yaml
gate: mib-studio-post-strict-cache-external-cuda-packet-refresh
objective: refresh external CUDA operator packet verification after strict-cache recertification changed source-pinned handoff artifact hashes

source_head: 29392d5
previous_packet_source_head: a1dd0cc
packet_timestamp_utc: "2026-06-22T20:01:03.059836+00:00"
verification_timestamp_utc: "2026-06-22T20:01:16.251401+00:00"

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_hash_paths:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: 29392d5
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
    - scripts/prepare_strict_model_cache.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: 29392d5
  required_file_hashes: verified 17 required file hashes
  required_commit_blobs: verified 17 required file blobs at 29392d5
  forbidden_tracked_artifacts: []

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-strict-model-cache-ready-recertification
objective: record strict Phi-3.5 model cache readiness from the prepared /tmp cache and refresh current expected NOT_GO release diagnostics

source_head: d13a1fa
pre_phase_download:
  command_status: READY_STRICT_MODEL_CACHE
  cache_dir: /tmp/mib-strict-model-cache-phi/model_cache/microsoft__Phi-3.5-mini-instruct@2fe192450127e6a83f7441aef6e3ca586c338b77
  repository_model_cache_files_committed: false

files:
  refreshed_artifacts:
    - artifacts/review/strict_model_cache_preparation.json
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
    - artifacts/review/v0_release_blocker_recertification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

strict_model_cache:
  status: READY_STRICT_MODEL_CACHE
  cache_ready: true
  download_allowed_for_repo_artifact: false
  required_file_count: 5
  missing_files: []
  downloaded_files: []
  release_claimed_go: false

training_preflight:
  status: NOT_READY_CUDA_LORA_TRAINING
  strict_model_cache_files_ok: true
  blockers:
    - docker_base_image_env_digest
    - cuda_visible
    - docker_daemon_available
    - docker_base_image_available

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS
  blocking_reasons_removed:
    - strict_model_cache_files

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false
  model_cache_files_committed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

follow_up:
  external_cuda_operator_packet_refresh_required: true
  reason: this recertification changed source-pinned handoff and blocker artifacts after the previous packet refresh
```

```yaml
gate: mib-studio-current-head-external-cuda-packet-refresh
objective: restore external CUDA operator packet verification after current-head recertification changed required handoff artifact hashes

source_head: a1dd0cc
previous_packet_source_head: 222f00c
packet_timestamp_utc: "2026-06-22T19:43:19.369434+00:00"
verification_timestamp_utc: "2026-06-22T19:43:23.734778+00:00"

pre_audit:
  old_packet_current_checkout_verification: NOT_GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  blocker: required_committed_file_hashes
  stale_hash_paths:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json

files:
  regenerated_operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  git_head: a1dd0cc
  release_claimed_go: false
  m6_rc_claimed_go: false
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
    - scripts/prepare_strict_model_cache.py

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  verification_ok: true
  operator_packet_ready: true
  warnings: []
  packet_handoff_source_commit: a1dd0cc
  required_file_hashes: verified 17 required file hashes
  required_commit_blobs: verified 17 required file blobs at a1dd0cc
  forbidden_tracked_artifacts: []

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - external CUDA operator packet now matches current checkout required-file hashes after a1dd0cc recertification
  - packet verifier is GO again for 17 current file hashes and 17 a1dd0cc commit blobs
  - this phase does not create real adapter evidence and does not change release readiness
```

```yaml
gate: mib-studio-current-head-20701d1-blocker-recertification
objective: refresh current-head release blocker diagnostics and rerun strict venv bootstrap smoke verification

source_head: 20701d1
recertification_timestamp_utc: "2026-06-22T19:35:02.438007+00:00"

files:
  regenerated_verification_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/v0_release_blocker_recertification.json
  bootstrap_artifacts_verified:
    - artifacts/review/toolchain_report.json
    - artifacts/security/model_manifest_verification.json
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
    - artifacts/security/pii_holdout_report.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

environment:
  python_venv: .venv
  venv_gitignored: true
  toolchain_strict: true
  toolchain_checks:
    node: true
    pnpm: true
    python: true
    rust: true
    sqlite: true
  bootstrap_smoke: passed
  bootstrap_command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install

recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  failed_step: null
  release_claimed_go: false
  m6_rc_claimed_go: false
  candidate_scan_decision: NO_GO_CANDIDATES_FOUND
  go_candidate_count: 0
  fixture_like_candidate_count: 0
  cuda_training_status: NOT_READY_CUDA_LORA_TRAINING
  m6_rc_prereq_status: NOT_READY_PRECHECK_FAILED
  bundle_decision: NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS

blocking_reasons:
  - no_go_adapter_candidates
  - docker_base_image_env_digest
  - strict_model_cache_files
  - cuda_visible
  - docker_daemon_available
  - docker_base_image_available
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - docker_image_available
  - host_cuda_visible
  - endpoint_live_no_fake_json
  - endpoint_markdown_present
  - adapter_intake_go
  - adapter_hash_crosscheck
  - rc_gate_go
  - m6_verification_go
  - real_trained_adapter_no_fake_endpoint
  - WAITING_FOR_REAL_ADAPTER_INPUTS

code_shape:
  files_checked: 119
  violations: []
  import_boundary_violations: []

scope:
  product_code_changed: false
  tests_changed: false
  scripts_changed: false
  release_criteria_changed: false
  docs_reviews_M6_changed: false
  real_adapter_evidence_created: false

verification:
  recertification_unit_tests: 2 passed
  py_compile_recertification_script: passed
  strict_bootstrap_m1_smoke: 1 passed, 3 warnings
  recertification_command: passed
  recertification_expected_status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  toolchain_mismatch: false

summary:
  - current HEAD 20701d1 was recertified after code-shape cleanup
  - strict bootstrap m1-smoke was rerun with repo-local .venv and /tmp/corepack and passed
  - v0 readiness still has no unexpected blockers
  - release remains NOT_GO until accepted real trained CUDA lora_adapter no-fake Docker endpoint evidence exists
```

```yaml
gate: mib-studio-dataset-gen-worker-validation-extraction
objective: resolve the dataset_gen.py code-shape soft warning without behavior changes

files:
  worker_handlers:
    - services/worker/handlers/dataset_gen.py
    - services/worker/handlers/dataset_gen_contracts.py
    - services/worker/handlers/dataset_gen_validation.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  dataset_gen_before_lines: 331
  dataset_gen_after_lines: 237
  dataset_gen_contracts_lines: 29
  dataset_gen_validation_lines: 77
  worker_handler_soft_warning_threshold: 260
  dataset_gen_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  contracts_extracted: true
  generated_example_validation_extracted: true
  run_dataset_gen_job_behavior_changed: false
  teacher_packet_semantics_changed: false
  audit_event_semantics_changed: false
  db_schema_changed: false
  tests_changed: false

verification:
  py_compile: passed
  focused_teacher_synthetic_tests: 7 passed, 26 warnings
  import_boundary_violations: []

code_shape:
  files_checked: 119
  hard_limit_violations: 0
  soft_warnings_remaining: []
  code_shape_violations: []

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - DatasetGenResult, DatasetGenWorkerError, and TeacherSyntheticClient moved into dataset_gen_contracts.py
  - teacher synthetic generated-example validation moved into dataset_gen_validation.py
  - dataset_gen.py keeps worker orchestration, teacher packet checks, dataset persistence, JobEvent, and AuditEvent behavior
  - code-shape report now has violations: []
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-training-service-read-model-extraction
objective: resolve the training_service.py code-shape soft warning without behavior changes

files:
  api_services:
    - services/api/app/services/training_service.py
    - services/api/app/services/training_read_models.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  training_service_before_lines: 277
  training_service_after_lines: 259
  training_read_models_lines: 27
  service_soft_warning_threshold: 260
  training_service_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  model_run_read_conversion_extracted: true
  training_service_public_api_changed: false
  api_schema_changed: false
  db_schema_changed: false
  tests_changed: false

verification:
  py_compile: passed
  focused_training_preflight_tests: 4 passed, 8 warnings
  import_boundary_violations: []

code_shape:
  files_checked: 117
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/worker/handlers/dataset_gen.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - ModelRun ORM-to-schema conversion moved into training_read_models.py
  - TrainingService keeps the same public methods and still resolves current job id through TrainingStore
  - focused train submission/list/read preflight tests pass
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-dataset-service-read-model-extraction
objective: resolve the dataset_service.py code-shape soft warning without behavior changes

files:
  api_services:
    - services/api/app/services/dataset_service.py
    - services/api/app/services/dataset_read_models.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  verified_bootstrap_artifacts:
    - artifacts/review/toolchain_report.json
    - artifacts/security/model_manifest_verification.json
    - artifacts/security/pii_holdout_report.json
    - artifacts/security/pip_audit_cuda.json
    - artifacts/security/pip_audit_cuda_exceptions.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  dataset_service_before_lines: 264
  dataset_service_after_lines: 237
  dataset_read_models_lines: 36
  service_soft_warning_threshold: 260
  dataset_service_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  read_model_conversion_extracted: true
  dataset_service_public_api_changed: false
  api_schema_changed: false
  db_schema_changed: false
  tests_changed: false

verification:
  py_compile: passed
  focused_dataset_tests: 4 passed, 5 warnings
  strict_m1_smoke_bootstrap: passed, 1 passed, 3 warnings
  toolchain_checks_all_true: true
  pip_audit_cuda_status: skipped_in_skip_install_environment
  import_boundary_violations: []

code_shape:
  files_checked: 116
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/worker/handlers/dataset_gen.py
    - services/api/app/services/training_service.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - Dataset/Example ORM-to-schema conversion moved into dataset_read_models.py
  - DatasetService keeps the same public methods and delegates read conversion to the focused helper
  - strict bootstrap m1-smoke now passes with .venv and /tmp/corepack; toolchain checks are all true
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-training-store-status-transitions-extraction
objective: resolve the training_store.py code-shape soft warning without behavior changes

files:
  shared_db_repositories:
    - services/shared/db/repositories/training_store.py
    - services/shared/db/repositories/training_status_store.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  training_store_before_lines: 312
  training_store_after_lines: 240
  training_status_store_lines: 141
  default_soft_warning_threshold: 260
  training_store_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  status_transitions_extracted: true
  training_store_public_api_changed: false
  db_schema_changed: false
  tests_changed: false

code_shape:
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/worker/handlers/dataset_gen.py
    - services/api/app/services/dataset_service.py
    - services/api/app/services/training_service.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - TrainingStore status transition and JobEvent writing logic moved into TrainingStatusStore
  - TrainingStore keeps the same public methods and delegates to the focused helper
  - focused CUDA, MLX, checkpoint/resume, CUDA OOM, and dry-run training tests pass
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-current-head-222f00c-external-cuda-operator-packet-refresh
objective: refresh the external CUDA operator packet after the current-head recertification closeout

files:
  packet_outputs:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

packet:
  source_commit: 222f00c
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  release_claimed_go: false
  m6_rc_claimed_go: false

verification:
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  verification_ok: true
  warnings: []
  required_file_hashes: verified 17 required file hashes
  required_commit_blobs: verified 17 required file blobs at 222f00c
  forbidden_tracked_artifacts: []

release_status:
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - external CUDA operator packet now pins required committed file hashes to source commit 222f00c
  - verifier confirms packet integrity GO and 17 required file blobs at 222f00c
  - primary external handoff remains the verified launcher
  - this phase does not create real adapter evidence and does not claim M6-RC or v0 release GO
```

```yaml
gate: mib-studio-v0-current-head-d28b071-blocker-recertification
objective: refresh current-head v0 release blocker diagnostics after export adapter validation refactor

files:
  recertification_outputs:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_blocker_recertification.json
  handoff_outputs:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

source_head: d28b071
recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS

bootstrap_recheck:
  command: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  status: passed
  toolchain_report: artifacts/review/toolchain_report.json
  toolchain_checks_all_true: true
  m1_smoke_pytest: 1 passed, 3 warnings
  pip_audit_cuda: skipped in --skip-install environment; run without --skip-install for required network-backed audit

current_missing_inputs:
  - real adapter candidate
  - digest-pinned CUDA/Python Docker base image
  - strict pinned Phi model cache files
  - CUDA visibility on the execution host
  - Docker daemon and required Docker images
  - no-fake live endpoint JSON/Markdown evidence
  - accepted M6 RC evidence verification

operator_next_step:
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  meaning: run this on the external CUDA host; it verifies the operator packet before invoking the lower-level training handoff

summary:
  - current HEAD d28b071 was recertified after export adapter validation refactor
  - release readiness still has no unexpected blockers
  - hook-reported strict bootstrap m1-smoke verification was rerun and passed with .venv plus /tmp/corepack
  - current NOT_GO remains expected and evidence-driven
  - no product code, verifier criteria, M6 review GO docs, model weights, adapter files, Docker images, endpoint transcripts, or evidence bundles were changed
```

```yaml
gate: mib-studio-export-adapter-validation-extraction
objective: resolve the M6 zip export worker code-shape soft warning without behavior changes

files:
  worker_handlers:
    - services/worker/handlers/export.py
    - services/worker/handlers/export_adapter_validation.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  export_worker_before_lines: 351
  export_worker_after_lines: 235
  export_adapter_validation_lines: 142
  worker_handler_soft_warning_threshold: 260
  export_worker_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  adapter_validation_extracted: true
  export_manifest_changed: false
  adapter_acceptance_rules_changed: false
  db_schema_changed: false
  tests_changed: false

code_shape:
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/shared/db/repositories/training_store.py
    - services/worker/handlers/dataset_gen.py
    - services/api/app/services/dataset_service.py
    - services/api/app/services/training_service.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - ExportError and adapter required-path, file-format, and lineage validation moved into export_adapter_validation.py
  - services/worker/handlers/export.py now stays below the worker handler soft warning threshold
  - focused export API, export manifest, and docker security tests pass
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-v0-current-head-d68ebb8-blocker-recertification
objective: refresh current-head v0 release blocker diagnostics after benchmark validation refactor

files:
  recertification_outputs:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_blocker_recertification.json
  handoff_outputs:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

source_head: d68ebb8
recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS

current_missing_inputs:
  - real adapter candidate
  - digest-pinned CUDA/Python Docker base image
  - strict pinned Phi model cache files
  - CUDA visibility on the execution host
  - Docker daemon and required Docker images
  - no-fake live endpoint JSON/Markdown evidence
  - accepted M6 RC evidence verification

operator_next_step:
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  meaning: run this on the external CUDA host; it verifies the operator packet before invoking the lower-level training handoff

summary:
  - current HEAD d68ebb8 was recertified after benchmark validation refactor
  - release readiness still has no unexpected blockers
  - current NOT_GO remains expected and evidence-driven
  - no product code, verifier criteria, M6 review GO docs, model weights, adapter files, Docker images, endpoint transcripts, or evidence bundles were changed
```

```yaml
gate: mib-studio-dataset-job-benchmark-validation-extraction
objective: resolve the dataset_job_service.py code-shape soft warning without behavior changes

files:
  api_services:
    - services/api/app/services/dataset_job_service.py
    - services/api/app/services/benchmark_job_validation.py
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
    - artifacts/review/import_boundary_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  dataset_job_service_before_lines: 380
  dataset_job_service_after_lines: 256
  benchmark_job_validation_lines: 156
  service_soft_warning_threshold: 260
  dataset_job_service_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  benchmark_validation_extracted: true
  api_contract_changed: false
  benchmark_acceptance_rules_changed: false
  db_schema_changed: false
  tests_changed: false

code_shape:
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/shared/db/repositories/training_store.py
    - services/worker/handlers/export.py
    - services/worker/handlers/dataset_gen.py
    - services/api/app/services/dataset_service.py
    - services/api/app/services/training_service.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - BenchmarkParams parsing, benchmark EvalSet checks, and benchmark target validation moved into benchmark_job_validation.py
  - dataset_job_service.py now stays below the service soft warning threshold
  - focused benchmark submit and M1 smoke tests pass
  - this phase does not change release readiness or create real adapter evidence
```

```yaml
gate: mib-studio-v0-current-head-blocker-recertification
objective: refresh current-head v0 release blocker diagnostics after FE v6 and strict bootstrap verification

files:
  recertification_outputs:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_blocker_recertification.json
  handoff_outputs:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

source_head: 6dac1ef
recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  handoff_decision: WAITING_FOR_REAL_ADAPTER_INPUTS

current_missing_inputs:
  - real adapter candidate
  - digest-pinned CUDA/Python Docker base image
  - strict pinned Phi model cache files
  - CUDA visibility on the execution host
  - Docker daemon and required Docker images
  - no-fake live endpoint JSON/Markdown evidence
  - accepted M6 RC evidence verification

operator_next_step:
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  meaning: run this on the external CUDA host; it verifies the operator packet before invoking the lower-level training handoff

summary:
  - current HEAD 6dac1ef was recertified after FE v6 workflow extraction and strict bootstrap m1-smoke verification
  - release readiness still has no unexpected blockers
  - current NOT_GO remains expected and evidence-driven
  - no product code, verifier criteria, M6 review GO docs, model weights, adapter files, Docker images, endpoint transcripts, or evidence bundles were changed
```

```yaml
gate: mib-studio-strict-bootstrap-m1-smoke-reverify
objective: re-run the hook-reported strict bootstrap m1-smoke command with repo-local .venv and /tmp/corepack

files:
  pabcd_contract:
    - .codex/tasks/current.json
  regenerated_verification_artifacts:
    - artifacts/review/file_size_report.json
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

baseline:
  source_head: a620943
  command_rechecked: COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install

bootstrap_result:
  command_status: passed
  toolchain_mismatch_reproduced: false
  toolchain_report:
    strict: true
    node: 20.18.1
    pnpm: 9.15.0
    python: 3.11.15
    rust: rustc 1.83.0
    sqlite: 3.50.4
    checks_all_true: true
  m1_smoke:
    pytest_file: tests/smoke/test_m1_smoke.py
    result: 1 passed
    warnings:
      - FastAPI ORJSONResponse deprecation warnings only
  pip_audit_cuda:
    status: skipped
    reason: skip-install environment could not complete pip-audit upgrade; run without --skip-install for required network-backed audit

code_shape:
  file_size_report_updated: true
  hard_limit_violations: 0
  soft_warnings_remaining:
    - services/shared/db/repositories/training_store.py
    - services/worker/handlers/export.py
    - services/worker/handlers/dataset_gen.py
    - services/api/app/services/dataset_service.py
    - services/api/app/services/dataset_job_service.py
    - services/api/app/services/training_service.py

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - the exact hook-reported strict bootstrap command now passes on current checkout
  - current toolchain_report.json has strict=true and all toolchain checks true
  - this phase does not change product runtime behavior or release readiness
  - remaining final-release work still requires accepted real adapter no-fake endpoint evidence
```

```yaml
gate: mib-studio-fe-workflow-view-extraction
objective: remove the FE desktop main.mjs 900+ God File soft warning by extracting workflow view rendering

files:
  frontend_shell:
    - apps/desktop/src/main.mjs
  frontend_workflow_views:
    - apps/desktop/src/lib/workflowViews.mjs
  llm_context:
    - docs/WORKING.md
    - docs/plans/2026-05-09_COMPLETION_LOG.md

line_counts:
  main_before_lines: 921
  main_after_lines: 884
  workflowViews_lines: 69
  main_soft_warning_threshold: 900
  main_below_soft_warning_threshold: true

scope:
  behavior_preserving: true
  package_playground_rendering_extracted: true
  export_rendering_extracted: true
  backend_api_contract_changed: false
  tests_or_mock_data_changed: false

release_status:
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_release_ready: false
  expected_local_decision: NOT_GO
  sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - Package, Playground, and Export page rendering moved from main.mjs into workflowViews.mjs
  - main.mjs remains the desktop shell and route dispatcher
  - workflowViews.mjs owns only FE rendering for Package/Playground and Export surfaces
  - this phase does not create or validate real adapter, endpoint, Docker, benchmark, package, export, or release evidence
```

```yaml
gate: mib-studio-v0-current-head-release-blocker-recertification
objective: refresh current-head v0 release blocker diagnostics after FE v6 Export workflow unlock

files:
  recertification_outputs:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_blocker_recertification.json
  handoff_outputs:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

current_head: 2686c78
recertification:
  status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  recertification_ok: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  v0_readiness_decision: NOT_GO
  v0_release_ready: false
  v0_unexpected_blockers: []
  sole_v0_blocker: real_trained_adapter_no_fake_endpoint

current_missing_inputs:
  - real adapter candidate
  - digest-pinned CUDA/Python Docker base image
  - strict pinned Phi model cache files
  - CUDA visibility on the execution host
  - Docker daemon and required Docker images
  - no-fake live endpoint JSON/Markdown evidence
  - accepted M6 RC evidence verification

operator_next_step:
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  meaning: run this on the external CUDA host; it verifies the operator packet before invoking the lower-level training handoff

summary:
  - current HEAD was recertified after FE v6 Export workflow unlock
  - release readiness still has no unexpected blockers
  - current NOT_GO remains expected and evidence-driven
  - no product code, verifier criteria, M6 review GO docs, model weights, adapter files, Docker images, endpoint transcripts, or evidence bundles were changed
```

```yaml
gate: mib-studio-fe-v6-export-workflow-unlock
objective: unlock the desktop FE v6 Export workflow using existing export APIs

files:
  frontend_model:
    - apps/desktop/src/lib/appModel.mjs
    - apps/desktop/src/lib/appModel.test.mjs
  frontend_api_client:
    - apps/desktop/src/lib/apiClient.mjs
    - apps/desktop/src/lib/apiClient.test.mjs
  desktop_shell:
    - apps/desktop/src/main.mjs
  browser_mock_and_e2e:
    - apps/desktop/e2e/mockApi.mjs
    - apps/desktop/e2e/m1_happy_path.test.mjs
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

export_workflow_contract:
  route: /projects/{id}/export
  required_frontend_gates:
    - existing AgentPackage
  backend_apis_used:
    - listAgentPackages: GET /projects/{id}/agent-packages
    - createExport: POST /projects/{id}/export
    - getExport: GET /exports/{job_id}
    - revealExportArtifact: POST /exports/{job_id}/reveal
  export_request:
    export_type: zip
  release_boundary:
    browser_mock_export_is_release_evidence: false
    m6_rc_go_claimed: false
    v0_release_go_claimed: false

verification:
  desktop_model_and_api_client: passed
  desktop_e2e_m1_happy_path_with_export: passed
  backend_export_api: passed
  release_claimed_go: false

summary:
  - desktop route parsing and workflow stepper expose /projects/{id}/export after an AgentPackage exists
  - Export page submits zip export through existing daemon APIs and displays daemon-provided ExportRead hashes and URLs
  - reveal action calls existing daemon reveal endpoint and never creates or edits export artifacts locally
  - browser mock path reaches Export after Package and Playground while preserving no-release-evidence labeling
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-fe-v6-package-playground-workflow-unlock
objective: unlock the desktop FE v6 Package and Playground workflow using existing agent-package and playground APIs

files:
  frontend_model:
    - apps/desktop/src/lib/appModel.mjs
    - apps/desktop/src/lib/appModel.test.mjs
  frontend_api_client:
    - apps/desktop/src/lib/apiClient.mjs
    - apps/desktop/src/lib/apiClient.test.mjs
    - apps/desktop/src/lib/generated.ts
  desktop_shell:
    - apps/desktop/src/main.mjs
  browser_mock_and_e2e:
    - apps/desktop/e2e/mockApi.mjs
    - apps/desktop/e2e/m1_happy_path.test.mjs
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

package_playground_contract:
  route: /projects/{id}/packages
  required_frontend_gates:
    - completed ModelRun with adapter metadata
    - completed Benchmark with hash_status=VALID
  backend_apis_used:
    - listAgentPackages: GET /projects/{id}/agent-packages
    - createAgentPackage: POST /projects/{id}/agent-packages
    - getAgentPackage: GET /agent-packages/{agent_package_id}
    - runPlayground: POST /agent-packages/{agent_package_id}/playground-runs
  package_request:
    agent_slug: support_router
    fallback:
      enabled: false
      provider: none
      condition:
        type: disabled

verification:
  desktop_model_and_api_client: passed
  desktop_e2e_m1_happy_path_with_package_playground: passed
  backend_agent_package_contract_builder: passed
  backend_playground_local_inference: passed
  release_claimed_go: false

summary:
  - desktop route parsing and workflow stepper now expose /projects/{id}/packages after a valid benchmark report
  - Package page builds an AgentPackage through the existing API and displays backend-created contract_yaml without local edits
  - Playground action calls the existing local daemon playground endpoint and displays verifier status, fallback flags, output JSON, and audit id
  - browser mock path now reaches Package and Playground after Train and AgentBench while preserving no-release-evidence labeling
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-fe-v6-benchmark-workflow-unlock
objective: unlock the FE v6 AgentBench workflow by enabling backend benchmark job queueing and wiring desktop Benchmark UI to existing report APIs

files:
  backend_submit:
    - services/api/app/schemas/job.py
    - services/api/app/services/dataset_job_service.py
  backend_tests:
    - tests/eval/test_benchmark_submit.py
  frontend_model:
    - apps/desktop/src/lib/appModel.mjs
    - apps/desktop/src/lib/appModel.test.mjs
  frontend_api_client:
    - apps/desktop/src/lib/apiClient.mjs
    - apps/desktop/src/lib/apiClient.test.mjs
  desktop_shell:
    - apps/desktop/src/main.mjs
  browser_mock_and_e2e:
    - apps/desktop/e2e/mockApi.mjs
    - apps/desktop/e2e/m1_happy_path.test.mjs
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

benchmark_workflow_contract:
  route: /projects/{id}/benchmarks/new
  backend_submit:
    endpoint: POST /projects/{id}/jobs
    type: benchmark
    creates:
      - Job(type=benchmark, resource_class=gpu_exclusive, status=QUEUED)
      - Benchmark(status=QUEUED, parity_status=NA)
      - JobResource(resource_type=benchmark)
    requires:
      - frozen benchmark_gold or finance_reference EvalSet with sample_count >= 200
      - one completed fine_tuned ModelRun with adapter_sha256 and artifact_manifest_sha256, or two for CUDA/MLX parity
      - exactly one prompt_only, teacher, and rule_based target
      - at least three unique seeds
  desktop_apis_used:
    - submitProjectJob: POST /projects/{id}/jobs
    - listModelRuns: GET /projects/{id}/model-runs
    - listEvalSets: GET /projects/{id}/eval-sets
    - listBenchmarks: GET /projects/{id}/benchmarks
    - getBenchmarkReport: GET /benchmarks/{id}/report

verification:
  backend_benchmark_submit: passed
  desktop_model_and_api_client: passed
  desktop_e2e_m1_happy_path_with_train_and_benchmark: passed
  release_claimed_go: false

summary:
  - backend now queues valid benchmark jobs instead of returning MILESTONE_LOCKED for type=benchmark
  - desktop route parsing and workflow stepper now expose /projects/{id}/benchmarks/new after completed ModelRun readiness
  - AgentBench page displays target contract, gate status, benchmark list, and daemon/worker report data without manual benchmark numbers
  - browser mock report is explicitly labeled mock-only and is not release evidence
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-fe-v6-train-workflow-unlock
objective: unlock the desktop FE v6 Train workflow route using existing project training job and model-run APIs

files:
  frontend_model:
    - apps/desktop/src/lib/appModel.mjs
    - apps/desktop/src/lib/appModel.test.mjs
  frontend_api_client:
    - apps/desktop/src/lib/apiClient.mjs
    - apps/desktop/src/lib/apiClient.test.mjs
  desktop_shell:
    - apps/desktop/src/main.mjs
  browser_mock_and_e2e:
    - apps/desktop/e2e/mockApi.mjs
    - apps/desktop/e2e/m1_happy_path.test.mjs
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

train_workflow_contract:
  route: /projects/{id}/training
  required_frontend_gates:
    - approved dataset
    - Hardware Doctor training_enabled result
  backend_apis_used:
    - submitProjectJob: POST /projects/{id}/jobs
    - listModelRuns: GET /projects/{id}/model-runs
  train_request_fields:
    - type: train
    - preset_id
    - dataset_id
    - base_model: google/gemma-2b-it
    - backend
    - training_preset: balanced
    - seed: 123

verification:
  desktop_model_and_api_client: passed
  desktop_e2e_m1_happy_path_with_train: passed
  release_claimed_go: false

summary:
  - desktop route parsing and workflow stepper now expose /projects/{id}/training after dataset approval and Hardware Doctor readiness
  - Train page displays the submission contract, gate status, queued job notice, and model-run table while delegating execution to the existing daemon/worker API path
  - mock browser happy path now builds and approves a dataset, runs Hardware Doctor, submits a train job, sees model_run_1, and opens job_train_1
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-fe-v6-route-contract-persistence
objective: preserve canonical FE v6 route contract fields through project save/reload and dataset route snapshots

files:
  backend_project_contract:
    - services/api/app/schemas/project.py
    - services/api/app/services/project_service.py
    - services/shared/db/models/project.py
    - services/shared/db/repositories/dataset_store.py
  frontend_v6_contract:
    - apps/desktop/src/lib/appModel.mjs
    - apps/desktop/e2e/fe_v6_route_contract.test.mjs
  generated_contracts:
    - schemas/openapi.json
    - apps/desktop/src/lib/generated.ts
  tests:
    - tests/api/test_projects.py
    - tests/dataset/test_dataset_builder.py
    - apps/desktop/src/lib/appModel.test.mjs

v6_route_contract_fields_persisted:
  - task_type
  - requires_calculation
  - requires_human_review
  - is_default
  - examples

verification:
  api_dataset: 9 passed
  desktop_model: passed
  desktop_e2e_v6_route_contract: passed
  openapi_drift: ok

summary:
  - project API/DB now stores and returns v6 route contract fields instead of only route_id/description/is_unsafe
  - desktop routesToProjectInput/routesFromProject round-trip the v6 fields, including examples, through save/reload
  - dataset route_snapshot_json now includes the v6 route contract fields for downstream traceability
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-checkout-guidance
objective: clarify that packet.git.head is a required-file source commit, not an operator checkout target

files:
  packet_generator: scripts/build_external_cuda_operator_packet.py
  packet_generator_tests: tests/scripts/test_build_external_cuda_operator_packet.py
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: c38ff33
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  required_committed_files_count: 17
  commit_blob_check_detail: verified 17 required file blobs at c38ff33
  verification_warnings: []
  operator_sequence_rule:
    - keep this packet file from the current checkout
    - packet.git.head is the required committed file source commit for verifier blob checks

summary:
  - operator packet no longer tells external CUDA operators to checkout packet.git.head before using the packet
  - packet.git.head is now described as the required-file blob verification source commit
  - packet verification remains GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION for packet integrity only
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-primary-verified-launcher
objective: make the verified external CUDA launcher the packet primary operator handoff

files:
  packet_generator: scripts/build_external_cuda_operator_packet.py
  packet_generator_tests: tests/scripts/test_build_external_cuda_operator_packet.py
  packet_verifier: scripts/verify_external_cuda_operator_packet.py
  packet_verifier_tests: tests/scripts/test_verify_external_cuda_operator_packet.py
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: 10ea0cb
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  recertification_primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  required_committed_files_count: 17
  commit_blob_check_detail: verified 17 required file blobs at 10ea0cb
  verification_warnings: []

summary:
  - operator packet primary_external_handoff now points to the verified launcher, so packet metadata no longer tells operators to bypass packet verification
  - verifier rejects packets whose primary_external_handoff is the lower-level training handoff
  - packet still records the training handoff as downstream_training_handoff and as a required committed file
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-stable-head-warning
objective: keep commit-pinned external CUDA packet verification warning-free after later closeout commits

files:
  packet_verifier: scripts/verify_external_cuda_operator_packet.py
  packet_verifier_tests: tests/scripts/test_verify_external_cuda_operator_packet.py
  operator_packet_verification:
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_verification:
  schema_version: mib_external_cuda_operator_packet_verification.v1
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  release_claimed_go: false
  m6_rc_claimed_go: false
  packet_handoff_source_commit: 65dfd1a
  required_committed_files_count: 17
  commit_blob_check_detail: verified 17 required file blobs at 65dfd1a
  verification_warnings: []
  current_checkout_after_packet_head_allowed_when_commit_blobs_verify: true

summary:
  - verifier still requires packet.git.head to resolve and still validates required file blobs at the packet handoff source commit
  - verifier no longer warns merely because the current checkout has advanced after the packet handoff source commit
  - refreshed packet verification is warning-free at current HEAD while packet remains pinned to 65dfd1a
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-source-refresh-65dfd1a
objective: refresh packet evidence to the latest verified-launcher required-file source commit

files:
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: 65dfd1a
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - scripts/prepare_strict_model_cache.py
  commit_blob_check_detail: verified 17 required file blobs at 65dfd1a
  verification_warnings: []

summary:
  - operator packet now pins source commit 65dfd1a, the commit containing the verified launcher required-file packet contract
  - packet verification remains GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION for packet integrity only
  - verifier warnings are empty from the current checkout
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-launcher-required-file
objective: make the verified external CUDA launcher shell part of the packet required committed file set

files:
  packet_generator: scripts/build_external_cuda_operator_packet.py
  packet_generator_tests: tests/scripts/test_build_external_cuda_operator_packet.py
  packet_verifier: scripts/verify_external_cuda_operator_packet.py
  packet_verifier_tests: tests/scripts/test_verify_external_cuda_operator_packet.py
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: f2227bf
  required_committed_files_count: 17
  required_committed_files_include:
    - artifacts/review/verified_external_cuda_training_launcher.sh
    - scripts/prepare_strict_model_cache.py
  commit_blob_check_detail: verified 17 required file blobs at f2227bf
  primary_external_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  recertification_primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh

summary:
  - operator packet required_committed_files now includes artifacts/review/verified_external_cuda_training_launcher.sh
  - packet verifier now rejects packets missing the verified launcher required path
  - packet verification remains GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION for packet integrity only
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-packet-source-commit-guard
objective: make the external CUDA operator packet reject stale handoff source commits

files:
  verifier: scripts/verify_external_cuda_operator_packet.py
  verifier_tests: tests/scripts/test_verify_external_cuda_operator_packet.py
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: 51b2d97
  required_committed_files_count: 16
  required_commit_blob_check: required_committed_file_commit_blobs
  commit_blob_check_detail: verified 16 required file blobs at 51b2d97
  primary_external_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh

summary:
  - verifier now checks every required_committed_files entry against both the current checkout file and the packet.git.head commit blob
  - focused tests cover a stale packet.git.head where scripts/prepare_strict_model_cache.py exists in the working tree but not in the pinned commit
  - external CUDA operator packet now pins handoff source commit 51b2d97, the commit containing scripts/prepare_strict_model_cache.py
  - packet verification remains GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION for packet integrity only
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-strict-model-cache-handoff
objective: make strict base-model cache preparation a repo-local external CUDA handoff command

files:
  strict_model_cache_cli: scripts/prepare_strict_model_cache.py
  strict_model_cache_tests: tests/scripts/test_prepare_strict_model_cache.py
  training_handoff_generator: scripts/prepare_cuda_lora_training_run.py
  generated_training_handoff:
    - artifacts/review/real_adapter_cuda_training_handoff.json
    - artifacts/review/real_adapter_cuda_training_handoff.md
    - artifacts/review/real_adapter_cuda_training_handoff.sh
  operator_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
    - artifacts/review/external_cuda_operator_packet_verification.json
  recertification_summary: artifacts/review/v0_release_blocker_recertification.json
  strict_model_cache_report: artifacts/review/strict_model_cache_preparation.json

strict_model_cache_contract:
  schema_version: mib_strict_model_cache_preparation.v1
  historical_status_at_gate: NOT_READY_STRICT_MODEL_CACHE
  no_download_default: true
  explicit_download_flag: --allow-download
  required_model_cache_dir: /tmp/mib-strict-model-cache-phi/model_cache
  required_base_model: microsoft/Phi-3.5-mini-instruct
  required_status_before_training_preflight: READY_STRICT_MODEL_CACHE
  release_claimed_go: false

handoff_contract:
  training_command_order_prefix:
    - resolve_cuda_base_image
    - prepare_strict_model_cache
    - preflight_cuda_training
  packet_required_committed_files_count: 16
  packet_required_committed_files_include:
    - scripts/prepare_strict_model_cache.py
  packet_verification_decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  recertification_action: run prepare_strict_model_cache.py with --allow-download before CUDA training preflight

summary:
  - prepare_strict_model_cache.py exposes the existing pinned ModelCacheService as an operator CLI
  - default no-download mode reported NOT_READY_STRICT_MODEL_CACHE at this historical gate when required pinned files were absent
  - generated external CUDA training handoff now runs prepare_strict_model_cache before preflight_cuda_training
  - external CUDA operator packet now pins scripts/prepare_strict_model_cache.py and requires prepare_strict_model_cache in command order
  - current recertification remains expected NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 release blocker
  - no model weights, adapter files, Docker images, endpoint transcripts, copied evidence bundles, M6-RC GO, or v0 GO were created
```

```yaml
gate: mib-studio-recertification-verified-launcher-routing
objective: route current recertification operator actions to the verified launcher first

files:
  recertification_tool: scripts/run_v0_release_blocker_recertification.py
  recertification_tests: tests/scripts/test_run_v0_release_blocker_recertification.py
  recertification_summary: artifacts/review/v0_release_blocker_recertification.json
  refreshed_not_go_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

recertification_action_contract:
  primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
  top_level_fields:
    - blocking_reasons
    - operator_next_actions
    - primary_external_handoff
  first_operator_action: run artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host so packet verification runs before training handoff execution

summary:
  - run_v0_release_blocker_recertification.py now emits the verified launcher as primary_external_handoff for missing real-adapter/CUDA setup paths
  - operator_next_actions now names artifacts/review/verified_external_cuda_training_launcher.sh before lower-level training or RC handoff paths
  - focused tests verify current NOT_GO and failed child-command routing to the launcher
  - host-access recertification remains expected NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 release blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-verified-external-cuda-training-launcher
objective: make external CUDA operators run packet verification before real-adapter training handoff execution

files:
  launcher_generator: scripts/build_verified_cuda_training_launcher.py
  launcher_tests: tests/scripts/test_build_verified_cuda_training_launcher.py
  generated_launcher:
    - artifacts/review/verified_external_cuda_training_launcher.json
    - artifacts/review/verified_external_cuda_training_launcher.md
    - artifacts/review/verified_external_cuda_training_launcher.sh
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

launcher_contract:
  schema_version: mib_verified_external_cuda_training_launcher.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  m6_rc_claimed_go: false
  first_command: verify_external_cuda_operator_packet
  required_verifier_decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  second_command: run_real_adapter_cuda_training_handoff
  training_handoff_shell: artifacts/review/real_adapter_cuda_training_handoff.sh
  fake_backend_guard: MIB_RUNTIME_ALLOW_FAKE_BACKEND must be unset

summary:
  - new launcher is the preferred external CUDA host entrypoint
  - launcher runs scripts/verify_external_cuda_operator_packet.py before artifacts/review/real_adapter_cuda_training_handoff.sh
  - focused tests cover command order, guard strings, artifact writing, and no-GO claims
  - launcher remains PREPARED_NOT_RUN and does not claim M6-RC GO or v0 release GO
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-operator-packet-verifier
objective: verify the external CUDA operator packet before real-adapter CUDA execution

files:
  verifier: scripts/verify_external_cuda_operator_packet.py
  verifier_tests: tests/scripts/test_verify_external_cuda_operator_packet.py
  verifier_output: artifacts/review/external_cuda_operator_packet_verification.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_verification:
  schema_version: mib_external_cuda_operator_packet_verification.v1
  decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  operator_packet_ready: true
  release_claimed_go: false
  m6_rc_claimed_go: false
  packet_handoff_source_commit: 51b2d97
  primary_external_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  verified:
    - packet contract and no-GO claims
    - 16 required committed file sha256/size values
    - 16 required committed file blobs at packet_handoff_source_commit
    - 6 package readiness checks
    - training/RC/local-closeout command order
    - forbidden committed artifact labels
    - no forbidden tracked model/adapter/Docker/endpoint/bundle artifacts
  warning: none

summary:
  - verifier gives operators a focused preflight command before running artifacts/review/real_adapter_cuda_training_handoff.sh
  - focused tests cover ready packet, hash mismatch, GO-claiming packet rejection, and forbidden tracked artifact matching
  - verifier GO is packet integrity only and does not claim M6-RC GO or v0 release GO
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-external-cuda-operator-packet
objective: create a commit-pinned external CUDA operator packet for the real-adapter evidence path

files:
  packet_generator: scripts/build_external_cuda_operator_packet.py
  packet_tests: tests/scripts/test_build_external_cuda_operator_packet.py
  generated_packet:
    - artifacts/review/external_cuda_operator_packet.json
    - artifacts/review/external_cuda_operator_packet.md
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

operator_packet_contract:
  schema_version: mib_external_cuda_operator_packet.v1
  status: PREPARED_NOT_RUN
  release_claimed_go: false
  handoff_source_commit: 51b2d97
  primary_external_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  contains_model_or_adapter_artifacts: false
  forbidden_committed_artifacts:
    - model weights
    - LoRA adapter files or /tmp/mib-real-adapter contents
    - Docker image layers or archives
    - raw live endpoint transcripts
    - copied external real-adapter evidence bundles

summary:
  - external CUDA operator packet now anchors the handoff source commit, required committed file sha256 values, package readiness checks, command order, expected return artifacts, and forbidden committed artifacts
  - focused tests verify packet structure, primary handoff, no-GO claims, and GO-claiming artifact rejection
  - generated packet remains PREPARED_NOT_RUN and does not claim M6-RC GO or v0 GO
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-recertification-training-handoff-action
objective: make recertification point to the hardened CUDA training handoff as the first external action

files:
  recertification_tool: scripts/run_v0_release_blocker_recertification.py
  recertification_tests: tests/scripts/test_run_v0_release_blocker_recertification.py
  recertification_summary: artifacts/review/v0_release_blocker_recertification.json
  refreshed_not_go_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

recertification_action_contract:
  primary_external_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
  top_level_fields:
    - blocking_reasons
    - operator_next_actions
    - primary_external_handoff
  first_operator_action: run artifacts/review/real_adapter_cuda_training_handoff.sh on the external CUDA host and require package_readiness_checks before training

summary:
  - run_v0_release_blocker_recertification.py now emits primary_external_handoff for missing real-adapter/CUDA setup paths
  - operator_next_actions now names artifacts/review/real_adapter_cuda_training_handoff.sh before the downstream RC handoff
  - focused tests verify the training handoff action ordering
  - host-access recertification remains expected NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 release blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-cuda-training-handoff-preflight-guards
objective: harden the external CUDA training handoff package before real-adapter execution

files:
  training_handoff_generator: scripts/prepare_cuda_lora_training_run.py
  training_handoff_tests: tests/scripts/test_prepare_cuda_lora_training_run.py
  generated_training_handoff:
    - artifacts/review/real_adapter_cuda_training_handoff.json
    - artifacts/review/real_adapter_cuda_training_handoff.md
    - artifacts/review/real_adapter_cuda_training_handoff.sh
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

package_readiness_checks:
  top_level_field: package_readiness_checks
  shell_guarded_ids:
    - dataset_jsonl_present
    - python_executable_present
    - llamafactory_cli_present
    - model_cache_dir_present
    - backend_config_present
    - rc_handoff_shell_present

summary:
  - generated CUDA training handoff JSON now lists package_readiness_checks for host-execution prerequisites
  - generated shell refuses to run when dataset JSONL, repo Python, LLaMA-Factory CLI, strict model cache, backend_config.yaml, or RC handoff shell is missing
  - focused tests verify the package readiness list and shell guard strings
  - generated training handoff remains PREPARED_NOT_RUN and does not claim M6-RC GO or v0 GO
  - current release blocker remains real_trained_adapter_no_fake_endpoint
```

```yaml
gate: mib-studio-v0-recertification-actionable-blockers
objective: make current release-blocker recertification output directly actionable

files:
  recertification_tool: scripts/run_v0_release_blocker_recertification.py
  recertification_tests: tests/scripts/test_run_v0_release_blocker_recertification.py
  recertification_summary: artifacts/review/v0_release_blocker_recertification.json
  refreshed_not_go_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_readiness_audit.json
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

recertification_summary_contract:
  top_level_fields:
    - blocking_reasons
    - operator_next_actions
  current_status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
  release_claimed_go: false
  current_release_blocker: real_trained_adapter_no_fake_endpoint

summary:
  - run_v0_release_blocker_recertification.py now emits top-level blocking_reasons for current NOT_GO recertification states
  - operator_next_actions maps missing adapter files, strict model cache, CUDA visibility, Docker image/base-image, bundle, endpoint, and handoff blockers to concrete next steps
  - focused recertification tests cover current expected NOT_GO and failed child-command paths
  - host-access recertification remains expected NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 release blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-v0-closeout-actionable-blockers
objective: make failed local closeout summaries directly actionable

files:
  closeout_tool: scripts/run_v0_release_closeout_from_bundle.py
  closeout_tests: tests/scripts/test_run_v0_release_closeout_from_bundle.py
  readiness_audit: artifacts/review/v0_release_readiness_audit.json
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

closeout_summary_contract:
  top_level_fields:
    - blocking_reasons
    - operator_next_actions
  covered_not_go_reasons:
    - archive_metadata_not_verified
    - source_bundle_not_go
    - target_verification_not_go
    - m6_review_docs_not_current
    - real_trained_adapter_no_fake_endpoint
  release_claimed_go: false

summary:
  - run_v0_release_closeout_from_bundle.py now emits top-level blocking_reasons for NOT_GO closeout states
  - operator_next_actions maps metadata, bundle, M6 review-doc, and real endpoint blockers to concrete next steps
  - focused closeout tests cover GO, archive metadata rejection, NOT_GO bundle, and M6 review-doc NOT_GO readiness
  - current v0 readiness remains NOT_GO with real_trained_adapter_no_fake_endpoint as the sole release blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-real-adapter-local-closeout-m6-doc-prereq
objective: make local closeout prerequisites explicit for transferred real-adapter evidence bundles

files:
  handoff_generator: scripts/build_real_adapter_handoff.py
  handoff_tests: tests/scripts/test_build_real_adapter_handoff.py
  generated_handoff:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
  llm_context:
    - docs/CONTEXT.md
    - docs/WORKING.md

local_closeout_prerequisites:
  same_release_workstation_checkout: true
  local_closeout_requires_m6_review_docs_go: true
  m6_review_doc_paths:
    - docs/reviews/M6/SIGNOFF_MATRIX.md
    - docs/reviews/M6/CTO_DECISION.md
  missing_m6_review_docs_go_status: m6_review_docs_not_current
  bundle_archive_alone_is_sufficient: false

summary:
  - generated handoff JSON now exposes local_closeout_prerequisites
  - generated markdown and shell now state that copying the metadata-bearing archive alone is insufficient
  - local closeout requires accepted GO updates to docs/reviews/M6 in the same release workstation checkout
  - if those local docs are not GO, v0 readiness returns m6_review_docs_not_current
  - current recertification remains NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-real-adapter-handoff-archive-metadata-contract
objective: align generated CUDA handoff with the metadata-bearing bundle archive closeout requirement

files:
  handoff_generator: scripts/build_real_adapter_handoff.py
  handoff_tests: tests/scripts/test_build_real_adapter_handoff.py
  generated_handoff:
    - artifacts/review/real_adapter_cuda_handoff.json
    - artifacts/review/real_adapter_cuda_handoff.md
    - artifacts/review/real_adapter_cuda_handoff.sh
  refreshed_not_go_artifacts:
    - artifacts/review/real_adapter_candidate_scan.json
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    - artifacts/review/m6_real_adapter_prereq_audit.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
    - artifacts/review/v0_release_blocker_recertification.json
  working_state: docs/WORKING.md

bundle_archive_contract_in_handoff:
  producer: scripts/build_real_adapter_evidence_bundle.py
  bundle_dir: artifacts/review/real_adapter_evidence_bundle
  bundle_archive_output: artifacts/review/real_adapter_evidence_bundle.tar.gz
  required_metadata_files:
    - artifacts/review/real_adapter_evidence_bundle_manifest.json
    - artifacts/review/real_adapter_evidence_bundle_verification.json
  local_closeout_requires_metadata: true
  missing_or_mismatched_metadata_status: archive_metadata_not_verified
  expected_success_status: GO_V0_RELEASE_CLOSEOUT

summary:
  - generated handoff JSON now exposes bundle_archive_contract for the copied evidence archive
  - generated markdown has a Bundle Archive Contract section and a metadata-bearing local closeout section
  - generated shell tells operators that copied tarballs without builder metadata are rejected with archive_metadata_not_verified
  - focused handoff tests cover JSON, markdown, and shell output for the metadata contract
  - current recertification remains NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 blocker
  - no M6-RC GO or v0 GO is claimed from current local artifacts
```

```yaml
gate: mib-studio-real-adapter-bundle-archive-metadata
objective: require transferred real-adapter evidence bundle archives to include builder metadata before promotion

files:
  promotion_tool: scripts/promote_real_adapter_evidence_bundle.py
  promotion_tests: tests/scripts/test_promote_real_adapter_evidence_bundle.py
  closeout_tests: tests/scripts/test_run_v0_release_closeout_from_bundle.py
  working_state: docs/WORKING.md

archive_metadata_contract:
  required_archive_members:
    - real_adapter_evidence_bundle_manifest.json
    - real_adapter_evidence_bundle_verification.json
  required_consistency:
    - manifest verification_summary matches strict verifier result after extraction
    - verification metadata decision/release_bundle_ready/blockers match strict verifier result after extraction
    - manifest fixed-file sha256 rows match extracted fixed evidence files
  missing_or_mismatched_metadata_result:
    promotion_ok: false
    promoted: false
    verification_decision: NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE
    blocker: archive_metadata_not_verified
  release_claimed_go: false

summary:
  - archive path traversal was already blocked; this gate adds archive provenance/metadata validation
  - GO archives without build_real_adapter_evidence_bundle metadata are rejected before promotion
  - metadata failures now downgrade returned bundle verification to NOT_GO so v0 readiness cannot see a misleading GO bundle artifact
  - focused promotion and closeout tests cover metadata-positive archive closeout and metadata-negative rejection
  - current recertification remains NOT_GO with real_trained_adapter_no_fake_endpoint as the sole v0 blocker
```

```yaml
gate: mib-studio-strict-toolchain-preparer
objective: make strict bootstrap/frontend verification toolchain setup reproducible

files:
  strict_toolchain_preparer: scripts/prepare_strict_toolchain.py
  strict_toolchain_tests: tests/scripts/test_prepare_strict_toolchain.py
  devex_spec: docs/specs/DEV_ENVIRONMENT_SPEC.md
  working_state: docs/WORKING.md

preparer_contract:
  reads_version_sources:
    - .node-version
    - rust-toolchain.toml
    - package.json packageManager
  defaults:
    toolchain_root: /tmp/mib-toolchain
    corepack_home: /tmp/corepack
  verifies_downloads:
    - node upstream SHASUMS256.txt
    - rust upstream .sha256 file
  dry_run_no_network: true
  release_claimed_go: false
  m6_rc_claimed_go: false

summary:
  - strict bootstrap mismatch is now reproducible through scripts/prepare_strict_toolchain.py instead of a manual /tmp setup
  - dry-run and idempotent real runs report READY_STRICT_TOOLCHAIN when Node 20.18.1, Rust 1.83.0, and pnpm 9.15.0 are present
  - focused tests cover version discovery, official archive planning, existing-tool detection, checksum parsing, command failure handling, and archive path traversal rejection
  - strict bootstrap m1-smoke passes after preparing /tmp/mib-toolchain and /tmp/corepack
  - this is DevEx verification support only and does not change product behavior or release readiness
```

```yaml
gate: mib-studio-real-adapter-handoff-local-closeout
objective: make the external CUDA handoff self-contained through local closeout

files:
  pytest_config: pytest.ini
  frontend_scripts: package.json
  handoff_generator: scripts/build_real_adapter_handoff.py
  handoff_tests: tests/scripts/test_build_real_adapter_handoff.py
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
  top_level_summary_fields:
    - blocking_reasons
    - operator_next_actions

summary:
  - recertification output now includes top-level blocking_reasons and operator_next_actions for LLM/operator handoff
  - real adapter CUDA handoff artifacts now include local_closeout_after_bundle_transfer
  - after copying artifacts/review/real_adapter_evidence_bundle.tar.gz back from the CUDA host, run scripts/run_v0_release_closeout_from_bundle.py with expected GO decisions
  - full pytest now collects duplicate-basename tests safely through pytest importlib mode
  - full Python regression passes: 193 passed
  - FE unit, build, M1 e2e, and FE v6 route-contract e2e pass with the strict local Node/pnpm toolchain
  - pnpm run e2e now invokes Node with --experimental-websocket, which is required by the Chrome CDP client
  - host-access recertification refreshes candidate scan, CUDA training preflight, M6 RC preflight, real-adapter bundle verification, v0 readiness, and CUDA handoff artifacts
  - the latest current-state recertification records Docker API permission denial in this execution context
  - docker_daemon_available and docker_image_available are current diagnostic blockers alongside missing CUDA/model/adapter inputs
  - the current local state remains NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
  - FE v6 remains verified through docs/mockup/mib_fe_mockup_v6_routes_contract.html and artifacts/review/fe_v6_evidence.md
  - current scan found 0 candidates and 0 GO candidates; /tmp/mib-real-adapter has generated training config but no adapter directory or manifest
  - historical strict model cache preparation at this gate was NOT_READY_STRICT_MODEL_CACHE because the pinned Phi-3.5 required files were absent under /tmp/mib-strict-model-cache-phi/model_cache
  - historical CUDA training preflight at this gate was NOT_READY_CUDA_LORA_TRAINING with blockers docker_base_image_env_digest, strict_model_cache_files, cuda_visible, docker_daemon_available, and docker_base_image_available
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
  External_CUDA_Operator_Packet_Checkout_Guidance: true
  External_CUDA_Operator_Packet_Primary_Verified_Launcher: true
  External_CUDA_Operator_Packet_Stable_Head_Warning: true
  External_CUDA_Operator_Packet_Verified_Launcher_Required_File: true
  External_CUDA_Operator_Packet_Source_Commit_Guard: true
  Strict_Model_Cache_Preparation_Handoff: true
  V0_Release_Blocker_Recertification_Verified_Launcher_Routing: true
  Verified_External_CUDA_Training_Launcher: true
  External_CUDA_Operator_Packet_Verification: true
  External_CUDA_Operator_Packet: true
  V0_Release_Blocker_Recertification_Training_Handoff_Action: true
  Real_Adapter_CUDA_Training_Handoff_Preflight_Guards: true
  V0_Release_Blocker_Recertification: true
  V0_Release_Blocker_Recertification_Actionable_Blockers: true
  V0_Release_Closeout_From_Bundle: true
  V0_Release_Closeout_Actionable_Blockers: true
  Real_Adapter_Evidence_Bundle_Archive: true
  Real_Adapter_Evidence_Bundle_Promotion: true
  Real_Adapter_Evidence_Bundle_Assembly: true
  Real_Adapter_CUDA_Handoff: true
  Real_Adapter_CUDA_Handoff_Archive_Metadata_Contract: true
  Real_Adapter_Local_Closeout_M6_Doc_Prereq: true
  Real_Adapter_CUDA_Training_Handoff: true
  Real_Adapter_Docker_Image_Handoff: true
  Real_Adapter_RC_Gate_Runner_Tooling: true
  Real_Adapter_Bundle_Archive_Metadata_Guard: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true
```

## 4. Verification State

```yaml
status: v0_external_cuda_packet_checkout_guidance_not_go_release
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/build_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head c38ff33
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - rg -n -- "Keep this packet file from the current checkout|packet.git.head is the required committed file source|verified_external_cuda_training_launcher.sh|real_trained_adapter_no_fake_endpoint" scripts/build_external_cuda_operator_packet.py tests/scripts/test_build_external_cuda_operator_packet.py artifacts/review/external_cuda_operator_packet.json artifacts/review/external_cuda_operator_packet.md artifacts/review/external_cuda_operator_packet_verification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/build_external_cuda_operator_packet.py scripts/verify_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head 10ea0cb
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import json; data=json.load(open('artifacts/review/external_cuda_operator_packet.json', encoding='utf-8')); assert data['primary_external_handoff'] == 'artifacts/review/verified_external_cuda_training_launcher.sh'"
  - rg -n -- "primary_external_handoff.*verified_external_cuda_training_launcher.sh|recertification_primary_external_handoff.*verified_external_cuda_training_launcher.sh|verified launcher as the primary external handoff|real_trained_adapter_no_fake_endpoint" scripts/build_external_cuda_operator_packet.py scripts/verify_external_cuda_operator_packet.py tests/scripts/test_build_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py artifacts/review/external_cuda_operator_packet.json artifacts/review/external_cuda_operator_packet.md artifacts/review/external_cuda_operator_packet_verification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_verify_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/verify_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -c "import json; data=json.load(open('artifacts/review/external_cuda_operator_packet_verification.json', encoding='utf-8')); assert data['warnings'] == []"
  - rg -n -- "packet_handoff_source_commit.*65dfd1a|verified 17 required file blobs at 65dfd1a|test_verifier_does_not_warn_when_current_checkout_is_after_packet_commit|real_trained_adapter_no_fake_endpoint" scripts/verify_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py artifacts/review/external_cuda_operator_packet_verification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - git diff --check
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head 65dfd1a
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/build_external_cuda_operator_packet.py scripts/verify_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head f2227bf
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_verify_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/verify_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head 51b2d97
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_prepare_strict_model_cache.py tests/scripts/test_prepare_cuda_lora_training_run.py tests/scripts/test_build_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py tests/scripts/test_run_v0_release_blocker_recertification.py -q
  - python3 -m py_compile scripts/prepare_strict_model_cache.py scripts/prepare_cuda_lora_training_run.py scripts/build_external_cuda_operator_packet.py scripts/verify_external_cuda_operator_packet.py scripts/run_v0_release_blocker_recertification.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_strict_model_cache.py --base-model microsoft/Phi-3.5-mini-instruct --backend cuda --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --no-download --expected-status NOT_READY_STRICT_MODEL_CACHE --json-output artifacts/review/strict_model_cache_preparation.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_cuda_lora_training_run.py --dataset-jsonl examples/fixtures/router_20.jsonl --dataset-id review_router_20 --base-model microsoft/Phi-3.5-mini-instruct --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --output-root /tmp/mib-real-adapter --training-preset quick
  - bash -n artifacts/review/real_adapter_cuda_training_handoff.sh
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --git-head eff6486
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/strict_model_cache_preparation.json
  - python3 -m json.tool artifacts/review/real_adapter_cuda_training_handoff.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "prepare_strict_model_cache.py|strict_model_cache_preparation|prepare_strict_model_cache|READY_STRICT_MODEL_CACHE|NOT_READY_STRICT_MODEL_CACHE|model_cache_dir_present|strict_model_cache_files|release_claimed_go|real_trained_adapter_no_fake_endpoint" scripts/prepare_strict_model_cache.py tests/scripts/test_prepare_strict_model_cache.py scripts/prepare_cuda_lora_training_run.py tests/scripts/test_prepare_cuda_lora_training_run.py scripts/build_external_cuda_operator_packet.py scripts/verify_external_cuda_operator_packet.py scripts/run_v0_release_blocker_recertification.py tests/scripts/test_run_v0_release_blocker_recertification.py artifacts/review/real_adapter_cuda_training_handoff.json artifacts/review/real_adapter_cuda_training_handoff.md artifacts/review/real_adapter_cuda_training_handoff.sh artifacts/review/external_cuda_operator_packet.json artifacts/review/external_cuda_operator_packet.md artifacts/review/external_cuda_operator_packet_verification.json artifacts/review/v0_release_blocker_recertification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_run_v0_release_blocker_recertification.py -q
  - python3 -m py_compile scripts/run_v0_release_blocker_recertification.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "verified_external_cuda_training_launcher.sh|real_adapter_cuda_training_handoff.sh|primary_external_handoff|operator_next_actions|operator_next_step|real_trained_adapter_no_fake_endpoint|NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION|release_claimed_go" scripts/run_v0_release_blocker_recertification.py tests/scripts/test_run_v0_release_blocker_recertification.py artifacts/review/v0_release_blocker_recertification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_verified_cuda_training_launcher.py -q
  - python3 -m py_compile scripts/build_verified_cuda_training_launcher.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_verified_cuda_training_launcher.py --json-output artifacts/review/verified_external_cuda_training_launcher.json --markdown-output artifacts/review/verified_external_cuda_training_launcher.md --shell-output artifacts/review/verified_external_cuda_training_launcher.sh
  - bash -n artifacts/review/verified_external_cuda_training_launcher.sh
  - python3 -m json.tool artifacts/review/verified_external_cuda_training_launcher.json
  - rg -n -- "verified_external_cuda_training_launcher|verify_external_cuda_operator_packet.py|GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION|real_adapter_cuda_training_handoff.sh|MIB_RUNTIME_ALLOW_FAKE_BACKEND|release_claimed_go|real_trained_adapter_no_fake_endpoint" scripts/build_verified_cuda_training_launcher.py tests/scripts/test_build_verified_cuda_training_launcher.py artifacts/review/verified_external_cuda_training_launcher.json artifacts/review/verified_external_cuda_training_launcher.md artifacts/review/verified_external_cuda_training_launcher.sh docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_verify_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/verify_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --packet-json artifacts/review/external_cuda_operator_packet.json --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet_verification.json
  - rg -n -- "external_cuda_operator_packet_verification|verify_external_cuda_operator_packet|GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION|release_claimed_go|forbidden_tracked_artifacts|real_adapter_cuda_training_handoff.sh|real_trained_adapter_no_fake_endpoint" scripts/verify_external_cuda_operator_packet.py tests/scripts/test_verify_external_cuda_operator_packet.py artifacts/review/external_cuda_operator_packet_verification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_external_cuda_operator_packet.py -q
  - python3 -m py_compile scripts/build_external_cuda_operator_packet.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_external_cuda_operator_packet.py --json-output artifacts/review/external_cuda_operator_packet.json --markdown-output artifacts/review/external_cuda_operator_packet.md
  - python3 -m json.tool artifacts/review/external_cuda_operator_packet.json
  - rg -n -- "external_cuda_operator_packet|primary_external_handoff|real_adapter_cuda_training_handoff.sh|51b2d97|release_claimed_go|forbidden_committed_artifacts" scripts/build_external_cuda_operator_packet.py tests/scripts/test_build_external_cuda_operator_packet.py artifacts/review/external_cuda_operator_packet.json artifacts/review/external_cuda_operator_packet.md docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_run_v0_release_blocker_recertification.py -q
  - python3 -m py_compile scripts/run_v0_release_blocker_recertification.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "real_adapter_cuda_training_handoff.sh|package_readiness_checks|operator_next_actions|no_go_adapter_candidates|real_trained_adapter_no_fake_endpoint|NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION" scripts/run_v0_release_blocker_recertification.py tests/scripts/test_run_v0_release_blocker_recertification.py artifacts/review/v0_release_blocker_recertification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_prepare_cuda_lora_training_run.py -q
  - python3 -m py_compile scripts/prepare_cuda_lora_training_run.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_cuda_lora_training_run.py --dataset-jsonl examples/fixtures/router_20.jsonl --dataset-id review_router_20 --base-model microsoft/Phi-3.5-mini-instruct --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --output-root /tmp/mib-real-adapter --training-preset quick
  - python3 -m json.tool artifacts/review/real_adapter_cuda_training_handoff.json
  - rg -n -- "package_readiness_checks|dataset_jsonl_present|python_executable_present|rc_handoff_shell_present|real_trained_adapter_no_fake_endpoint|PREPARED_NOT_RUN|MIB_RUNTIME_ALLOW_FAKE_BACKEND" scripts/prepare_cuda_lora_training_run.py tests/scripts/test_prepare_cuda_lora_training_run.py artifacts/review/real_adapter_cuda_training_handoff.json artifacts/review/real_adapter_cuda_training_handoff.md artifacts/review/real_adapter_cuda_training_handoff.sh docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_run_v0_release_blocker_recertification.py -q
  - python3 -m py_compile scripts/run_v0_release_blocker_recertification.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "blocking_reasons|operator_next_actions|real_trained_adapter_no_fake_endpoint|adapter_dir_present|docker_base_image_env_digest|NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION" scripts/run_v0_release_blocker_recertification.py tests/scripts/test_run_v0_release_blocker_recertification.py artifacts/review/v0_release_blocker_recertification.json docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_run_v0_release_closeout_from_bundle.py -q
  - python3 -m py_compile scripts/run_v0_release_closeout_from_bundle.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - rg -n -- "blocking_reasons|operator_next_actions|archive_metadata_not_verified|m6_review_docs_not_current|real_trained_adapter_no_fake_endpoint|GO_V0_RELEASE_CLOSEOUT|NOT_GO_V0_READINESS|NOT_GO_BUNDLE_PROMOTION" scripts/run_v0_release_closeout_from_bundle.py tests/scripts/test_run_v0_release_closeout_from_bundle.py docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_real_adapter_handoff.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/real_adapter_cuda_handoff.json
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "local_closeout_requires_m6_review_docs_go|same release workstation checkout|m6_review_docs_not_current|docs/reviews/M6|GO_V0_RELEASE_CLOSEOUT|real_trained_adapter_no_fake_endpoint" scripts/build_real_adapter_handoff.py tests/scripts/test_build_real_adapter_handoff.py artifacts/review/real_adapter_cuda_handoff.json artifacts/review/real_adapter_cuda_handoff.md artifacts/review/real_adapter_cuda_handoff.sh docs/CONTEXT.md docs/WORKING.md .codex/tasks/current.json
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_real_adapter_handoff.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/real_adapter_cuda_handoff.json
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - rg -n -- "bundle_archive_contract|metadata-bearing|real_adapter_evidence_bundle_manifest.json|real_adapter_evidence_bundle_verification.json|archive_metadata_not_verified|GO_V0_RELEASE_CLOSEOUT|real_trained_adapter_no_fake_endpoint" scripts/build_real_adapter_handoff.py tests/scripts/test_build_real_adapter_handoff.py artifacts/review/real_adapter_cuda_handoff.json artifacts/review/real_adapter_cuda_handoff.md artifacts/review/real_adapter_cuda_handoff.sh docs/WORKING.md .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_promote_real_adapter_evidence_bundle.py tests/scripts/test_run_v0_release_closeout_from_bundle.py -q
  - python3 -m py_compile scripts/promote_real_adapter_evidence_bundle.py
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_v0_release_blocker_recertification.py --expected-readiness-decision NOT_GO --expected-bundle-decision NOT_GO --expected-training-status NOT_READY_CUDA_LORA_TRAINING --expected-rc-status NOT_READY_PRECHECK_FAILED
  - python3 -m json.tool artifacts/review/v0_release_blocker_recertification.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_prepare_strict_toolchain.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_strict_toolchain.py --dry-run --json-output /tmp/mib-strict-toolchain-dry-run.json
  - python3 -m json.tool /tmp/mib-strict-toolchain-dry-run.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_strict_toolchain.py --json-output /tmp/mib-strict-toolchain-preparation.json
  - python3 -m json.tool /tmp/mib-strict-toolchain-preparation.json
  - python3 -m py_compile scripts/prepare_strict_toolchain.py
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest tests/scripts/test_build_real_adapter_handoff.py tests/scripts/test_run_v0_release_closeout_from_bundle.py -q
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
  - rg -n -- "local_closeout_after_bundle_transfer|run_v0_release_closeout_from_bundle.py|GO_V0_RELEASE_CLOSEOUT|NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION|real_trained_adapter_no_fake_endpoint" scripts/build_real_adapter_handoff.py tests/scripts/test_build_real_adapter_handoff.py artifacts/review/real_adapter_cuda_handoff.json artifacts/review/real_adapter_cuda_handoff.md artifacts/review/real_adapter_cuda_handoff.sh docs/WORKING.md artifacts/review/v0_release_blocker_recertification.json

fixed_verification_blockers:
  - full_pytest_import_file_mismatch_from_duplicate_test_basenames
  - fe_e2e_missing_node_experimental_websocket_flag
  - handoff_missing_embedded_local_closeout_after_bundle_transfer
  - strict_toolchain_setup_was_manual_and_hook_fragile
  - bundle_archive_promotion_did_not_require_builder_metadata
  - handoff_did_not_explain_metadata_bearing_archive_requirement
  - local_closeout_handoff_did_not_explicitly_require_same_checkout_m6_go_review_docs
  - local_closeout_summary_did_not_emit_actionable_not_go_reasons

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
  - mib-export:test_real_adapter_image

local_ready_inputs:
  - /tmp/mib-real-adapter/adapter directory
  - strict Phi-3.5 files under /tmp/mib-strict-model-cache-phi/model_cache
  - MIB_DOCKER_BASE_IMAGE_WITH_DIGEST from artifacts/review/real_adapter_cuda_base_image.env
  - local digest-pinned CUDA/Python base image:
      ref: pytorch/pytorch@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126
```

## 6. Next Work

```yaml
recertify_current_state:
  env_file: artifacts/review/real_adapter_cuda_base_image.env
  command: >
    MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=pytorch/pytorch@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126
    PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
    scripts/run_v0_release_blocker_recertification.py
    --expected-readiness-decision NOT_GO
    --expected-bundle-decision NOT_GO
    --expected-training-status NOT_READY_CUDA_LORA_TRAINING
    --expected-rc-status NOT_READY_PRECHECK_FAILED

prepare_strict_toolchain_before_strict_checks:
  command: >
    PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
    scripts/prepare_strict_toolchain.py
    --json-output /tmp/mib-strict-toolchain-preparation.json

external_cuda_host_flow:
  - before operator handoff, run scripts/build_external_cuda_operator_transfer_manifest.py and require READY_EXTERNAL_CUDA_OPERATOR_TRANSFER from a full repository checkout
  - run bash artifacts/review/verified_external_cuda_training_launcher.sh on a CUDA host
  - allow the training handoff to run scripts/prepare_strict_model_cache.py with --allow-download before CUDA preflight
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
  requires_metadata_bearing_archive: true
  required_archive_metadata:
    - real_adapter_evidence_bundle_manifest.json
    - real_adapter_evidence_bundle_verification.json
  same_release_workstation_checkout_required: true
  requires_local_m6_review_docs_go:
    - docs/reviews/M6/SIGNOFF_MATRIX.md
    - docs/reviews/M6/CTO_DECISION.md
  missing_local_m6_review_docs_go_status: m6_review_docs_not_current
  missing_or_mismatched_metadata_status: archive_metadata_not_verified
  not_go_summary_fields:
    - blocking_reasons
    - operator_next_actions
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
The preferred external CUDA host entrypoint is
artifacts/review/verified_external_cuda_training_launcher.sh. It refuses
MIB_RUNTIME_ALLOW_FAKE_BACKEND, verifies
artifacts/review/external_cuda_operator_packet.json with
scripts/verify_external_cuda_operator_packet.py and expected decision
GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION, then runs
artifacts/review/real_adapter_cuda_training_handoff.sh only after verification
passes. This launcher is PREPARED_NOT_RUN and does not claim M6-RC or v0 release
GO.
The external CUDA operator packet is
artifacts/review/external_cuda_operator_packet.json and .md. It pins the handoff
source commit to f31050c, records required committed file sha256 values, names
artifacts/review/verified_external_cuda_training_launcher.sh as the primary
external handoff, records artifacts/review/real_adapter_cuda_training_handoff.sh
as the downstream training handoff, and forbids committing model weights, LoRA
adapter files, Docker image layers/archives, raw endpoint transcripts, or copied
external evidence bundles. Keep the packet file from the current checkout;
packet.git.head is the required committed file source commit for verifier blob
checks, not an instruction to checkout an older commit before using the packet.
The packet was regenerated after the current-head recertification commit and
includes scripts/build_external_cuda_operator_transfer_manifest.py in
required_committed_files. No packet refresh is pending after f31050c.
Before running that handoff, use
scripts/build_external_cuda_operator_transfer_manifest.py from a full repository
checkout and require READY_EXTERNAL_CUDA_OPERATOR_TRANSFER. Then run
scripts/verify_external_cuda_operator_packet.py with
artifacts/review/external_cuda_operator_packet.json and require
GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION. The current verification artifact
is artifacts/review/external_cuda_operator_packet_verification.json; it verifies
18 required committed file hashes including artifacts/review/verified_external_cuda_training_launcher.sh, scripts/prepare_strict_model_cache.py, and scripts/build_external_cuda_operator_transfer_manifest.py,
18 required committed file blobs at handoff source commit f31050c,
6 package readiness checks, command order,
forbidden artifact labels, and no forbidden tracked artifacts. The verifier
allows the current checkout to be a later closeout commit than packet.git.head
when packet.git.head resolves and required committed file blobs verify at that
pinned handoff commit. This is packet integrity GO only, not M6-RC or v0 release
GO.
The generated CUDA training handoff runs
scripts/prepare_strict_model_cache.py --allow-download before
preflight_cuda_training. The local strict Phi-3.5 cache has now been prepared
under /tmp/mib-strict-model-cache-phi/model_cache, and the repo-local
no-download verification artifact reports READY_STRICT_MODEL_CACHE with all 5
pinned files present. The handoff still embeds
package_readiness_checks and fails fast if the dataset JSONL, repo Python,
LLaMA-Factory CLI, backend_config.yaml, or downstream RC handoff shell is
missing.
The current recertification summary now sets primary_external_handoff to
artifacts/review/verified_external_cuda_training_launcher.sh and lists that
launcher as the first operator_next_actions item for missing real-adapter/CUDA
setup paths.
The generated CUDA handoff now embeds bundle_archive_contract and
local_closeout_after_bundle_transfer. After copying the metadata-bearing
artifacts/review/real_adapter_evidence_bundle.tar.gz back into this repo, run
scripts/run_v0_release_closeout_from_bundle.py with expected GO bundle/readiness
decisions and require GO_V0_RELEASE_CLOSEOUT. The archive must include
real_adapter_evidence_bundle_manifest.json and
real_adapter_evidence_bundle_verification.json; missing or mismatched metadata
returns archive_metadata_not_verified and prevents promotion. This same release
workstation checkout must also contain accepted GO updates to
docs/reviews/M6/SIGNOFF_MATRIX.md and docs/reviews/M6/CTO_DECISION.md before
local closeout; otherwise v0 readiness returns m6_review_docs_not_current.
NOT_GO closeout summaries include blocking_reasons and operator_next_actions so
the next agent can distinguish archive metadata, source bundle, M6 review-doc,
and real endpoint evidence blockers without weakening release acceptance.
NOT_GO recertification summaries also include blocking_reasons and
operator_next_actions so the next agent can distinguish missing adapter files,
CUDA visibility, Docker export image, bundle, endpoint, and handoff
blockers without weakening release acceptance.
The current local strict model cache blocker is cleared: the CUDA training
preflight check for strict_model_cache_files is ok and no longer appears in the
top-level blocker list.
The latest current-state recertification ran with host Docker access:
docker_daemon_available is ok and no longer appears in the top-level blocker
list. The digest-pinned CUDA/Python base image is now resolved as
pytorch/pytorch@sha256:ac7c098a81512e719afa5d2d497f812d7db3498f340a4b819c69cb7b3b257126,
and docker_base_image_env_digest/docker_base_image_available are no longer
top-level blockers. The Docker export image mib-export:test is still missing,
CUDA is still not visible through nvidia-smi, adapter files are still absent,
and the release blocker is still the missing real trained adapter no-fake
endpoint evidence.

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
