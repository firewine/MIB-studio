# M1 Smoke Recertification Evidence

Date: 2026-06-22
Gate: `mib-studio-m1-smoke-recertification`
Decision: `GO_M1_SMOKE_CURRENT_ENVIRONMENT`

## Scope

This evidence reruns the previously failing M1 smoke verification command in
the current `.venv` environment:

```text
COREPACK_HOME=/tmp/corepack PYTHONDONTWRITEBYTECODE=1 PYTHON_BIN=./.venv/bin/python ./scripts/bootstrap_dev.sh --phase m1-smoke --skip-install
```

No product code was changed in this gate. This does not change M6-RC status.
M6-RC remains `NOT_GO` until real trained adapter endpoint evidence exists or
release policy explicitly accepts fixture-adapter evidence.

## Result

The command completed successfully:

```text
toolchain versions OK
requirements exact pins OK
json artifacts OK
fixture JSONL OK
model catalog verification errors=[]
openapi export status=ok
import boundary violations=[]
export secret scan self-test OK
PII holdout verification errors=[]
sqlite ddl extraction OK
markdown links OK
tests/smoke/test_m1_smoke.py 1 passed
```

The previous `toolchain version mismatch` failure no longer reproduces in the
current environment.

## Generated Reports

Toolchain report:

```yaml
path: artifacts/review/toolchain_report.json
strict: true
checks:
  python: true
  node: true
  pnpm: true
  rust: true
  sqlite: true
actual:
  python: 3.11.15
  node: 20.18.1
  pnpm: 9.15.0
  rust: rustc 1.83.0
  sqlite: 3.50.4
```

File-size report:

```yaml
path: artifacts/review/file_size_report.json
hard_failures: 0
soft_warnings:
  - services/shared/db/repositories/training_store.py
  - services/worker/handlers/export.py
  - services/worker/handlers/dataset_gen.py
  - services/api/app/services/dataset_service.py
  - services/api/app/services/training_service.py
```

`services/worker/handlers/export.py` is now recorded as a soft LOC warning
after recent M6 hardening work. It remains under the hard limit.

Pip audit report:

```yaml
path: artifacts/security/pip_audit_cuda.json
status: skipped
reason: pip-audit could not complete in this --verify-only/--skip-install environment
required_files:
  - requirements.txt
  - requirements-dev.txt
```

This skip is expected for the smoke command in `--skip-install` mode. Required
network-backed audit should be run without `--skip-install`.

## Decision

```yaml
m1_smoke_current_environment: GO
toolchain_mismatch_reproduced: false
toolchain_strict_checks_all_true: true
file_size_hard_failures: 0
product_code_changed: false
m6_rc: NOT_GO
```

Next required action before M6-RC GO remains unchanged:

1. Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
2. Export with matching adapter manifest/hash lineage.
3. Run `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
   without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Rerun M6-RC sign-off only after those endpoint transcripts pass.
