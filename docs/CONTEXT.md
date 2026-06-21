# MIB Studio LLM Context

```yaml
doc_type: llm_bootstrap_context
audience: llm_agents_only
purpose: load_before_planning_or_editing
version: v0.2
updated: 2026-06-21
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

Current planning state:

```yaml
document_state: Implementation-Ready v0.3
M0_Product_Lock: GO
M1_Core: authorized
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

## 8. Program Development Startup

Current development entry point:

```yaml
authorized_milestone: M1_Core
first_required_stage: Day_0_Bootstrap
day_0_source: docs/specs/IMPLEMENTATION_GUIDE.md#4-day-0-bootstrap
m1_ticket_source: docs/specs/IMPLEMENTATION_GUIDE.md#8-m1-core
first_m1_ticket_after_day_0: M1-001 API bootstrap
product_code_started: false
```

Startup sequence for future LLM agents:

```yaml
development_start_sequence:
  - read docs/WORKING.md
  - confirm current_work.status and active milestone
  - read IMPLEMENTATION_GUIDE section 4 for Day-0 Bootstrap readiness
  - check whether Day-0 scaffold files already exist before creating or editing them
  - if Day-0 is incomplete, prepare a Day-0 bootstrap task contract before product code work
  - after Day-0 readiness, read IMPLEMENTATION_GUIDE section 8 and start M1-001 only
  - keep M1 tickets sequential: M1-001 -> M1-002 -> M1-003 -> M1-004 -> M1-005 -> M1-006 -> M1-007
```

Do not start from arbitrary app files. The first implementation decision is
whether Day-0 Bootstrap is already complete. If it is not complete, the next
task is Day-0 scaffold/readiness, not M1 API or UI implementation.

Minimum M1 preparation context:

```yaml
read_for_development_prep:
  - docs/foundation/MIB_Studio_Dev_Plan_v0.3.md section 22 Phase 1
  - docs/foundation/MIB_Studio_Dev_Plan_v0.3.md section 22.8 M1 row
  - docs/specs/IMPLEMENTATION_GUIDE.md section 4 Day-0 Bootstrap
  - docs/specs/IMPLEMENTATION_GUIDE.md section 8 M1 Core implementation tickets
```

Day-0/M1 guardrails:

```yaml
must:
  - keep Docker out of normal M1 development unless the spec explicitly requires export smoke
  - use repo-local .venv for M1-M5 development
  - create the local Python environment with python3 -m venv .venv before installing dependencies
  - keep .venv ignored by git
  - update API, DTO, OpenAPI, generated TS, DB, repository, fixtures, and tests together when contracts change
  - keep the first M1 product implementation limited to M1-001 API bootstrap after Day-0 readiness
  - at verified phase completion, stage explicit files, commit, and push the completed phase
must_not:
  - skip Day-0 readiness
  - implement M1-002+ before M1-001 is complete
  - edit foundation/spec docs unless the task explicitly asks for contract repair
  - claim M1 done without smoke, schema, DB integrity, Hardware Doctor, and review evidence
  - stage, commit, or push before verification passes and phase closeout is reached
```
