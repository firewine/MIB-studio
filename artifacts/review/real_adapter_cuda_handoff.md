# Real Adapter CUDA Handoff

```yaml
date: 2026-06-22T05:19:03.595846+00:00
gate: mib-studio-real-adapter-cuda-handoff
decision: WAITING_FOR_REAL_ADAPTER_INPUTS
m6_rc_claimed_go: false
release_claimed_go: false
```

M6-RC remains NOT_GO until a real trained CUDA `lora_adapter` produces no-fake Docker endpoint evidence and the M6/v0 verifiers return GO.

Executable shell artifact: `artifacts/review/real_adapter_cuda_handoff.sh`. Run it only on the CUDA host after placing the real trained adapter under the configured adapter root and setting `MIB_RUNTIME_BEARER_TOKEN`.

## Current State

```yaml
candidate_scan_decision: NO_GO_CANDIDATES_FOUND
candidate_count: 2
go_candidate_count: 0
fixture_like_candidate_count: 2
prereq_status: NOT_READY_PRECHECK_FAILED
prereq_decision: NOT_READY
missing_prereq_ids: ["adapter_safetensors_present", "adapter_config_present", "adapter_manifest_present", "docker_image_available", "host_cuda_visible"]
v0_readiness_decision: NOT_GO
v0_release_ready: false
real_adapter_evidence_bundle_decision: NOT_GO_REAL_ADAPTER_EVIDENCE_BUNDLE
real_adapter_evidence_bundle_ready: false
v0_blockers: ["real_trained_adapter_no_fake_endpoint"]
v0_unexpected_blockers: []
```

## Required Inputs

| Check | Status | Requirement |
| --- | --- | --- |
| `adapter_dir_present` | available | Real adapter directory exists, normally /tmp/mib-real-adapter/adapter |
| `adapter_safetensors_present` | missing | adapter.safetensors is present and is not fixture-sized |
| `adapter_config_present` | missing | adapter_config.json declares PEFT LORA and the locked base model |
| `adapter_manifest_present` | missing | manifest.json records adapter_sha256, files, and trainer_backend |
| `docker_image_available` | missing | Docker image tag exists for the export that packages the same adapter |
| `docker_image_adapter_matches_adapter_manifest` | pending | Docker /app/adapter hash matches manifest adapter_sha256 |
| `host_cuda_visible` | missing | nvidia-smi succeeds on the host |
| `model_cache_dir_present` | available | Strict base-model cache directory is present and mounted read-only |
| `bearer_token_ready` | available | MIB_RUNTIME_BEARER_TOKEN is at least 32 characters |
| `fake_backend_env_absent` | available | MIB_RUNTIME_ALLOW_FAKE_BACKEND is unset |

## Operator Rules

- Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.
- Do not use fixture-sized or self-test adapters as release evidence.
- The Docker image must package the same adapter hash recorded by manifest.json.
- The live endpoint capture must produce structured JSON sidecar evidence from source live_docker_capture.
- Capture endpoint evidence before updating M6 review docs to GO; the generated shell stops before M6 GO verification until those docs contain final GO markers.
- Run build_real_adapter_evidence_bundle.py to assemble the fixed evidence bundle and portable archive, then require GO_REAL_ADAPTER_EVIDENCE_BUNDLE before v0 readiness recheck.
- M6-RC and v0 remain NOT_GO until the M6 verifier, real adapter bundle verifier, and v0 readiness verifier all return GO.

## Command Sequence

### candidate_scan

```bash
./.venv/bin/python scripts/find_real_adapter_candidates.py --root /home/firewine/MIB-studio --root /tmp/mib-real-adapter --root /tmp/mib-phi-docker-export-_vgqfd4g --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --json-output artifacts/review/real_adapter_candidate_scan.json
```

### adapter_intake

```bash
./.venv/bin/python scripts/verify_real_adapter_artifact.py --adapter-dir /tmp/mib-real-adapter/adapter --base-model microsoft/Phi-3.5-mini-instruct --manifest /tmp/mib-real-adapter/manifest.json --json-output artifacts/review/real_adapter_artifact_intake.json
```

### rc_gate_preflight

```bash
MIB_RUNTIME_BEARER_TOKEN='<set-32-plus-character-token>' ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --adapter-intake-json-output artifacts/review/real_adapter_artifact_intake.json --endpoint-output artifacts/review/real_trained_adapter_endpoint_evidence.md --endpoint-json-output artifacts/review/real_trained_adapter_endpoint_evidence.json --m6-json-output artifacts/review/m6_rc_evidence_verification.json --json-output artifacts/review/m6_real_adapter_rc_gate_run.json --preflight-only
```

### rc_gate_endpoint_evidence

```bash
MIB_RUNTIME_BEARER_TOKEN='<set-32-plus-character-token>' ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --adapter-intake-json-output artifacts/review/real_adapter_artifact_intake.json --endpoint-output artifacts/review/real_trained_adapter_endpoint_evidence.md --endpoint-json-output artifacts/review/real_trained_adapter_endpoint_evidence.json --m6-json-output artifacts/review/m6_rc_evidence_verification.json --json-output artifacts/review/m6_real_adapter_rc_gate_run.json --endpoint-evidence-only
```

### m6_review_docs_go_update_required

```bash
./.venv/bin/python -c 'from pathlib import Path; import sys; signoff=Path('"'"'docs/reviews/M6/SIGNOFF_MATRIX.md'"'"').read_text(encoding='"'"'utf-8'"'"'); cto=Path('"'"'docs/reviews/M6/CTO_DECISION.md'"'"').read_text(encoding='"'"'utf-8'"'"'); ok='"'"'| M6 Export / v0 RC | GO | GO | GO | GO | GO | GO | GO | GO | GO | GO |'"'"' in signoff and '"'"'Decision: GO'"'"' in cto; sys.exit(0 if ok else 3)'
```

### rc_gate_m6_go

```bash
MIB_RUNTIME_BEARER_TOKEN='<set-32-plus-character-token>' ./.venv/bin/python scripts/run_m6_real_adapter_rc_gate.py --adapter-dir /tmp/mib-real-adapter/adapter --adapter-manifest /tmp/mib-real-adapter/manifest.json --base-model microsoft/Phi-3.5-mini-instruct --image mib-export:test --agent-id finance.router.v1 --model-cache-dir /tmp/mib-strict-model-cache-phi/model_cache --adapter-intake-json-output artifacts/review/real_adapter_artifact_intake.json --endpoint-output artifacts/review/real_trained_adapter_endpoint_evidence.md --endpoint-json-output artifacts/review/real_trained_adapter_endpoint_evidence.json --m6-json-output artifacts/review/m6_rc_evidence_verification.json --json-output artifacts/review/m6_real_adapter_rc_gate_run.json --m6-verification-only
```

### evidence_bundle_assembly

```bash
./.venv/bin/python scripts/build_real_adapter_evidence_bundle.py --source-dir artifacts/review --bundle-dir artifacts/review/real_adapter_evidence_bundle --expected-decision GO --verification-output artifacts/review/real_adapter_evidence_bundle_verification.json --manifest-output artifacts/review/real_adapter_evidence_bundle_manifest.json --archive-output artifacts/review/real_adapter_evidence_bundle.tar.gz
```

### v0_readiness_recheck

```bash
./.venv/bin/python scripts/verify_v0_release_readiness.py --expected-decision GO --json-output artifacts/review/v0_release_readiness_audit.json
```
