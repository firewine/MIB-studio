# Real Adapter RC Gate Runner Evidence

Date: 2026-06-22
Gate: `mib-studio-real-adapter-rc-gate-runner`
Decision: `GO_RUNNER_TOOLING_ONLY_M6_NOT_GO`

## Scope

This phase adds a single command runner for the remaining M6-RC real adapter
evidence path. It does not create or provide a real trained adapter, does not
run live Docker endpoint transcripts, and does not mark M6-RC GO in the current
environment.

## Runner

```text
scripts/run_m6_real_adapter_rc_gate.py
```

The runner executes the required M6-RC closeout sequence when a real CUDA
`lora_adapter`, manifest, strict model cache, exported Docker image, and bearer
token are supplied:

```yaml
steps:
  - adapter_intake: scripts/verify_real_adapter_artifact.py
  - endpoint_capture: scripts/capture_real_adapter_endpoint_evidence.py
  - m6_go_verification: scripts/verify_m6_rc_evidence.py --expected-decision GO
```

The runner fails before endpoint capture if adapter intake fails, refuses to run
when `MIB_RUNTIME_ALLOW_FAKE_BACKEND` is set, and redacts bearer token values in
the JSON summary.

## Plan-Only Verification

Command:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --plan-only --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --token 12345678901234567890123456789012 --json-output /tmp/mib-real-adapter-rc-gate-plan.json
```

Result:

```yaml
status: PLAN_ONLY_NOT_RUN
decision: NOT_RUN
m6_rc_claimed_go: false
planned_steps:
  - adapter_intake
  - endpoint_capture
  - m6_go_verification
```

The generated plan JSON passed:

```text
python3 -m json.tool /tmp/mib-real-adapter-rc-gate-plan.json
```

## Verification

```yaml
python3 -m json.tool .codex/tasks/current.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/run_m6_real_adapter_rc_gate.py: pass
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_run_m6_real_adapter_rc_gate.py -q: pass_4_tests
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --plan-only --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --token 12345678901234567890123456789012 --json-output /tmp/mib-real-adapter-rc-gate-plan.json: pass
python3 -m json.tool /tmp/mib-real-adapter-rc-gate-plan.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json: pass
python3 -m json.tool artifacts/review/m6_rc_evidence_verification.json: pass
git diff --check: pass
git diff --cached --check: pass
```

## Decision

```yaml
real_adapter_rc_gate_runner: GO
live_adapter_endpoint_evidence_present: false
runner_plan_only_claims_go: false
current_m6_rc_decision: NOT_GO
acceptable_not_go_blocker: real_trained_adapter_no_fake_endpoint
unexpected_blockers: []
```

To close M6-RC, run this runner without `--plan-only` after a real trained CUDA
adapter and strict external model cache are available.
