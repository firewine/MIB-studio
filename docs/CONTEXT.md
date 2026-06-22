# MIB Studio LLM Context

```yaml
doc_type: llm_bootstrap_context
audience: llm_agents_only
purpose: load_before_planning_or_editing
version: v0.3
updated: 2026-06-23
canonical_ssot: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
active_state: docs/WORKING.md
```

## 0. How To Use This File

Read this file before planning or editing. It is a compressed project map for
LLM agents. It is not the source of truth for requirements, architecture,
security, benchmark rules, or acceptance criteria.

Operational rules:

1. Treat `docs/foundation/MIB_Studio_Dev_Plan_v0.3.md` as the canonical SSOT.
2. Treat `docs/specs/*` as the detailed contracts referenced by the SSOT.
3. Treat `docs/WORKING.md` as the current active-task state.
4. Do not infer missing requirements from this file. If detail matters, read the relevant SSOT/spec section.
5. Do not duplicate SSOT content into new docs. Link to the owning doc instead.

## 1. Project Definition

MIB Studio means **MicroAgent Inventor Blocks**.

One-line product definition:

```text
MIB Studio is a local-first desktop GUI for building narrow specialist Small Agents
from rules, examples, synthetic data, fine-tuning, evaluation, packaging, and export.
```

The v0 product proves one workflow end to end:

```text
Router preset
  -> rules/examples
  -> reviewed synthetic/hard-negative data
  -> CUDA QLoRA or Apple Silicon MLX LoRA training
  -> benchmark against prompt-only, cloud teacher, and rule-only baselines
  -> Agent Contract + Playground
  -> package/export artifact
```

Current development state:

```yaml
document_state: Implementation-Ready v0.3
M0_Product_Lock: GO
M1_to_M5_Local_Evidence: verified
FE_V6_Mockup_Verified: true
FE_V6_Route_Contract_Persistence_Verified: true
FE_V6_Train_Workflow_Unlocked: true
FE_V6_Benchmark_Workflow_Unlocked: true
FE_V6_Package_Playground_Workflow_Unlocked: true
FE_V6_Export_Workflow_Unlocked: true
M6_RC_Signoff: NOT_GO
V0_Release_Readiness: NOT_GO
sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
target_user_v0: tech-savvy work user who can handle GPU/Python environments
```

## 2. Canonical Sources

Use this routing table instead of loading every doc.

```yaml
dev_plan:
  path: docs/foundation/MIB_Studio_Dev_Plan_v0.3.md
  owns:
    - principles
    - phases
    - acceptance criteria
    - milestone gates
    - risks

product_scope:
  path: docs/specs/MVP_SCOPE.md
  owns:
    - v0 included scope
    - v0.2+ deferred scope
    - excluded scope

architecture:
  path: docs/specs/ARCHITECTURE.md
  owns:
    - Tauri/React/FastAPI/Worker shape
    - SQLite job queue
    - daemon/worker/runtime boundaries
    - DB and API contracts

implementation:
  path: docs/specs/IMPLEMENTATION_GUIDE.md
  owns:
    - ticket order
    - file responsibility
    - DTO/API/test update rules

security:
  path: docs/specs/SECURITY_SPEC.md
  owns:
    - local API auth
    - keychain policy
    - egress allowlist
    - Teacher Packet approval
    - PII masking

evaluation:
  path: docs/specs/EVAL_SPEC.md
  owns:
    - benchmark protocol
    - overlap checks
    - seed/CI/report hash rules

preset_data:
  path: docs/specs/PRESET_SPEC.md
  owns:
    - Router preset
    - dataset and schema formats

hardware_training:
  path: docs/specs/HARDWARE_DOCTOR_SPEC.md
  owns:
    - G0/G1/G2 hardware gates
    - CUDA/MLX support assumptions

agent_contract:
  path: docs/specs/AGENT_CONTRACT_SPEC.md
  owns:
    - Agent Package
    - verifier
    - fallback and audit rules

ux:
  path: docs/specs/UX_SPEC.md
  owns:
    - screens
    - workflow
    - UI states
  canonical_mockup: docs/mockup/mib_fe_mockup_v6_routes_contract.html
  evidence: artifacts/review/fe_v6_evidence.md
```

