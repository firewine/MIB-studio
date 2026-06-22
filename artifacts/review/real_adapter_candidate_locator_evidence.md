# Real Adapter Candidate Locator Evidence

```yaml
date: 2026-06-22
gate: mib-studio-real-adapter-candidate-locator
decision: GO_LOCATOR_TOOLING_ONLY_M6_NOT_GO
locator: scripts/find_real_adapter_candidates.py
json_report: artifacts/review/real_adapter_candidate_scan.json
```

## Result

The project now has reusable tooling to locate submitted or newly trained CUDA `lora_adapter` candidates and turn GO intake candidates into `scripts/run_m6_real_adapter_rc_gate.py` commands.

The current scan found no GO real-adapter candidates and does not claim M6-RC GO.

The hook-required M1 smoke bootstrap also passes after restoring the route-contract source sentinel in `apps/desktop/src/main.mjs` breadcrumb text.

## Current Scan

```yaml
roots:
  - /home/firewine/MIB-studio
  - /tmp/mib-real-adapter
  - /tmp/mib-phi-docker-export-_vgqfd4g
decision: NO_GO_CANDIDATES_FOUND
candidate_count: 2
go_candidate_count: 0
fixture_like_candidate_count: 2
m6_rc_claimed_go: false
```

The two candidates are existing Phi fixture adapter paths. Both are rejected by the existing real adapter intake rules because they are fixture-sized, have invalid safetensors, and do not provide a valid locked-base-model LoRA adapter config/manifest.

## Locator Behavior

```yaml
scan:
  - explicit roots only
  - ignores .git, .venv, __pycache__, and node_modules
candidate_rule:
  - directory contains adapter.safetensors
  - directory contains adapter_config.json
validation:
  - reuses scripts/verify_real_adapter_artifact.py intake rules
go_output:
  - emits rc_gate_command for GO_REAL_ADAPTER_ARTIFACT_INTAKE candidates
  - command includes adapter dir, manifest, base model, image, agent id, model cache, and output paths
```

## Verification

```text
python3 -m json.tool .codex/tasks/current.json
PASS

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/find_real_adapter_candidates.py
PASS

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_find_real_adapter_candidates.py -q
PASS - 3 passed

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/find_real_adapter_candidates.py --root /home/firewine/MIB-studio --root /tmp/mib-real-adapter --root /tmp/mib-phi-docker-export-_vgqfd4g --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache/model_cache --expected-go-candidates 0 --json-output artifacts/review/real_adapter_candidate_scan.json
PASS - go_candidate_count 0

python3 -m json.tool artifacts/review/real_adapter_candidate_scan.json
PASS

PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision NOT_GO --json-output artifacts/review/v0_release_readiness_audit.json
PASS - decision NOT_GO, verification_ok true, unexpected_blockers []

python3 -m json.tool artifacts/review/v0_release_readiness_audit.json
PASS

COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
PASS - tests/smoke/test_m1_smoke.py 1 passed

git diff --check
PASS

git diff --cached --check
PASS after staging this phase
```
