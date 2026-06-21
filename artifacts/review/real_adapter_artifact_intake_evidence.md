# Real Adapter Artifact Intake Evidence

Date: 2026-06-22
Gate: `mib-studio-real-adapter-artifact-intake`
Decision: `GO_INTAKE_TOOLING_ONLY_M6_NOT_GO`

## Scope

This gate adds real CUDA `lora_adapter` artifact intake verification and wires
that prerequisite into real endpoint evidence verification.

No real trained adapter was created or provided in this gate. No product
runtime, API, UI, training, export, schema, or DB behavior changed. M6-RC
remains `NOT_GO`.

## Tool

Added:

```text
scripts/verify_real_adapter_artifact.py
```

Live intake command shape:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_real_adapter_artifact.py \
  --adapter-dir <run_dir>/adapter \
  --manifest <run_dir>/manifest.json \
  --base-model microsoft/Phi-3.5-mini-instruct \
  --json-output artifacts/review/real_adapter_artifact_intake.json
```

The verifier requires:

- `adapter.safetensors` and `adapter_config.json`.
- PEFT LoRA metadata: `peft_type=LORA`, positive `r`, positive `lora_alpha`,
  non-empty `target_modules`.
- `base_model_name_or_path` matching a locked v0 base model and optional
  `--base-model`.
- Safetensors content with non-empty tensors and LoRA tensor keys.
- Adapter file size above fixture-sized placeholder bytes.
- Optional training manifest lineage: `trainer_backend`, `adapter_sha256`, and
  file rows must match the adapter directory.

## Endpoint Evidence Integration

Updated:

```text
scripts/capture_real_adapter_endpoint_evidence.py
scripts/verify_m6_rc_evidence.py
```

Live endpoint capture now requires:

```text
--adapter-intake-report <GO_REAL_ADAPTER_ARTIFACT_INTAKE json>
```

Generated endpoint evidence must include:

```yaml
adapter_intake_verified: true
self_test: false
```

`scripts/verify_m6_rc_evidence.py` now requires
`adapter_intake_verified: true` for RC GO endpoint evidence.

## Verification

Syntax check:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m py_compile scripts/verify_real_adapter_artifact.py scripts/capture_real_adapter_endpoint_evidence.py scripts/verify_m6_rc_evidence.py
```

Result: passed.

Focused tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/scripts/test_verify_real_adapter_artifact.py tests/scripts/test_capture_real_adapter_endpoint_evidence.py -q
```

Result:

```text
8 passed in 0.10s
```

Adapter intake self-test:

```text
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/verify_real_adapter_artifact.py --self-test --json-output /tmp/mib-real-adapter-intake-self-test.json
```

Result summary:

```yaml
status: GO_REAL_ADAPTER_ARTIFACT_INTAKE
base_model: microsoft/Phi-3.5-mini-instruct
peft_type: LORA
lora_key_count: 2
tensor_elements: 8192
errors: []
```

Current M6 verifier:

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
missing_required_endpoint_markers:
  - adapter_intake_verified: true
```

## Decision

```yaml
real_adapter_artifact_intake_tooling: GO
fixture_adapter_rejection_tested: true
real_like_peft_lora_acceptance_tested: true
endpoint_evidence_requires_adapter_intake: true
live_real_adapter_artifact_present: false
live_real_adapter_endpoint_evidence_present: false
m6_rc: NOT_GO
```

Next required action is to verify a real adapter artifact with
`verify_real_adapter_artifact.py`, pass that report to
`capture_real_adapter_endpoint_evidence.py`, and then rerun
`verify_m6_rc_evidence.py`.
