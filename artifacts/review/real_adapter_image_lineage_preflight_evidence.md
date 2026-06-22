# Real Adapter Image Lineage Preflight Evidence

```yaml
date: 2026-06-22
gate: mib-studio-real-adapter-image-lineage-preflight
decision: GO_PREFLIGHT_HARDENING_ONLY_M6_NOT_GO
runner: scripts/run_m6_real_adapter_rc_gate.py
json_report: artifacts/review/m6_real_adapter_prereq_audit.json
```

## Result

The M6 real-adapter RC runner preflight now checks Docker image adapter lineage when the submitted adapter manifest has `adapter_sha256` and the Docker image is available.

This prevents a stale or fixture export image from satisfying the real-adapter closeout path only because the tag exists.

M6-RC remains `NOT_GO`; this gate does not provide a real trained CUDA `lora_adapter`, a matching Docker image, or live no-fake endpoint transcripts.

## Added Guard

```yaml
check_id: docker_image_adapter_matches_adapter_manifest
condition:
  - adapter manifest includes lowercase adapter_sha256
  - adapter directory is present
  - Docker image is available
action:
  - run the image with a Python one-shot command
  - compute aggregate SHA-256 of /app/adapter files using the same canonical row shape as adapter intake
  - compare image adapter hash with submitted adapter manifest adapter_sha256
failure:
  - preflight decision stays NOT_READY or NOT_GO before endpoint capture
```

In the current environment the guard is skipped because the real adapter manifest, adapter directory, and `mib-export:test` image are missing. The other required preflight checks still report `NOT_READY_PRECHECK_FAILED`.

## Current Preflight State

```yaml
status: NOT_READY_PRECHECK_FAILED
decision: NOT_READY
m6_rc_claimed_go: false
new_guard:
  id: docker_image_adapter_matches_adapter_manifest
  ok: true
  skipped: true
  skipped_prereq_ids:
    - adapter_manifest_sha256_unavailable
    - adapter_dir_present
    - docker_image_available
remaining_missing_prereqs:
  - adapter_dir_present
  - adapter_safetensors_present
  - adapter_config_present
  - adapter_manifest_present
  - docker_image_available
  - host_cuda_visible
```

## Verification

```text
python3 -m json.tool .codex/tasks/current.json
PASS

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/run_m6_real_adapter_rc_gate.py
PASS

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_run_m6_real_adapter_rc_gate.py -q
PASS - 7 passed

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --preflight-only --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --token 12345678901234567890123456789012 --json-output artifacts/review/m6_real_adapter_prereq_audit.json
PASS - status NOT_READY_PRECHECK_FAILED, decision NOT_READY

python3 -m json.tool artifacts/review/m6_real_adapter_prereq_audit.json
PASS

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
PASS - decision NOT_GO, verification_ok true, unexpected_blockers []

python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
PASS
```

`git diff --check` and `git diff --cached --check` are required before commit.
