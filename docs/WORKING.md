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
phase_id: REAL_ADAPTER_EVIDENCE_BUNDLE_ARCHIVE
milestone: M6_RC_Blocker_Remediation
phase_status: real_adapter_evidence_bundle_archive_verified_not_go
active_slice: none
gate_id: mib-studio-real-adapter-evidence-bundle-archive
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
  gate: mib-studio-real-adapter-evidence-bundle-archive
  implementation_commit: this_commit
  closeout_commit: this_commit
  pushed_to_origin_main: true
  objective: add portable archive support for external CUDA real-adapter evidence bundle transfer and promotion
  evidence:
    real_adapter_cuda_base_image_resolution: artifacts/review/real_adapter_cuda_base_image_resolution.json
    real_adapter_cuda_training_prereq_preflight: artifacts/review/real_adapter_cuda_training_prereq_preflight.json
    real_adapter_docker_image_handoff: artifacts/review/real_adapter_docker_image_handoff.md
    real_adapter_docker_image_handoff_json: artifacts/review/real_adapter_docker_image_handoff.json
    real_adapter_docker_image_handoff_shell: artifacts/review/real_adapter_docker_image_handoff.sh
    real_adapter_cuda_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.md
    real_adapter_cuda_training_handoff_json: artifacts/review/real_adapter_cuda_training_handoff.json
    real_adapter_cuda_training_handoff_shell: artifacts/review/real_adapter_cuda_training_handoff.sh
    real_adapter_evidence_bundle_verification: artifacts/review/real_adapter_evidence_bundle_verification.json
    real_adapter_cuda_handoff: artifacts/review/real_adapter_cuda_handoff.md
    real_adapter_cuda_handoff_json: artifacts/review/real_adapter_cuda_handoff.json
    real_adapter_cuda_handoff_shell: artifacts/review/real_adapter_cuda_handoff.sh
    real_adapter_candidate_locator: artifacts/review/real_adapter_candidate_locator_evidence.md
    real_adapter_candidate_scan_json: artifacts/review/real_adapter_candidate_scan.json
    real_adapter_image_lineage_preflight: artifacts/review/real_adapter_image_lineage_preflight_evidence.md
    v0_release_readiness_audit: artifacts/review/v0_release_readiness_audit_evidence.md
    v0_release_readiness_audit_json: artifacts/review/v0_release_readiness_audit.json
    desktop_e2e_route_repair: artifacts/review/desktop_e2e_route_repair_evidence.md
    fe_v6_evidence: artifacts/review/fe_v6_evidence.md
    m6_rc_evidence_verification: artifacts/review/m6_rc_evidence_verification.json
    real_adapter_prereq_audit: artifacts/review/real_adapter_prereq_audit_evidence.md
    real_adapter_prereq_audit_json: artifacts/review/m6_real_adapter_prereq_audit.json
  summary:
    - scripts/build_real_adapter_evidence_bundle.py now supports --archive-output to emit a portable tar.gz containing only fixed verifier-required evidence files plus bundle manifest/verification metadata
    - scripts/promote_real_adapter_evidence_bundle.py now accepts either --bundle-dir or --bundle-archive; archive promotion safely extracts to a temp directory, rejects unsafe archive member paths/types, verifies with the existing strict bundle verifier, and only copies fixed required evidence files
    - artifacts/review/real_adapter_cuda_handoff.* now pass --archive-output artifacts/review/real_adapter_evidence_bundle.tar.gz during evidence_bundle_assembly for external CUDA host transfer
    - archive support does not change GO policy; v0 still requires GO_REAL_ADAPTER_EVIDENCE_BUNDLE and the current local state remains NOT_GO
    - release_blocker_recertification refreshed artifacts/review/real_adapter_candidate_scan.json and artifacts/review/real_adapter_cuda_training_prereq_preflight.json against the current local state
    - candidate scan remains NO_GO_CANDIDATES_FOUND with go_candidate_count 0 and fixture_like_candidate_count 2
    - recertified_release_values: go_candidate_count: 0; release_ready: false; unexpected_blockers: []
    - CUDA training preflight remains NOT_READY_CUDA_LORA_TRAINING; Docker daemon is available outside the sandbox, while docker_base_image_env_digest, cuda_visible, and docker_base_image_available remain blockers
    - /tmp/mib-real-adapter currently contains backend_config.yaml and train_config.json only; /tmp/mib-real-adapter/adapter and /tmp/mib-real-adapter/manifest.json are still missing
    - v0 release readiness remains NOT_GO with release_ready false, verification_ok true, unexpected_blockers empty, and real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/run_m6_real_adapter_rc_gate.py now supports --m6-verification-only, which requires a prior endpoint-only gate summary plus existing live endpoint/intake evidence before running M6 GO verification
    - m6-verification-only mode refuses with NOT_GO_EXISTING_ENDPOINT_EVIDENCE when the prior endpoint-only summary, matching inputs, adapter intake, or live endpoint JSON is missing or stale
    - m6-verification-only mode preserves prior adapter_intake and endpoint_capture step evidence and appends only m6_go_verification before claiming GO_M6_REAL_ADAPTER_RC_GATE
    - artifacts/review/real_adapter_cuda_handoff.* now run rc_gate_m6_go with --m6-verification-only after the M6 review-doc GO marker check, avoiding a second endpoint capture during closeout
    - current M6 and v0 release readiness remain NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/run_m6_real_adapter_rc_gate.py now supports --endpoint-evidence-only, which runs adapter intake and live no-fake endpoint capture without running M6 GO verification or claiming M6-RC GO
    - endpoint-only mode returns GO_REAL_ADAPTER_ENDPOINT_EVIDENCE_READY_M6_NOT_CLAIMED with m6_rc_claimed_go false and next_required_action pointing to M6 review-doc GO update
    - artifacts/review/real_adapter_cuda_handoff.* now sequence rc_gate_endpoint_evidence before m6_review_docs_go_update_required, then rc_gate_m6_go, evidence_bundle_assembly, and v0_readiness_recheck
    - the generated shell checks docs/reviews/M6/SIGNOFF_MATRIX.md and docs/reviews/M6/CTO_DECISION.md for final GO markers and stops before M6 GO verification while those docs remain NOT_GO
    - current M6 and v0 release readiness remain NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/verify_m6_rc_evidence.py now evaluates M6 review docs against the requested expected decision
    - --expected-decision NOT_GO still accepts the current blocker docs when real_trained_adapter_no_fake_endpoint is the only blocker
    - --expected-decision GO now requires final M6 signoff GO and CTO Decision: GO markers before the verifier can return GO
    - focused tests cover current NOT_GO docs, complete endpoint evidence rejected while docs remain NOT_GO, and complete endpoint plus GO docs accepted
    - current M6 and v0 release readiness remain NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/promote_real_adapter_evidence_bundle.py now verifies an externally produced real-adapter evidence bundle with the existing strict verifier before promotion
    - promotion copies only the fixed files required by scripts/verify_real_adapter_evidence_bundle.py into the target review artifact directory, and only when GO_REAL_ADAPTER_EVIDENCE_BUNDLE is proven
    - NOT_GO dry-run promotion against current artifacts/review writes verification and promotion manifest under /tmp without mutating the target directory
    - focused tests cover GO promotion, NOT_GO dry-run no-copy behavior, expected-GO rejection of a NOT_GO bundle, and source/target safety
    - scripts/build_real_adapter_evidence_bundle.py now copies the fixed evidence files required by scripts/verify_real_adapter_evidence_bundle.py into a caller-selected bundle directory, runs the existing verifier, and writes manifest plus verification JSON
    - the bundle assembler removes stale fixed evidence files from the target bundle before copying current source files, preventing old GO-looking files from satisfying a new incomplete bundle
    - artifacts/review/real_adapter_cuda_handoff.* now run evidence_bundle_assembly after rc_gate_live and before v0_readiness_recheck
    - local bundle assembly smoke against artifacts/review into /tmp/mib-real-adapter-evidence-bundle remains NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE because live endpoint, adapter intake, and RC gate artifacts are missing
    - current v0 release readiness remains NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/prepare_cuda_lora_training_run.py now passes --cuda-base-image-json-output, --cuda-base-image-env-output, and every --cuda-base-image-candidate into the generated prepare_docker_image command
    - artifacts/review/real_adapter_cuda_training_handoff.* now record prepare_docker_image with the same CUDA base image resolver output paths and default pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime candidate used earlier in the training handoff
    - focused tests assert the generated operator shell preserves the downstream resolver output flags and CUDA base image candidate
    - current v0 release readiness remains NOT_GO with real_trained_adapter_no_fake_endpoint as the only release blocker
    - scripts/resolve_cuda_base_image.py now emits MIB_DOCKER_BASE_IMAGE_WITH_DIGEST only when a local candidate has a sha256 RepoDigest plus CUDA markers plus Python runtime markers
    - scripts/resolve_cuda_base_image.py now rejects digest-pinned CUDA-only images with python_runtime_markers_missing instead of emitting an env var that the next preflight would reject
    - focused resolver tests prove CUDA+Python success, non-CUDA rejection, CUDA-only rejection, missing RepoDigest rejection, and default candidate behavior
    - current artifacts/review/real_adapter_cuda_base_image_resolution.json remains NOT_READY_CUDA_BASE_IMAGE because pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime is not present in the current Docker daemon
    - scripts/check_cuda_lora_training_prereqs.py now validates MIB_DOCKER_BASE_IMAGE_WITH_DIGEST with docker_base_image_cuda_python_runtime when the image is inspectable
    - docker_base_image_cuda_python_runtime requires CUDA markers and Python runtime markers from docker image inspect output, preventing ordinary application images from satisfying the base-image prerequisite
    - focused tests prove inspectable non-CUDA digest images are rejected and CUDA+Python runtime marker images remain READY in the simulated all-prereqs path
    - current artifacts/review/real_adapter_cuda_training_prereq_preflight.json remains NOT_READY_CUDA_LORA_TRAINING because MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is unset and host CUDA is unavailable
    - scripts/resolve_cuda_base_image.py rejects non-CUDA images, CUDA-only images without Python runtime markers, and locally built/tagged images that lack a usable RepoDigest
    - artifacts/review/real_adapter_cuda_training_handoff.* now include resolve_cuda_base_image before preflight; the generated shell runs it only when MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is unset and then sources artifacts/review/real_adapter_cuda_base_image.env
    - artifacts/review/real_adapter_docker_image_handoff.* now include the same resolver guard before materialize_context and docker build
    - scripts/check_cuda_lora_training_prereqs.py now checks the configured LLaMA-Factory CLI path with the valid version subcommand
    - scripts/prepare_cuda_lora_training_run.py now emits the same ./.venv/bin/llamafactory-cli path for preflight and llamafactory train
    - artifacts/review/real_adapter_cuda_training_handoff.* now use ./.venv/bin/llamafactory-cli instead of relying on PATH
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json now reports llamafactory_cli_available ok
    - current CUDA training preflight blockers are reduced to docker_base_image_env_digest, cuda_visible, and docker_base_image_available
    - artifacts/review/real_adapter_cuda_training_handoff.* now use /tmp/mib-strict-model-cache-phi/model_cache for microsoft/Phi-3.5-mini-instruct
    - /tmp/mib-real-adapter/backend_config.yaml now uses the same strict Phi cache path as the generated training handoff and preflight
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json now reports backend_config_ready ok and strict_model_cache_files ok with verify_hashes true
    - current CUDA training preflight no longer depends on a globally installed llamafactory-cli
    - scripts/check_cuda_lora_training_prereqs.py now produces a structured CUDA training host preflight report before real adapter training
    - the preflight checks MIB_RUNTIME_ALLOW_FAKE_BACKEND absence, MIB_DOCKER_BASE_IMAGE_WITH_DIGEST digest format, dataset JSONL readiness, backend_config.yaml consistency, strict model cache required files with hash verification enabled in the handoff, nvidia-smi, llamafactory-cli, Docker daemon access, Docker base image availability, and CUDA/Python base image runtime markers when the base image is set
    - artifacts/review/real_adapter_cuda_training_prereq_preflight.json is NOT_READY_CUDA_LORA_TRAINING and does not claim M6-RC or release GO
    - scripts/prepare_cuda_lora_training_run.py now inserts preflight_cuda_training before llamafactory-cli train
    - scripts/prepare_real_adapter_docker_image.py now prepares a guarded Docker image handoff for a real adapter root without committing adapter artifacts or building an image on the current host
    - artifacts/review/real_adapter_docker_image_handoff.sh refuses fake backend mode, resolves MIB_DOCKER_BASE_IMAGE_WITH_DIGEST when unset, requires @sha256, materializes a Docker context, builds mib-export:test, then runs docker image inspect
    - Docker context materialization reuses packages/agent-runtime Dockerfile, zip runtime agents, runtime loaders, schemas, strict base-model catalog metadata, and the operator-provided real adapter directory
    - focused tests validate the handoff shell guards and a materialized export manifest/context using an in-test self-test adapter only
    - scripts/prepare_cuda_lora_training_run.py now inserts prepare_docker_image after verify_adapter_intake and before artifacts/review/real_adapter_cuda_handoff.sh
    - current Docker image handoff artifact is PLAN_PREPARED_NOT_RUN and does not claim M6-RC or release GO
    - services/worker/runtime/llamafactory.py now writes explicit lora_rank and lora_alpha into CUDA LLaMA-Factory backend_config.yaml
    - examples/fixtures/llamafactory_config.golden.yaml now locks quick preset lora_rank 4 and lora_alpha 8 in the generated config contract
    - scripts/prepare_cuda_lora_training_run.py prepares the canonical LLaMA-Factory dataset conversion and backend_config.yaml for an external CUDA training run
    - artifacts/review/real_adapter_cuda_training_handoff.sh refuses fake backend mode, requires nvidia-smi and llamafactory-cli, runs the CUDA training preflight, runs actual training, finalizes manifest, verifies adapter intake, prepares the Docker image handoff, then invokes artifacts/review/real_adapter_cuda_handoff.sh
    - artifacts/review/real_adapter_cuda_training_handoff.json is PREPARED_NOT_RUN and does not claim M6-RC or release GO
    - scripts/build_real_adapter_handoff.py now emits artifacts/review/real_adapter_cuda_handoff.sh in addition to JSON/Markdown
    - the generated shell artifact refuses to run when MIB_RUNTIME_ALLOW_FAKE_BACKEND is set
    - the generated shell artifact requires a real MIB_RUNTIME_BEARER_TOKEN of at least 32 characters
    - the generated shell artifact preserves the safe sequence candidate_scan, adapter_intake, rc_gate_preflight, rc_gate_live, evidence_bundle_assembly, v0_readiness_recheck
    - artifacts/review/real_adapter_cuda_handoff.json records executable_artifact: artifacts/review/real_adapter_cuda_handoff.sh
    - scripts/build_real_adapter_handoff.py now composes candidate scan, adapter intake, RC preflight, live no-fake RC gate, real-adapter evidence bundle assembly, and v0 readiness recheck
    - the handoff command sequence runs scripts/build_real_adapter_evidence_bundle.py --expected-decision GO after rc_gate_live and before v0_readiness_recheck
    - artifacts/review/real_adapter_cuda_handoff.md now lists the evidence_bundle_assembly command and the GO_REAL_ADAPTER_EVIDENCE_BUNDLE release precondition
    - current handoff state exposes real_adapter_evidence_bundle_decision NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE and real_adapter_evidence_bundle_ready false
    - scripts/verify_real_adapter_evidence_bundle.py now validates endpoint/intake/RC-gate/M6 evidence only, avoiding a circular dependency on v0 readiness
    - scripts/verify_v0_release_readiness.py now requires GO_REAL_ADAPTER_EVIDENCE_BUNDLE for release GO
    - bundle verification requires live no-fake endpoint JSON, endpoint markdown markers, GO adapter intake, matching adapter hashes, GO RC gate runner output, and GO M6 verification
    - focused tests prove complete live bundle acceptance, self-test/hash-mismatch/missing bundle rejection, v0 GO requiring bundle GO, and missing bundle report as an unexpected release blocker
    - current artifacts/review bundle verification is NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE because live endpoint, adapter intake, RC gate GO, and M6 GO artifacts are absent
    - current handoff decision is WAITING_FOR_REAL_ADAPTER_INPUTS and does not claim M6-RC or v0 GO
    - scripts/find_real_adapter_candidates.py scans explicit roots for adapter.safetensors plus adapter_config.json directories
    - candidate validation reuses scripts/verify_real_adapter_artifact.py real adapter intake rules
    - GO candidates emit runnable scripts/run_m6_real_adapter_rc_gate.py commands
    - current scan across repo, /tmp/mib-real-adapter, and /tmp/mib-phi-docker-export-_vgqfd4g found 2 fixture-like candidates and 0 GO candidates
    - apps/desktop/src/main.mjs breadcrumb text includes the Route contract sentinel required by M1 smoke bootstrap
    - hook-required bootstrap_dev.sh --phase m1-smoke --skip-install now passes in .venv
    - current v0 release readiness decision remains NOT_GO, release_ready false, verification_ok true, unexpected_blockers empty
    - the only current release blocker is real_trained_adapter_no_fake_endpoint
    - current missing prereqs are adapter_dir_present, adapter_safetensors_present, adapter_config_present, adapter_manifest_present, docker_image_available, and host_cuda_visible
    - no backend, schema, training, export, runtime behavior, or M6 evidence policy files changed