## 3. System Mental Model

```text
MIB Studio Desktop
  Tauri shell + React UI
  Calls localhost daemon only.

MIB Local Daemon
  FastAPI localhost API.
  Owns Project, Preset, Dataset, Job, Model Registry, auth, egress policy, audit.

MIB Worker
  Separate process for long-running or risky work.
  Owns dataset generation, teacher calls, training wrappers, eval, packaging, export.

Local Storage
  SQLite WAL queue + project DB + project files + adapters + reports + export artifacts.

Optional Cloud
  v0 only supports BYO OpenAI-compatible Teacher egress after preview and approval.
```

Boundary constraints:

```yaml
ui:
  must_not:
    - own training logic
    - own security authorization
    - invent benchmark numbers
  route_contract_v6_persistence:
    project_route_fields:
      - task_type
      - requires_calculation
      - requires_human_review
      - is_default
      - examples
    required_behavior:
      - project API and desktop save/reload preserve the edited v6 route contract fields
      - dataset route_snapshot_json preserves the same fields for downstream traceability
  train_workflow_v6:
    route: /projects/{id}/training
    uses_existing_apis:
      - POST /projects/{id}/jobs with type=train
      - GET /projects/{id}/model-runs
    required_frontend_gates:
      - approved dataset
      - Hardware Doctor training_enabled result
    owns:
      - route navigation
      - submission request display
      - queued job/model-run status display
    does_not_own:
      - training execution
      - worker scheduling
      - adapter artifact creation
      - release evidence
  benchmark_workflow_v6:
    route: /projects/{id}/benchmarks/new
    uses_apis:
      - POST /projects/{id}/jobs with type=benchmark
      - GET /projects/{id}/model-runs
      - GET /projects/{id}/eval-sets
      - GET /projects/{id}/benchmarks
      - GET /benchmarks/{id}/report
    required_runtime_gates:
      - frozen benchmark_gold or finance_reference EvalSet
      - completed fine_tuned ModelRun with adapter lineage
      - prompt_only, fine_tuned, teacher, and rule_based targets
      - at least three unique seeds
    ui_must:
      - display only daemon/worker-provided benchmark report data
      - label mock browser data as mock-only and not release evidence
    ui_must_not:
      - invent benchmark numbers
      - treat queued benchmark jobs as completed benchmark evidence
      - change release readiness
  package_playground_workflow_v6:
    route: /projects/{id}/packages
    uses_apis:
      - POST /projects/{id}/agent-packages
      - GET /projects/{id}/agent-packages
      - GET /agent-packages/{agent_package_id}
      - POST /agent-packages/{agent_package_id}/playground-runs
    required_runtime_gates:
      - completed ModelRun with adapter metadata
      - completed Benchmark with VALID report hash
    ui_must:
      - display backend-created contract_yaml as immutable package output
      - display Playground verifier status, fallback flags, and audit event id from API response
    ui_must_not:
      - edit agent contract YAML locally
      - call exported /agents/{agent_id}/run route inside the local daemon
      - treat package/playground smoke as export or release evidence
  export_workflow_v6:
    route: /projects/{id}/export
    uses_apis:
      - GET /projects/{id}/agent-packages
      - POST /projects/{id}/export
      - GET /exports/{job_id}
      - POST /exports/{job_id}/reveal
    required_runtime_gates:
      - existing AgentPackage for the project
    ui_must:
      - submit zip export through the daemon export endpoint
      - display daemon-provided ExportRead status, manifest_sha256, artifact_sha256, artifact_url, and reveal_url
      - keep Docker/runtime/release evidence boundaries explicit
    ui_must_not:
      - create or edit export artifacts locally
      - recompute or manually enter export hashes
      - treat browser mock export output as M6-RC or v0 release evidence

daemon:
  must:
    - bind to localhost
    - enforce bearer auth
    - validate job requests
    - own DB writes and approvals

worker:
  must:
    - isolate CUDA/MLX work from daemon/UI
    - write JobEvent progress
    - preserve artifact lineage

local_runtime:
  purpose: inference only
  must_not:
    - write Job or JobEvent state
```

