# External CUDA Operator Packet

```yaml
schema_version: mib_external_cuda_operator_packet.v1
date: 2026-06-22T22:09:15.969420+00:00
gate: mib-studio-external-cuda-operator-packet
status: PREPARED_NOT_RUN
release_claimed_go: false
m6_rc_claimed_go: false
git_head: cbd6074
primary_external_handoff: artifacts/review/verified_external_cuda_training_launcher.sh
downstream_training_handoff: artifacts/review/real_adapter_cuda_training_handoff.sh
```

## Required Committed Files

- `artifacts/review/verified_external_cuda_training_launcher.sh` (verified_training_launcher): `01a0c441724b5252c35bb9ff3033e44919c0535f4ee7439aaf6053726dc5fa48`
- `artifacts/review/real_adapter_cuda_training_handoff.json` (training_handoff_json): `7aa526075b226f67a4b9d41bb412a9f2bc3a28b95339d2dcaba207a1ba8584f5`
- `artifacts/review/real_adapter_cuda_training_handoff.md` (training_handoff_markdown): `da9abc50ba0100a2cf5b1e3f30d9c87ec7894bb93a77f1d29f6f266b2b251bc3`
- `artifacts/review/real_adapter_cuda_training_handoff.sh` (training_handoff_shell): `dade49ab2aa5718cdd9b07fa05196927130546fef943a9390ff99927d284e697`
- `artifacts/review/real_adapter_cuda_handoff.json` (rc_handoff_json): `91ce09c4145e01b83a2f37a05278e12d077a2f50c9274b5fd48f9106ba1bd685`
- `artifacts/review/real_adapter_cuda_handoff.md` (rc_handoff_markdown): `5e9b41b21d0828139ef50c87742d8c49b425a7bdce6e5209c8836a10b6bbd917`
- `artifacts/review/real_adapter_cuda_handoff.sh` (rc_handoff_shell): `4f480e310d70fc036e2e17f420bea22c51cf19261c74a6839100f37a43e53c9c`
- `artifacts/review/v0_release_blocker_recertification.json` (recertification_summary): `822457ce7417f774d10a8c235d07d19890da665b7002e3fb5518bc12748a5ae5`
- `examples/fixtures/router_20.jsonl` (router_training_dataset): `3be5cdfe2f6b655eed0e9c11c8ec23b5778bf61798b4c8fb152be67a9953bd90`
- `scripts/prepare_strict_model_cache.py` (strict_model_cache_preparation): `327352a72b263b1f06665d84e55d25bdd4f963fdc504b5c8c8854b1ff35d8452`
- `scripts/build_external_cuda_operator_transfer_manifest.py` (operator_transfer_manifest_builder): `b818829dbe047d4d6ad4990df40783353a3c24acdb1c50cecddd1ad605365230`
- `scripts/prepare_cuda_lora_training_run.py` (training_handoff_generator): `8681af37c4a0cc0c16d5f47db30bb5fe236c44f96320fc9da54ac8341f49b323`
- `scripts/check_cuda_lora_training_prereqs.py` (cuda_training_preflight): `ac5b0df5eb6efbb860e5a516c257596a0e7e8a9ae31ae41c9285a3c128d2137e`
- `scripts/resolve_cuda_base_image.py` (cuda_base_image_resolver): `0c8d641aa46a6f94441ec9ca2b3c0f61cf72b94b6be9cd3dcf8ca6e00ae8a685`
- `scripts/prepare_real_adapter_docker_image.py` (docker_image_handoff_generator): `0c9e92b0a3bfcd711a4a85ec26fd3a3393fbd74387e59ac7169cb9ea8609c69f`
- `scripts/run_m6_real_adapter_rc_gate.py` (real_adapter_rc_gate): `1f681bef22e7b08556b0ec7bc4438bf60e1b786d2d7e7dd3c89a5f165c87f5c3`
- `scripts/build_real_adapter_evidence_bundle.py` (evidence_bundle_builder): `d0c8ad106e1463b46a0e987b27f8c78d8557d6c65e96a3f14901f995a3249c74`
- `scripts/run_v0_release_closeout_from_bundle.py` (bundle_closeout): `e5bbdebd9c314db8b047dec4af635720102a2d15dbbdf04bf17777b1cd453e27`

## Package Readiness Checks

- `dataset_jsonl_present`: `examples/fixtures/router_20.jsonl`
- `python_executable_present`: `./.venv/bin/python`
- `llamafactory_cli_present`: `./.venv/bin/llamafactory-cli`
- `model_cache_dir_present`: `/tmp/mib-strict-model-cache-phi/model_cache`
- `backend_config_present`: `/tmp/mib-real-adapter/backend_config.yaml`
- `rc_handoff_shell_present`: `artifacts/review/real_adapter_cuda_handoff.sh`

## Operator Sequence

1. Keep this packet file from the current checkout; packet.git.head is the required committed file source commit cbd6074 for verifier blob checks.
2. Run artifacts/review/verified_external_cuda_training_launcher.sh on the external CUDA host so packet verification runs before artifacts/review/real_adapter_cuda_training_handoff.sh.
3. Allow the verified launcher to invoke artifacts/review/real_adapter_cuda_training_handoff.sh only after GO_EXTERNAL_CUDA_OPERATOR_PACKET_VERIFICATION.
4. Run the downstream no-fake endpoint/M6/evidence-bundle commands emitted by artifacts/review/real_adapter_cuda_handoff.sh.
5. Transfer the metadata-bearing artifacts/review/real_adapter_evidence_bundle.tar.gz back to the release workstation.
6. Run scripts/run_v0_release_closeout_from_bundle.py only after accepted M6 GO review docs are present in the same checkout.

## Expected Return Artifacts

- `artifacts/review/real_adapter_evidence_bundle.tar.gz`
- `artifacts/review/real_adapter_evidence_bundle_manifest.json`
- `artifacts/review/real_adapter_evidence_bundle_verification.json`
- `accepted GO updates to docs/reviews/M6/SIGNOFF_MATRIX.md`
- `accepted GO updates to docs/reviews/M6/CTO_DECISION.md`

## Forbidden Committed Artifacts

- model weights
- LoRA adapter files or /tmp/mib-real-adapter contents
- Docker image layers or archives
- raw live endpoint transcripts
- copied external real-adapter evidence bundles
