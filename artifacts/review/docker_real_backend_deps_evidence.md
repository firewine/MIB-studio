# Docker Real Backend Dependency Evidence

Date: 2026-06-22
Gate: `mib-studio-docker-real-backend-deps`
Decision: `GO_DEPENDENCY_PACKAGING_ONLY`

## Scope

This gate remediates the exported Docker runtime dependency blocker recorded in
`artifacts/review/real_adapter_inference_evidence.md`.

It does not claim real trained adapter inference, because no real trained CUDA
`lora_adapter` artifact is available in the current repo or temp artifacts.
M6-RC remains `NOT_GO` until a real adapter is provided and no-fake-backend
endpoint transcripts pass.

## Change

`packages/agent-runtime/templates/zip_runtime/requirements-runtime.txt` now
packages the CUDA LoRA inference backend dependencies used by
`packages/agent-runtime/loaders/transformers_lora.py`:

```text
--extra-index-url https://download.pytorch.org/whl/cu121
torch==2.4.1+cu121
transformers==5.6.0
accelerate==1.11.0
peft==0.18.0
bitsandbytes==0.49.2
sentencepiece==0.2.1
safetensors==0.4.5
protobuf==5.29.6
```

The Docker export path copies that same runtime requirements file into the
Docker context, and `packages/agent-runtime/templates/docker/Dockerfile.cuda`
installs it with:

```text
python -m pip install --no-cache-dir -r requirements-runtime.txt
```

## Tests

Focused Docker export packaging test:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
```

Result:

```text
2 passed, 3 warnings in 31.47s
```

Zip/export runtime regression tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_export_manifest.py tests/export/test_exported_runtime_smoke.py -q
```

Result:

```text
5 passed, 6 warnings in 61.83s
```

The focused Docker export test now asserts:

- `requirements-runtime.txt` is included in the Docker context tar.
- CUDA LoRA inference backend packages are present in that file.
- The runtime package pins match the root `requirements.txt` CUDA dependency
  line for the required subset.

## Temporary Docker Build Probe

An isolated temp context was built from the current Dockerfile and runtime
requirements:

```text
docker build --pull=false \
  --build-arg BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1 \
  -t mib-runtime-deps-probe:fee0795 \
  /tmp/mib-docker-real-backend-deps/context
```

Build result:

```text
Successfully installed ... torch-2.4.1+cu121 transformers-5.6.0 peft-0.18.0 bitsandbytes-0.49.2 safetensors-0.4.5 accelerate-1.11.0 ...
```

Image id:

```text
sha256:b3561aceed6c7291521986d353fa4533573d7ce44a77d96fde626bdafcdbb415
```

Image size:

```text
3302838865 bytes
```

Import probe:

```text
docker run --rm mib-runtime-deps-probe:fee0795 python -c "<import torch/transformers/peft/safetensors/accelerate/bitsandbytes>"
```

Output:

```json
{"accelerate":"1.11.0","bitsandbytes":"0.49.2","peft":"0.18.0","safetensors":"0.4.5","torch":"2.4.1+cu121","transformers":"5.6.0"}
```

Warning observed during `bitsandbytes` import:

```text
Failed to load CPU gemm_4bit_forward from kernels-community: No module named 'kernels'.
```

This warning did not make the import probe fail. It should be revisited if CPU
fallback inference becomes an acceptance target. Current v0 CUDA inference
remains GPU-oriented.

The temp image was removed after evidence collection:

```text
docker rmi mib-runtime-deps-probe:fee0795
```

## Decision

```yaml
exported_runtime_real_backend_dependency_packaging: GO
new_docker_context_includes_backend_deps: true
temp_image_backend_import_probe: pass
bitsandbytes_cpu_kernel_warning_observed: true
real_trained_adapter_inference: NOT_PROVEN
m6_rc: NOT_GO
```

Next required action before M6-RC GO:

1. Provide or train a real CUDA `lora_adapter` for a locked v0 base model.
2. Export a new Docker image with the updated runtime requirements.
3. Run `/healthz`, `/agents/{agent_id}/run`, and `/v1/chat/completions`
   without `MIB_RUNTIME_ALLOW_FAKE_BACKEND`.
4. Rerun M6-RC sign-off only after those endpoint transcripts pass.