## 4. Locked v0 Decisions

```yaml
v0_preset: Router only
base_models:
  - google/gemma-2b-it
  - microsoft/Phi-3.5-mini-instruct
training_backends:
  nvidia: CUDA + LLaMA-Factory QLoRA
  apple_silicon: MLX 4-bit LoRA
  amd_intel: no v0 training support
benchmark_targets_required:
  - fine_tuned
  - prompt_only
  - cloud_teacher
  - rule_only
benchmark_targets_optional:
  - local_large
export_required:
  - agent_package_zip
  - Docker runtime API where available
  - OpenAI-compatible endpoint wrapper
```

Deferred beyond v0:

```yaml
deferred:
  - Extractor preset
  - Rule Selector preset
  - Review Router preset
  - Report Draft preset
  - preset marketplace
  - multi-user collaboration
  - RBAC
  - managed GPU
  - advanced RLHF/RL training
  - full automatic agent orchestration
```

## 5. Non-Negotiable Rules

Product and scope:

```yaml
must:
  - keep v0 focused on Router
  - preserve local-first positioning
  - frame Small Agents as low-cost specialists with fallback, not full LLM replacement
must_not:
  - expand scope without SSOT/spec update
  - claim enterprise/air-gapped features before implementation
```

Security:

```yaml
must:
  - store API keys in OS keychain only
  - keep local API bound to 127.0.0.1 with bearer token auth
  - require Teacher Packet Preview and approval before egress
  - send only rules, schema, anonymized examples, and instruction to Teacher
must_not:
  - store secrets in SQLite, files, logs, tests, docs, or fixtures
  - send raw CSV, file paths, PII, or unapproved samples externally
  - claim "data never leaves the machine" without qualifying Cloud Teacher mode
```

Training and evaluation:

```yaml
must:
  - keep long jobs in the persistent Job queue
  - isolate training in worker subprocesses
  - verify model cache/hash lineage
  - generate benchmark reports from eval runner data
  - record overlap, seeds, confidence intervals, and report hash
must_not:
  - enter benchmark numbers manually
  - package a ModelRun without completed benchmark and valid report hash
  - show CUDA/MLX joint claims before parity gate result
```

Agent package and export:

```yaml
must:
  - validate outputs through schema and verifier
  - show fallback conditions clearly
  - require user approval before external fallback calls
  - include manifest, hashes, benchmark report, and secret scan in export evidence
```

## 6. Milestone Map

```yaml
M1_Core:
  goal: project + Router preset + rules/examples + SQLite persistence + training JSONL + Hardware Doctor
  hard_stop_if:
    - JSONL schema mismatch
    - DB restart loses state
    - unsupported hardware can start training
    - API/FE DTO drift

M2_Teacher_Data:
  goal: keychain + packet preview + PII masking + synthetic/hard-negative generation + human review
  hard_stop_if:
    - plaintext key storage
    - egress differs from preview
    - dataset created without review
    - EvalSet not frozen before synthetic generation

M3_Training:
  goal: locked base model LoRA/QLoRA/MLX training + checkpoint/resume + worker isolation
  hard_stop_if:
    - unverified model download
    - no resume path
    - OOM kills daemon/UI
    - adapter lineage missing

M4_Benchmark:
  goal: reproducible comparison report with overlap checks, seeds, CI, and report hash
  hard_stop_if:
    - manual benchmark numbers
    - train/eval contamination
    - missing seed/CI
    - parity decision missing for CUDA/MLX report

M5_Package_Playground:
  goal: Agent Contract + verifier + playground + fallback/audit UX
  hard_stop_if:
    - package without completed benchmark
    - schema-invalid responses displayed as valid
    - fallback auto-calls external provider
    - audit missing

M6_Export_RC:
  goal: zip native runtime + Docker/OpenAI-compatible runtime where available + secret-scanned export
  hard_stop_if:
    - zip export requires Docker
    - export contains secrets
    - OpenAI-compatible wrapper fails
    - package/export output mismatch
```

