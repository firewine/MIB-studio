---
name: pabcd-gate-protocol
description: Use when a GetBeta task is run by phase or gate using the PABCD flow, Gate 1-7, plan/audit/build/check/done, or docs/guides/VS_CODE_MULTI_AGENT_GATE_PROTOCOL_V4.md. Enforces baseline lock, documentation authority, multi-agent review, approved scope, verification, and closeout rules for Codex CLI work.
---

# GetBeta PABCD Gate Protocol

Use this skill for any GetBeta development goal that is split into phases and
run through PABCD:

- P: Plan
- A: Audit
- B: Build
- C: Check
- D: Done

The canonical protocol is
`docs/guides/VS_CODE_MULTI_AGENT_GATE_PROTOCOL_V4.md`. Read only the sections
needed for the current gate.

## Gate Map

- Gate 1: detailed planning only. No implementation.
- Gate 2: revised planning and CTO handoff. No implementation.
- Gate 2R: planning remediation and unlock preparation. No runtime code.
- Gate 3: draft code proposal only after explicit approval. Do not apply final code.
- Gate 4: revised draft review and final implementation handoff. No implementation.
- Gate 5: approved implementation, validation, and approved doc updates.
- Gate 5R: post-implementation review-only checkpoint. Do not modify files.
- Gate 6: remediation planning only. No remediation implementation.
- Gate 7: approved remediation, final validation, live code/live docs closeout, and commit/push only if explicitly approved. Gate 7 means the phase is complete.

PABCD mapping:

- P = Gate 1, Gate 2, and Gate 2R when planning needs remediation.
- A = Gate 3 and Gate 4.
- B = Gate 5.
- C = Gate 5R and Gate 6 when issues are found.
- D = Gate 7 for approved remediation closeout, or Gate 5R closeout when no remediation is required.

## Required First Steps

Before every gate:

1. Run and report:
   - `pwd`
   - `git branch --show-current`
   - `git rev-parse --short HEAD`
   - `git status --short`
2. Declare:
   - workspace root
   - branch
   - HEAD
   - approved scope
   - blocked scope
   - allowed files
   - blocked files
3. Lock documentation authority:
   - authoritative docs root: `/home/firewine/getbeta/docs`
   - allowed live docs: `docs/CONTEXT.md`, `docs/WORKING.md`, `docs/plans/**`, `docs/issues/**`, approved `docs/verification/**`, approved `docs/guides/**`
   - reference-only: temp folders, Downloads, Desktop, archive docs, backups, scratch files, prompt exports, and other worktrees
4. Create or update `.codex/pabcd-state.json` from `.codex/pabcd-state.example.json` when hooks should enforce the gate.

## Review Discipline

Do not perform a solo review.

When Codex CLI must use subagents for PABCD multi-agent work, prefer the
native Codex subagent tools (`multi_agent_v1.spawn_agent`, `wait_agent`,
`send_input`, `close_agent`, and `resume_agent`) over Hermes. Do not use
Hermes as the default subagent executor. Use Hermes only when the user
explicitly asks for Hermes, the native Codex subagent tools are unavailable, or
an approved gate instruction requires Hermes; state the reason before using it.

For planning, review, remediation, and implementation gates, follow:

1. Independent team reviews
2. Cross-review loop 1
3. Revised packet
4. Cross-review loop 2
5. CTO synthesis

Use only the smallest adequate team set. Default required teams are BE/API,
LLM, Security, QC, and CTO. Add DB, FE, and Doc Gardener only when relevant.

## Gate Guardrails

- Do not implement code in Gate 1, Gate 2, Gate 2R, Gate 3, Gate 4, Gate 5R, or Gate 6.
- Do not start Gate 3 without explicit approval of the prior CTO packet.
- Do not start Gate 5 without explicit approval of the Gate 4 CTO handoff.
- Do not start Gate 7 without explicit approval of the Gate 6 CTO remediation handoff.
- Record required user approval in approved live docs before code changes in Gate 5 or Gate 7.
- Do not stage, commit, or push unless the current gate explicitly approves it.
- Stop and report contamination if any work reads or edits outside the declared workspace root.
- Stop and report doc-target contamination if any doc update targets a non-authoritative path.
- Gate 7 requires all required teams to be GO before closeout.
- Gate 7 must apply final code and documentation into the real workspace and approved live docs. Do not close Gate 7 with patches, notes, or results only in temp folders, Downloads, Desktop, scratch files, prompt exports, other worktrees, or archive docs.
- Gate 7 completion means the phase is complete. Do not leave "hard parts" as deferred slices.
- If a problem truly cannot be finished inside the phase without splitting scope, stop and ask the user for explicit approval to split it out, even when the approval mode is automatic.

## Build And Remediation

Gate 5 and Gate 7 must use draft-first work:

1. draft implementation or patch plan
2. cross-code-review loop 1
3. revised draft
4. cross-code-review loop 2
5. CTO consolidation
6. apply only the CTO-approved final version

After code changes, run the required focused tests, regression tests, Security
validation, QC validation, diagnostics, `git diff --check`, direct local
verification on the real local runtime, and browser smoke when frontend, auth,
session, API-consumer, or chatbot behavior is affected.

## Gate 7 Phase Completion Rule

Gate 7 is not a partial-delivery gate.

Before claiming Gate 7 complete:

- all required teams must be `GO`
- approved runtime code changes must be present in the real workspace
- approved live documentation updates must be present under `/home/firewine/getbeta/docs`
- completion log must be updated
- direct verification evidence must reflect the live code path, not a temp patch or copied file
- `phase_complete` must be true in `.codex/pabcd-state.json`
- no unapproved `deferred_followups` may remain

Allowed exception: if the phase cannot be completed without splitting scope,
ask the user for explicit approval to create a separate follow-up. Record that
approval in live docs and in `.codex/pabcd-state.json` using
`deferred_split_approved_by_user=true` plus `approved_deferred_items`.

## God File Check

For touched source files:

- report line counts in final gate output
- treat 900+ lines as a decomposition warning
- treat 1,000+ lines as a blocker unless the gate explicitly accepts it
- do not create vague dump files such as `utils.py`, `helpers.py`, `misc.py`, `common.py`, or `shared.py` without narrow ownership

## Final Gate Output

Every final gate report must include:

- baseline path, branch, and HEAD
- contamination check result
- authoritative docs root
- approved doc files
- reference-only files consulted
- docs updated
- docs intentionally not updated
- remaining doc drift
- whether the development plan matches the implemented state
- Gate 7 only: phase completion statement and any user-approved split-out items
- touched file line counts when files changed
- tests and verification results when required
- final CTO verdict or closeout recommendation

After completing any task, add a short Korean summary to
`docs/plans/2026-05-09_COMPLETION_LOG.md`.
