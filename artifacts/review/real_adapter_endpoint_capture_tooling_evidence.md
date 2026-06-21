# Real Adapter Endpoint Capture Tooling Evidence

Date: 2026-06-22
Gate: `mib-studio-real-adapter-endpoint-capture-tooling`
Decision: `GO_CAPTURE_TOOLING_ONLY_M6_NOT_GO`

## Scope

This gate adds a standard capture tool for the only remaining M6-RC blocker:
real trained CUDA `lora_adapter` Docker endpoint evidence without
`MIB_RUNTIME_ALLOW_FAKE_BACKEND`.

No real adapter was created or provided in this gate. No product runtime, API,
UI, training, export, schema, or DB behavior changed. M6-RC remains `NOT_GO`.

## Tool

Added:

```text
scripts/capture_real_adapter_endpoint_evidence.py
```

Live capture command shape:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/capture_real_adapter_endpoint_evidence.py \
  --image <real-exported-docker-image> \
  --agent-id <agent_id> \
  --model-cache-dir <strict-model-cache-root> \
  --token <32+ char runtime bearer token> \
  --output artifacts/review/real_trained_adapter_endpoint_evidence.md
```

The script runs Docker with:

```yaml
gpus: all
model_cache_mount: "<strict-model-cache-root>:/models:ro"
env:
  MIB_MODEL_CACHE_DIR: /models
  MIB_RUNTIME_BEARER_TOKEN: "<redacted>"
forbidden_env:
  - MIB_RUNTIME_ALLOW_FAKE_BACKEND
```

The script fails if the parent process has `MIB_RUNTIME_ALLOW_FAKE_BACKEND`
set. It does not pass that env var into Docker.

## Captured Checks

The live capture path verifies:

- `/healthz` returns 200.
- `/agents/{agent_id}/run` returns 200.
- `/v1/chat/completions` returns 200.
- Native endpoint output equals the JSON content returned by the
  OpenAI-compatible endpoint.
- Docker inspect shows no `MIB_RUNTIME_ALLOW_FAKE_BACKEND` env.
- Docker inspect shows `/models` is mounted read-only from the supplied strict
  model cache root.

If all checks pass, the generated markdown includes the exact markers consumed
by `scripts/verify_m6_rc_evidence.py`:

```yaml
Decision: GO_REAL_TRAINED_ADAPTER_ENDPOINT
MIB_RUNTIME_ALLOW_FAKE_BACKEND: absent
/agents/{agent_id}/run: 200
/v1/chat/completions: 200
real_trained_adapter: true
self_test: false
```

## Self-Test

Command:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/capture_real_adapter_endpoint_evidence.py --self-test --output /tmp/mib-real-adapter-endpoint-self-test.md
```

Result:

```json
{"output": "/tmp/mib-real-adapter-endpoint-self-test.md", "self_test": true}
```

The self-test renders the same marker shape but includes:

```yaml
self_test: true
```

`scripts/verify_m6_rc_evidence.py` now rejects `self_test: true` as RC GO
evidence.

## Verification

Focused tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_capture_real_adapter_endpoint_evidence.py -q
```

Result:

```text
4 passed in 0.01s
```

Syntax check:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/capture_real_adapter_endpoint_evidence.py scripts/verify_m6_rc_evidence.py
```

Result: passed.

Current M6 verifier still reports `NOT_GO`:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json
```

Result summary:

```yaml
decision: NOT_GO
verification_ok: true
unexpected_blockers: []
blockers:
  - real_trained_adapter_no_fake_endpoint
```

## Decision

```yaml
real_adapter_endpoint_capture_tooling: GO
self_test_is_not_rc_go_evidence: true
live_real_adapter_endpoint_evidence_present: false
m6_rc: NOT_GO
```

Next required action is to run the live capture command against a real exported
CUDA `lora_adapter` image with a strict external model cache.
