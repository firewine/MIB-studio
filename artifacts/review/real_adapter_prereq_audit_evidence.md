# Real Adapter Prerequisite Audit Evidence

Date: 2026-06-22
Gate: `mib-studio-real-adapter-prereq-audit`
Decision: `GO_PREREQ_AUDIT_TOOLING_ONLY_M6_NOT_GO`

## Scope

This phase adds prerequisite audit mode to the real adapter RC gate runner. It
does not create a trained adapter, does not run Docker endpoint transcripts, and
does not mark M6-RC GO.

## Tooling Change

Updated:

```text
scripts/run_m6_real_adapter_rc_gate.py
```

New mode:

```text
--preflight-only
```

The preflight audit checks:

```yaml
fake_backend_env_absent: required
bearer_token_ready: required
adapter_dir_present: required
adapter_safetensors_present: required
adapter_config_present: required
adapter_manifest_present: required
model_cache_dir_present: required
docker_image_available: required
host_cuda_visible: required
```

`--preflight-only` writes a JSON report and does not execute adapter intake,
endpoint capture, or M6 GO verification steps.

## Current Audit Result

Output:

```text
artifacts/review/m6_real_adapter_prereq_audit.json
```

Summary:

```yaml
status: NOT_READY_PRECHECK_FAILED
decision: NOT_READY
m6_rc_claimed_go: false
steps_executed: 0
ready:
  - fake_backend_env_absent
  - bearer_token_ready
  - model_cache_dir_present
not_ready:
  - adapter_dir_present
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - docker_image_available
  - host_cuda_visible
```

Concrete current blockers from the audit:

```yaml
adapter_dir_present: missing adapter directory /tmp/mib-real-adapter/adapter
adapter_safetensors_present: missing adapter.safetensors
adapter_config_present: missing adapter_config.json
adapter_manifest_present: missing adapter manifest /tmp/mib-real-adapter/manifest.json
docker_image_available: No such image mib-export:test
host_cuda_visible: nvidia-smi not found
```

## Verification

```yaml
python3 -m json.tool .codex/tasks/current.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/run_m6_real_adapter_rc_gate.py: pass
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_run_m6_real_adapter_rc_gate.py -q: pass_5_tests
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --preflight-only --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --token 12345678901234567890123456789012 --json-output artifacts/review/m6_real_adapter_prereq_audit.json: pass
python3 -m json.tool artifacts/review/m6_real_adapter_prereq_audit.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json: pass
python3 -m json.tool artifacts/review/m6_rc_evidence_verification.json: pass
git diff --check: pass
git diff --cached --check: pass
```

## Decision

```yaml
real_adapter_prereq_audit_tooling: GO
current_environment_ready_for_live_real_adapter_rc_gate: false
live_real_adapter_endpoint_evidence_present: false
m6_rc_decision: NOT_GO
acceptable_not_go_blocker: real_trained_adapter_no_fake_endpoint
unexpected_blockers: []
```

Next required action is still to provide or train a real CUDA `lora_adapter`,
export a matching Docker image, run on a CUDA host with `nvidia-smi`, and then
execute `scripts/run_m6_real_adapter_rc_gate.py` without `--preflight-only` or
`--plan-only`.