important_previous_commits:
  real_adapter_evidence_bundle_promotion: this_commit
  real_adapter_evidence_bundle_assembly: f240bf1
  cuda_base_image_candidate_propagation: 9dea880
  cuda_base_image_resolver_runtime_alignment: b0f83e5
  cuda_base_image_runtime_preflight: bb296b4
  cuda_base_image_resolver_handoff: fa17a6b
  venv_llamafactory_cli_handoff_alignment: 52b0187
  phi_strict_cache_handoff_alignment: this_commit
  cuda_training_host_preflight: this_commit
  real_adapter_docker_image_handoff: this_commit
  real_adapter_cuda_training_handoff: this_commit
  real_adapter_cuda_handoff_executable_artifact: this_commit
  real_adapter_cuda_handoff_bundle_step: this_commit
  real_adapter_evidence_bundle_verifier: 755b1a5
  real_adapter_cuda_handoff: 77855d3
  real_adapter_candidate_locator: 80ac19a
  real_adapter_image_lineage_preflight: ff38eeb
  v0_milestone_evidence_matrix_audit: f9f2499
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
status: real_adapter_evidence_bundle_archive_verified_not_go
passed:
  - python3 -m json.tool .codex/tasks/current.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/build_real_adapter_evidence_bundle.py scripts/promote_real_adapter_evidence_bundle.py scripts/build_real_adapter_handoff.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_build_real_adapter_evidence_bundle.py tests/scripts/test_promote_real_adapter_evidence_bundle.py tests/scripts/test_build_real_adapter_handoff.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_real_adapter_handoff.py --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --json-output artifacts/review/real_adapter_cuda_handoff.json --markdown-output artifacts/review/real_adapter_cuda_handoff.md --shell-output artifacts/review/real_adapter_cuda_handoff.sh
  - python3 -m json.tool artifacts/review/real_adapter_cuda_handoff.json
  - rg -n -- "archive-output|bundle-archive|real_adapter_evidence_bundle.tar.gz|archive_sha256|unsafe archive" scripts/build_real_adapter_evidence_bundle.py scripts/promote_real_adapter_evidence_bundle.py scripts/build_real_adapter_handoff.py tests/scripts/test_build_real_adapter_evidence_bundle.py tests/scripts/test_promote_real_adapter_evidence_bundle.py tests/scripts/test_build_real_adapter_handoff.py artifacts/review/real_adapter_cuda_handoff.md artifacts/review/real_adapter_cuda_handoff.sh docs/WORKING.md
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/find_real_adapter_candidates.py --root /home/firewine/MIB-studio --root /tmp/mib-real-adapter --root /tmp/mib-phi-docker-export-_vgqfd4g --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --json-output artifacts/review/real_adapter_candidate_scan.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/check_cuda_lora_training_prereqs.py --dataset-jsonl examples/fixtures/router_20.jsonl --base-model microsoft/Phi-3.5-mini-instruct --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --output-root /tmp/mib-real-adapter --backend-config /tmp/mib-real-adapter/backend_config.yaml --llamafactory-cli ./.venv/bin/llamafactory-cli --verify-model-cache-hashes --json-output artifacts/review/real_adapter_cuda_training_prereq_preflight.json --expected-status NOT_READY_CUDA_LORA_TRAINING
  - python3 -m json.tool artifacts/review/real_adapter_candidate_scan.json
  - python3 -m json.tool artifacts/review/real_adapter_cuda_training_prereq_preflight.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - rg -n -- "release_blocker_recertification|docker_base_image_env_digest|cuda_visible|docker_base_image_available|go_candidate_count: 0|release_ready: false" docs/WORKING.md
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/run_m6_real_adapter_rc_gate.py scripts/build_real_adapter_handoff.py
  - PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_run_m6_real_adapter_rc_gate.py tests/scripts/test_build_real_adapter_handoff.py -q
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/build_real_adapter_handoff.py --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --json-output artifacts/review/real_adapter_cuda_handoff.json --markdown-output artifacts/review/real_adapter_cuda_handoff.md --shell-output artifacts/review/real_adapter_cuda_handoff.sh
  - python3 -m json.tool artifacts/review/real_adapter_cuda_handoff.json
  - rg -n -- "m6-verification-only|m6_verification_only|NOT_GO_EXISTING_ENDPOINT_EVIDENCE|rc_gate_m6_go" scripts/run_m6_real_adapter_rc_gate.py scripts/build_real_adapter_handoff.py tests/scripts/test_run_m6_real_adapter_rc_gate.py tests/scripts/test_build_real_adapter_handoff.py artifacts/review/real_adapter_cuda_handoff.md artifacts/review/real_adapter_cuda_handoff.sh docs/WORKING.md
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json
  - python3 -m json.tool artifacts/review/m6_rc_evidence_verification.json
  - PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
  - python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
  - COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
  - git diff --check
  - git diff --cached --check
