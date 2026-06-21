# Structured Real Endpoint Evidence Tooling

Date: 2026-06-22
Gate: `mib-studio-structured-real-endpoint-evidence`
Decision: `GO_STRUCTURED_EVIDENCE_TOOLING_ONLY_M6_NOT_GO`

## Scope

This phase hardens evidence tooling only. It does not provide a real trained
CUDA `lora_adapter`, does not run live Docker endpoint transcripts, and does not
change product runtime behavior.

## Changes

```yaml
capture_script: scripts/capture_real_adapter_endpoint_evidence.py
verifier_script: scripts/verify_m6_rc_evidence.py
focused_tests: tests/scripts/test_capture_real_adapter_endpoint_evidence.py
m6_verification_output: artifacts/review/m6_rc_evidence_verification.json
```

- The endpoint capture script now writes both markdown evidence and a structured JSON sidecar.
- The JSON sidecar records `source`, `self_test`, adapter intake report path, adapter and artifact manifest SHA-256 hashes, fake-backend absence, read-only model-cache mount state, endpoint statuses, and native/OpenAI output equivalence.
- Live capture refuses adapter intake reports that do not have `GO_REAL_ADAPTER_ARTIFACT_INTAKE` or lowercase SHA-256 hash fields.
- The M6-RC verifier prefers the structured sidecar and rejects markdown-only endpoint evidence as incomplete.
- The M6-RC verifier rejects self-test JSON sidecars as RC GO evidence.

## Structured Sidecar Requirements

```yaml
schema_version: mib_real_adapter_endpoint_evidence.v1
source: live_docker_capture
decision: GO_REAL_TRAINED_ADAPTER_ENDPOINT
self_test: false
adapter_intake_verified: true
adapter_sha256: lowercase_64_hex
artifact_manifest_sha256: lowercase_64_hex
fake_backend_env_absent: true
readonly_model_cache_mount: true
health_status: 200
native_status: 200
openai_status: 200
native_openai_output_equal: true
```

## Verification

```yaml
python3 -m json.tool .codex/tasks/current.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/capture_real_adapter_endpoint_evidence.py scripts/verify_m6_rc_evidence.py: pass
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_capture_real_adapter_endpoint_evidence.py -q: pass_9_tests
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/capture_real_adapter_endpoint_evidence.py --self-test --output /tmp/mib-real-adapter-endpoint-self-test.md --json-output /tmp/mib-real-adapter-endpoint-self-test.json: pass
python3 -m json.tool /tmp/mib-real-adapter-endpoint-self-test.json: pass
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_m6_rc_evidence.py --expected-decision NOT_GO --json-output artifacts/review/m6_rc_evidence_verification.json: pass
python3 -m json.tool artifacts/review/m6_rc_evidence_verification.json: pass
git diff --check: pass
git diff --cached --check: pass
```

## Decision

```yaml
structured_endpoint_json_tooling: GO
markdown_only_endpoint_evidence_rejected: true
self_test_json_rejected: true
live_real_adapter_endpoint_evidence_present: false
m6_rc_decision: NOT_GO
acceptable_not_go_blocker: real_trained_adapter_no_fake_endpoint
unexpected_blockers: []
```

M6-RC remains `NOT_GO` until a real trained adapter is available and live
no-fake-backend Docker endpoint evidence is captured with the structured JSON
sidecar.
