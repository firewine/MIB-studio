# Verified External CUDA Training Launcher

```yaml
schema_version: mib_verified_external_cuda_training_launcher.v1
date: 2026-06-22T22:03:40.444200+00:00
gate: mib-studio-verified-external-cuda-training-launcher
status: PREPARED_NOT_RUN
release_claimed_go: false
m6_rc_claimed_go: false
expected_verifier_decision: GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION
expected_transfer_manifest_status: READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
training_handoff_shell: artifacts/review/real_adapter_cuda_training_handoff.sh
```

This launcher verifies the external CUDA operator packet before running the real-adapter CUDA training handoff. It does not contain model weights, adapter files, Docker images, endpoint transcripts, copied evidence bundles, or release GO evidence.

## Guardrails

- Refuse to run when MIB_RUNTIME_ALLOW_FAKE_BACKEND is set.
- Refuse to run when repo Python, verifier script, transfer manifest script, operator packet, or CUDA training handoff shell is missing.
- Require READY_EXTERNAL_CUDA_OPERATOR_TRANSFER before invoking the CUDA training handoff.
- Do not claim M6-RC or v0 release GO from launcher execution alone.

## Command Sequence

### verify_external_cuda_operator_packet

```bash
./.venv/bin/python scripts/verify_external_cuda_operator_packet.py --packet-json artifacts/review/external_cuda_operator_packet.json --expected-decision GO --json-output artifacts/review/external_cuda_operator_packet_verification.json
```

### build_external_cuda_operator_transfer_manifest

```bash
./.venv/bin/python scripts/build_external_cuda_operator_transfer_manifest.py --packet-json artifacts/review/external_cuda_operator_packet.json --packet-verification-json artifacts/review/external_cuda_operator_packet_verification.json --json-output artifacts/review/external_cuda_operator_transfer_manifest.json --markdown-output artifacts/review/external_cuda_operator_transfer_manifest.md --expected-status READY_EXTERNAL_CUDA_OPERATOR_TRANSFER
```

### run_real_adapter_cuda_training_handoff

```bash
bash artifacts/review/real_adapter_cuda_training_handoff.sh
```