warnings:
  - M6-RC decision remains NOT_GO
  - evidence bundle archive support does not claim M6-RC or v0 GO and does not relax strict bundle verification
  - release_blocker_recertification does not claim M6-RC or v0 GO
  - m6-verification-only mode requires existing endpoint-only evidence and does not bypass endpoint, M6, bundle, or v0 acceptance checks
  - endpoint-evidence-only mode does not claim M6-RC GO; it exists to capture live endpoint evidence before the review-doc GO update
  - M6-RC --expected-decision GO now also requires final M6 signoff and CTO GO docs
  - no real trained CUDA lora_adapter artifact was found in the repo or current /tmp artifacts
  - current host has no visible CUDA device; nvidia-smi is unavailable and torch.cuda.is_available() is false
  - current CUDA training preflight is NOT_READY_CUDA_LORA_TRAINING
  - current preflight lacks MIB_DOCKER_BASE_IMAGE_WITH_DIGEST, nvidia-smi, and Docker base image availability; Docker daemon is available when the preflight is run outside the sandbox
  - current CUDA base image resolver is NOT_READY_CUDA_BASE_IMAGE because the default PyTorch CUDA runtime image is not present locally
  - bootstrap_dev.sh --phase m1-smoke --skip-install passes in .venv; pip-audit remains skipped by script policy in skip-install environments when isolated pip upgrade cannot complete
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
  V0_Milestone_Evidence_Matrix_Audit: true
  Real_Adapter_Image_Lineage_Preflight: true
  Real_Adapter_Candidate_Locator: true
  Real_Adapter_CUDA_Handoff: true
  Real_Adapter_Evidence_Bundle_Verifier: true
  V0_Bundle_Gate_Integration: true
  Real_Adapter_CUDA_Handoff_Bundle_Step: true
  Real_Adapter_CUDA_Handoff_Executable_Artifact: true
  Real_Adapter_CUDA_Training_Handoff: true
  Real_Adapter_Docker_Image_Handoff: true
  CUDA_Training_Host_Preflight: true
  Phi_Strict_Cache_Handoff_Alignment: true
  Venv_LLaMAFactory_CLI_Handoff_Alignment: true
  CUDA_Base_Image_Resolver_Handoff: true
  CUDA_Base_Image_Runtime_Preflight: true
  CUDA_Base_Image_Resolver_Runtime_Alignment: true
  CUDA_Base_Image_Candidate_Propagation: true
  Real_Adapter_Evidence_Bundle_Assembly: true
  Real_Adapter_Evidence_Bundle_Promotion: true
  M6_RC_Review_Doc_Decision_Gate: true
  Real_Adapter_Endpoint_First_Closeout: true
  Real_Adapter_M6_Verification_Resume: true
  Release_Blocker_Recertification: true
  Real_Adapter_Evidence_Bundle_Archive: true

