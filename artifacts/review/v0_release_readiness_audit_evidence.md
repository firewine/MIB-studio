# v0 Release Readiness Audit Evidence

```yaml
date: 2026-06-22
gate: mib-studio-v0-release-readiness-audit
decision: NOT_GO
release_ready: false
verifier: scripts/verify_v0_release_readiness.py
json_report: artifacts/review/v0_release_readiness_audit.json
```

## Result

The v0 release readiness verifier confirms that FE v6 evidence and the desktop route repair evidence are present.

The current release decision remains `NOT_GO`. The only release blocker reported by the verifier is:

```text
real_trained_adapter_no_fake_endpoint
```

No runtime, API, UI behavior, DB, schema, training, export, or model artifact behavior changed in this gate.

## Current Verified State

```yaml
fe_v6_applied: true
desktop_e2e_route_repair_verified: true
m6_rc_decision: NOT_GO
m6_rc_verification_ok: true
unexpected_blockers: []
acceptable_not_go_blockers:
  - real_trained_adapter_no_fake_endpoint
```

## Diagnostic Prerequisites Still Missing

The M6 real adapter prereq audit remains `NOT_READY_PRECHECK_FAILED`.

```yaml
missing_prereq_ids:
  - adapter_dir_present
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - docker_image_available
  - host_cuda_visible
```

These diagnostics mean a live M6-RC run still needs a real trained CUDA `lora_adapter`, a matching manifest, a tagged exported Docker image, and a CUDA host with `nvidia-smi`.

## Verification

```text
python3 -m json.tool .codex/tasks/current.json
PASS

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/verify_v0_release_readiness.py
PASS

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_verify_v0_release_readiness.py -q
PASS - 4 passed

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
PASS - decision NOT_GO, verification_ok true, unexpected_blockers []

python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
PASS
```

`git diff --check` and `git diff --cached --check` are required before commit.