## 7. Before Any Edit

LLM agents must complete this checklist before editing:

```yaml
pre_edit_checklist:
  - read docs/WORKING.md
  - identify the active milestone or confirm no active work
  - read only the relevant SSOT/spec sections
  - declare allowed files and blocked files
  - avoid changing specs/foundation docs unless the task explicitly asks for it
  - update API/DTO/DB/schema/tests together when any contract changes
  - keep generated claims tied to verification evidence
```

If required context is missing, stop and update the task contract or ask for the
missing gate/handoff before implementation.

## 8. Program Development Continuation / Closeout

Current development entry point:

```yaml
current_development_state: v0_release_closeout
authorized_milestone: V0_Release_Closeout
product_code_started: true
frontend_canonical_mockup: docs/mockup/mib_fe_mockup_v6_routes_contract.html
frontend_evidence: artifacts/review/fe_v6_evidence.md
latest_operational_state: docs/WORKING.md
release_readiness_report: artifacts/review/v0_release_readiness_audit.json
release_blocker_recertification: artifacts/review/v0_release_blocker_recertification.json
cuda_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.json
external_cuda_operator_packet: artifacts/review/external_cuda_operator_packet.json
external_cuda_operator_packet_verification: artifacts/review/external_cuda_operator_packet_verification.json
verified_external_cuda_training_launcher: artifacts/review/verified_external_cuda_training_launcher.sh
external_cuda_operator_packet_source_commit: a1dd0cc
strict_model_cache_preparation: artifacts/review/strict_model_cache_preparation.json
current_local_release_decision: NOT_GO
current_recertification_status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
current_recertification_head: 20701d1
current_local_unexpected_blockers: []
sole_expected_release_blocker: real_trained_adapter_no_fake_endpoint
primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
```

Continuation sequence for future LLM agents:

```yaml
development_continuation_sequence:
  - read docs/WORKING.md
  - read .codex/tasks/current.json
  - read only the SSOT/spec sections relevant to the active closeout slice
  - do not restart from M1 or Day-0 bootstrap
  - create_or_update_pabcd_contract_before_edits
  - keep allowed_edit_paths narrow and explicit
  - use scripts/run_v0_release_blocker_recertification.py for current blocker/action refreshes
  - verify current release state with scripts/verify_v0_release_readiness.py
  - stage_commit_push_after_verified_phase_completion
```

The FE requirement from the user objective is already represented by the v6
route-contract mockup and evidence:

```yaml
FE_V6_Mockup_Verified: true
FE_V6_Train_Workflow_Unlocked: true
FE_V6_Benchmark_Workflow_Unlocked: true
FE_V6_Package_Playground_Workflow_Unlocked: true
FE_V6_Export_Workflow_Unlocked: true
canonical_mockup: docs/mockup/mib_fe_mockup_v6_routes_contract.html
evidence: artifacts/review/fe_v6_evidence.md
verifier_check: fe_v6_applied
train_workflow_evidence:
  - apps/desktop/e2e/m1_happy_path.test.mjs covers dataset approval, Hardware Doctor, Train submit, queued model run, and job monitor in mock/browser smoke
benchmark_workflow_evidence:
  - tests/eval/test_benchmark_submit.py covers backend benchmark job queueing with frozen EvalSet, completed ModelRun, teacher credential, required targets, seeds, and idempotency
  - apps/desktop/e2e/m1_happy_path.test.mjs covers AgentBench navigation, benchmark submit, mock-only report display, and benchmark job monitor in browser smoke
package_playground_workflow_evidence:
  - tests/agent_package/test_contract_builder.py::test_agent_package_builder_creates_schema_valid_immutable_contract covers backend package creation contract validity
  - tests/playground/test_playground_local_inference.py::test_playground_run_returns_verified_json_output_and_audit_event covers local Playground verifier/audit response
  - apps/desktop/e2e/m1_happy_path.test.mjs covers Package navigation, package build, Playground run, verifier output, and audit id in browser smoke
export_workflow_evidence:
  - tests/export/test_export_api.py covers backend export job creation, ExportRead, hash-verified artifact serving, reveal response, and Docker unavailable behavior
  - apps/desktop/e2e/m1_happy_path.test.mjs covers Export navigation, zip export submit, daemon-provided manifest/artifact hash display, and reveal action in browser smoke
release_impact: no_release_go_claim
```