recorded_not_go:
  M6_RC_Signoff: true
  Docker_Runtime_Real_Trained_Adapter_Inference: true
  Real_Trained_Adapter_Artifact_Available: true

last_completed_gate:
  id: mib-studio-real-adapter-evidence-bundle-archive
  review_bundle: scripts/build_real_adapter_evidence_bundle.py
  decision: real_adapter_evidence_bundle_archive_verified_not_go

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
  - /tmp/mib-real-adapter/adapter and /tmp/mib-real-adapter/manifest.json are missing
  - MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is unset and the digest-pinned CUDA/Python runtime base image is not locally inspectable
  - current host has no nvidia-smi/CUDA visibility
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
  - provide or pull a local pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime image on the CUDA host, then run artifacts/review/real_adapter_cuda_training_handoff.sh; the generated prepare_docker_image step now receives the same CUDA base image candidate and resolver output paths
  - rerun scripts/check_cuda_lora_training_prereqs.py and require docker_base_image_cuda_python_runtime ok once MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is set
  - confirm nvidia-smi succeeds on the CUDA host
  - provide or train a real CUDA lora_adapter with adapter.safetensors, adapter_config.json, and manifest.json
  - run artifacts/review/real_adapter_docker_image_handoff.sh with MIB_DOCKER_BASE_IMAGE_WITH_DIGEST set to a digest-pinned CUDA runtime base image
  - export or tag the matching mib-export:test Docker image and run on a host where nvidia-smi is available
  - rerun scripts/run_m6_real_adapter_rc_gate.py --preflight-only with the real paths until status is READY_TO_RUN
  - run scripts/run_m6_real_adapter_rc_gate.py --endpoint-evidence-only against the real adapter, exported Docker image, and model cache to capture live endpoint evidence without claiming M6-RC GO
  - review artifacts/review/real_trained_adapter_endpoint_evidence.md and .json; update docs/reviews/M6/SIGNOFF_MATRIX.md and docs/reviews/M6/CTO_DECISION.md to final GO only if that evidence is accepted
  - run scripts/run_m6_real_adapter_rc_gate.py --m6-verification-only after M6 review docs contain final GO markers; it reuses the endpoint-only evidence and runs only M6 GO verification
  - run scripts/build_real_adapter_evidence_bundle.py after live RC gate success to assemble artifacts/review/real_adapter_evidence_bundle and require GO_REAL_ADAPTER_EVIDENCE_BUNDLE
  - if the GO bundle is produced on another CUDA host, transfer artifacts/review/real_adapter_evidence_bundle.tar.gz locally and run scripts/promote_real_adapter_evidence_bundle.py --bundle-archive <copied_tar_gz> --target-dir artifacts/review --expected-decision GO before v0 readiness recheck; --bundle-dir remains supported for copied directories
  - rerun M6-RC sign-off only after that decision/evidence is complete
```

## 7. Resume Prompt For Next LLM

```text
Read docs/CONTEXT.md and docs/WORKING.md before edits. Use .venv for Python and
COREPACK_HOME=/tmp/corepack for frontend commands. The latest completed gate is
mib-studio-real-adapter-evidence-bundle-archive. scripts/build_real_adapter_evidence_bundle.py
supports --archive-output and scripts/promote_real_adapter_evidence_bundle.py
supports --bundle-archive for the portable tar.gz produced on an external CUDA
host. The promoter safely extracts archives, rejects unsafe archive member paths
or types, verifies with the existing strict real-adapter bundle verifier, and
copies only fixed required evidence files into artifacts/review. The current
recertified local state is:
candidate scan NO_GO_CANDIDATES_FOUND with go_candidate_count 0; CUDA training
preflight NOT_READY_CUDA_LORA_TRAINING with blockers docker_base_image_env_digest,
cuda_visible, and docker_base_image_available; v0 readiness NOT_GO with
release_ready false and real_trained_adapter_no_fake_endpoint as the only release
blocker. Docker daemon access is available outside the sandbox, but the current
host has no nvidia-smi and no digest-pinned CUDA/Python base image env. The prior
implementation gate was mib-studio-real-adapter-m6-verification-resume.
scripts/run_m6_real_adapter_rc_gate.py
now supports both --endpoint-evidence-only and --m6-verification-only.
--endpoint-evidence-only runs adapter intake and live no-fake Docker endpoint
capture, writes endpoint evidence, returns
GO_REAL_ADAPTER_ENDPOINT_EVIDENCE_READY_M6_NOT_CLAIMED, and keeps
m6_rc_claimed_go false. Use it before updating M6 review docs to GO.
--m6-verification-only is the next step after those docs are GO; it requires the
prior endpoint-only gate summary, matching inputs, GO adapter intake, and live
endpoint JSON, then runs only verify_m6_rc_evidence.py and appends
m6_go_verification. scripts/verify_m6_rc_evidence.py checks M6 review docs
according to --expected-decision: NOT_GO accepts the current blocker docs, while
GO requires final M6 signoff GO and CTO Decision: GO. Do not edit
docs/reviews/M6 to GO until real no-fake endpoint evidence exists and has been
reviewed. After m6-verification-only returns GO_M6_REAL_ADAPTER_RC_GATE,
assemble the real-adapter evidence bundle and run v0 readiness. Before accepting
any external CUDA evidence bundle, run scripts/promote_real_adapter_evidence_bundle.py
against the copied bundle with --expected-decision GO. It first uses the
existing strict bundle verifier and promotes only the fixed verifier-required
files into artifacts/review when GO_REAL_ADAPTER_EVIDENCE_BUNDLE is proven. v0
readiness now also requires that bundle decision for release GO. The current
local artifacts/review bundle is NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE. Start with
artifacts/review/real_adapter_cuda_training_handoff.sh on the CUDA host to
produce the real trained adapter. That script refuses MIB_RUNTIME_ALLOW_FAKE_BACKEND,
requires nvidia-smi and ./.venv/bin/llamafactory-cli, resolves
MIB_DOCKER_BASE_IMAGE_WITH_DIGEST with scripts/resolve_cuda_base_image.py when
unset, first runs scripts/check_cuda_lora_training_prereqs.py, then runs
llamafactory-cli train, finalizes manifest.json, verifies real adapter intake, runs
scripts/prepare_real_adapter_docker_image.py to emit
artifacts/review/real_adapter_docker_image_handoff.sh, then invokes
artifacts/review/real_adapter_cuda_handoff.sh. The Docker image handoff shell
also resolves MIB_DOCKER_BASE_IMAGE_WITH_DIGEST when unset, requires @sha256,
refuses fake backend mode, materializes /tmp/mib-real-adapter/docker_context,
builds mib-export:test, and runs docker image inspect before RC endpoint capture.
The downstream RC handoff script requires a real MIB_RUNTIME_BEARER_TOKEN, then
runs candidate scan, adapter intake, RC preflight, endpoint-evidence-only live
capture, a M6 review-doc GO marker check, m6-verification-only, evidence bundle
assembly, and v0 readiness recheck. The evidence bundle assembly
step runs scripts/build_real_adapter_evidence_bundle.py, copies the fixed
required files into artifacts/review/real_adapter_evidence_bundle, removes stale
fixed evidence files before copying, writes
artifacts/review/real_adapter_evidence_bundle_manifest.json, writes
artifacts/review/real_adapter_evidence_bundle_verification.json, writes
artifacts/review/real_adapter_evidence_bundle.tar.gz via --archive-output, and
requires GO_REAL_ADAPTER_EVIDENCE_BUNDLE before v0 readiness can pass. Use
scripts/promote_real_adapter_evidence_bundle.py with --bundle-archive for a
copied tar.gz or --bundle-dir for a copied directory when that GO bundle must be
promoted from an external location into canonical artifacts/review. It supports
--dry-run for NOT_GO checks and refuses to copy NOT_GO bundles when GO is
expected.
Then use
scripts/find_real_adapter_candidates.py to scan explicit roots for real adapter
candidates; GO candidates emit scripts/run_m6_real_adapter_rc_gate.py commands.
The current training preflight report is
artifacts/review/real_adapter_cuda_training_prereq_preflight.json with status
NOT_READY_CUDA_LORA_TRAINING. Current preflight blockers are
docker_base_image_env_digest, cuda_visible, and docker_base_image_available.
When MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is set and inspectable, the preflight now
also requires docker_base_image_cuda_python_runtime ok, with CUDA markers and
Python runtime markers from docker image inspect output.
The generated training handoff now also propagates --cuda-base-image-json-output,
--cuda-base-image-env-output, and --cuda-base-image-candidate into the downstream
prepare_docker_image command, so operator-supplied CUDA base image choices do not
drop between training and Docker export.
The strict Phi model cache now passes via
/tmp/mib-strict-model-cache-phi/model_cache, and /tmp/mib-real-adapter/backend_config.yaml
uses that same path. LLaMA-Factory now passes via ./.venv/bin/llamafactory-cli.
The current base image resolver report is
artifacts/review/real_adapter_cuda_base_image_resolution.json with status
NOT_READY_CUDA_BASE_IMAGE because pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
is not present in the current Docker daemon. The resolver now emits
MIB_DOCKER_BASE_IMAGE_WITH_DIGEST only when a candidate has a sha256 RepoDigest,
CUDA markers, and Python runtime markers; CUDA-only images fail with
python_runtime_markers_missing.
The current scan found 2 fixture-like candidates and 0 GO candidates.
apps/desktop/src/main.mjs contains the Route contract sentinel required by
COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1
PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke
--skip-install. Use
scripts/verify_v0_release_readiness.py --expected-decision NOT_GO to audit the
current final-program completion state. The current JSON report is
artifacts/review/v0_release_readiness_audit.json: M0 signoff, M1 smoke
recertification, M2-M5 recorded milestone state, FE v6 evidence, desktop route
repair evidence, M6 review docs, and M6-RC evidence verification are present.
release_ready is false, unexpected_blockers is empty, and the only release
blocker is real_trained_adapter_no_fake_endpoint.

Do not claim M6-RC GO. M6-RC remains NOT_GO until real trained CUDA
lora_adapter no-fake Docker endpoint evidence exists or release policy
explicitly accepts fixture-adapter endpoint evidence. Use
scripts/run_m6_real_adapter_rc_gate.py --preflight-only before any live M6-RC
attempt; current preflight is NOT_READY because the real adapter directory,
adapter files, manifest, Docker image, and host CUDA are missing.
```