The remaining release path is evidence-driven, not a normal M1-M6 feature
implementation loop:

```yaml
required_before_release_go:
  - real trained CUDA lora_adapter artifact:
      adapter_dir: /tmp/mib-real-adapter/adapter
      manifest: /tmp/mib-real-adapter/manifest.json
  - strict base-model cache prepared from pinned presets/model_catalog.yaml files
  - digest-pinned CUDA/Python Docker base image on the CUDA host
  - mib-export:test image built with the real adapter
  - no-fake-backend live Docker endpoint evidence
  - accepted review of that endpoint evidence
  - M6 review docs changed to GO only after the evidence is accepted
  - GO_REAL_ADAPTER_EVIDENCE_BUNDLE promoted into artifacts/review
  - accepted M6 GO review docs present in the same release workstation checkout before local bundle closeout
  - v0 release readiness decision GO
```

Current actionable NOT_GO recertification summary:

```yaml
summary_file: artifacts/review/v0_release_blocker_recertification.json
current_head: 20701d1
top_level_fields:
  - blocking_reasons
  - operator_next_actions
  - primary_external_handoff
current_status: NOT_GO_V0_RELEASE_BLOCKER_RECERTIFICATION
recertification_ok: true
release_claimed_go: false
primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
v0_unexpected_blockers: []
sole_v0_blocker: real_trained_adapter_no_fake_endpoint
current_blocking_reasons_include:
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
next_actions_are_in_artifact: true
first_operator_action: run artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host so packet verification runs before training handoff execution
strict_model_cache_action: run ./.venv/bin/python scripts/prepare_strict_model_cache.py --base-model microsoft/Phi-3.5-mini-instruct --backend cuda --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --allow-download --expected-status READY_STRICT_MODEL_CACHE before CUDA training preflight
```

Current external CUDA training handoff package:

```yaml
handoff_file: artifacts/review/real_adapter_cuda_training_handoff.json
status: PREPARED_NOT_RUN
release_claimed_go: false
top_level_fields:
  - package_readiness_checks
  - command_sequence
strict_model_cache_report: artifacts/review/strict_model_cache_preparation.json
command_order_prefix:
  - resolve_cuda_base_image
  - prepare_strict_model_cache
  - preflight_cuda_training
shell_guarded_prereqs:
  - dataset_jsonl_present
  - python_executable_present
  - llamafactory_cli_present
  - model_cache_dir_present
  - backend_config_present
  - rc_handoff_shell_present
purpose: fail fast on CUDA host package/setup mistakes before real adapter training and endpoint evidence capture
```

Current external CUDA operator packet:

```yaml
packet_json: artifacts/review/external_cuda_operator_packet.json
packet_markdown: artifacts/review/external_cuda_operator_packet.md
packet_verification: artifacts/review/external_cuda_operator_packet_verification.json
schema_version: mib_external_cuda_operator_packet.v1
status: PREPARED_NOT_RUN
release_claimed_go: false
handoff_source_commit: a1dd0cc
primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
recertification_primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
required_committed_files_count: 17
required_committed_files_include:
  - artifacts/review/verified_external_cuda_training_launcher.sh
  - scripts/prepare_strict_model_cache.py
training_handoff_command_order_include:
  - prepare_strict_model_cache
operator_sequence_rule:
  - keep this packet file from the current checkout
  - treat packet.git.head as the required committed file source commit for verifier blob checks
forbidden_committed_artifacts:
  - model weights
  - LoRA adapter files
  - Docker image layers or archives
  - raw live endpoint transcripts
  - copied external real-adapter evidence bundles
```

Current external CUDA operator packet verification:

```yaml
verification_json: artifacts/review/external_cuda_operator_packet_verification.json
schema_version: mib_external_cuda_operator_packet_verification.v1
decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
operator_packet_ready: true
release_claimed_go: false
m6_rc_claimed_go: false
validated:
  - packet contract and no-GO claims
  - 17 required committed file sha256/size values
  - 17 required committed file blobs at handoff source commit a1dd0cc
  - operator sequence keeps the packet file from the current checkout
  - primary handoff must be the verified launcher, not the lower-level training handoff
  - packet.git.head resolves even when current checkout is a later closeout commit
  - 6 package readiness checks
  - training/RC/local-closeout command order
  - forbidden committed artifact labels
  - no forbidden tracked model/adapter/Docker/endpoint/bundle artifacts
warning: none
meaning: packet integrity is GO; M6-RC and v0 release remain NOT_GO until real adapter endpoint evidence exists
```

Current verified external CUDA training launcher:

```yaml
launcher_json: artifacts/review/verified_external_cuda_training_launcher.json
launcher_markdown: artifacts/review/verified_external_cuda_training_launcher.md
launcher_shell: artifacts/review/verified_external_cuda_training_launcher.sh
schema_version: mib_verified_external_cuda_training_launcher.v1
status: PREPARED_NOT_RUN
release_claimed_go: false
m6_rc_claimed_go: false
sequence:
  - verify_external_cuda_operator_packet:
      command: scripts/verify_external_cuda_operator_packet.py --packet-json artifacts/review/external_cuda_operator_packet.json --expected-decision GO
      required_decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
  - run_real_adapter_cuda_training_handoff:
      command: bash artifacts/review/real_adapter_cuda_training_handoff.sh
meaning: this is the preferred external CUDA host entrypoint; it still does not claim release GO
```

Recommended external CUDA host sequence:

```yaml
external_cuda_host_sequence:
  - run bash artifacts/review/verified_external_cuda_training_launcher.sh
  - run artifacts/review/real_adapter_docker_image_handoff.sh
  - run scripts/run_m6_real_adapter_rc_gate.py --endpoint-evidence-only
  - review artifacts/review/real_trained_adapter_endpoint_evidence.md and .json
  - update docs/reviews/M6/SIGNOFF_MATRIX.md and docs/reviews/M6/CTO_DECISION.md to GO only after accepted evidence review
  - run scripts/run_m6_real_adapter_rc_gate.py --m6-verification-only
  - run scripts/build_real_adapter_evidence_bundle.py --archive-output artifacts/review/real_adapter_evidence_bundle.tar.gz
```

Recommended local closeout after transferring a GO bundle:

```yaml
local_closeout_command: >
  PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python
  scripts/run_v0_release_closeout_from_bundle.py
  --bundle-archive <copied_real_adapter_evidence_bundle.tar.gz>
  --expected-bundle-decision GO
  --expected-readiness-decision GO
same_release_workstation_checkout_required: true
requires_local_m6_review_docs_go:
  - docs/reviews/M6/SIGNOFF_MATRIX.md
  - docs/reviews/M6/CTO_DECISION.md
missing_local_m6_review_docs_go_status: m6_review_docs_not_current
expected_success_status: GO_V0_RELEASE_CLOSEOUT
not_go_summary_fields:
  - blocking_reasons
  - operator_next_actions
recertification_not_go_summary_fields:
  - blocking_reasons
  - operator_next_actions
```

Closeout guardrails:

```yaml
must:
  - use repo-local .venv for Python commands
  - keep .venv ignored by git
  - keep release claims tied to verifier evidence
  - treat fixture adapters, self-tests, and mockup values as non-release evidence
  - preserve FE v6 as the canonical frontend implementation baseline unless UX_SPEC changes
must_not:
  - claim M6-RC GO or v0 GO from current local artifacts
  - edit docs/reviews/M6 to GO before accepted real no-fake endpoint evidence exists
  - weaken verifier acceptance criteria to pass without real adapter evidence
  - commit model weights, adapter artifacts, Docker images, endpoint transcripts, or copied external bundles unless a future scoped gate explicitly allows it
  - stage, commit, or push before verification passes and phase closeout is reached
```
