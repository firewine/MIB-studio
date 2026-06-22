# Real Adapter Docker Image Handoff

```yaml
date: 2026-06-22T03:08:24.785575+00:00
gate: mib-studio-real-adapter-docker-image-handoff
status: PLAN_PREPARED_NOT_RUN
release_claimed_go: false
m6_rc_claimed_go: false
image: mib-export:test
context_output: /tmp/mib-real-adapter/docker_context
```

This artifact prepares the Docker image required by the downstream no-fake CUDA RC handoff. It does not build an image in the current host and does not claim release GO.

## Operator Rules

- Do not set MIB_RUNTIME_ALLOW_FAKE_BACKEND.
- If MIB_DOCKER_BASE_IMAGE_WITH_DIGEST is unset, resolve a local CUDA/PyTorch base image with scripts/resolve_cuda_base_image.py before docker build.
- MIB_DOCKER_BASE_IMAGE_WITH_DIGEST must include @sha256 before docker build.
- Do not use fixture-sized or self-test adapters as release evidence.
- Do not claim M6-RC or v0 GO until the downstream no-fake endpoint and bundle verifiers return GO.

## Command Sequence

### resolve_cuda_base_image

```bash
./.venv/bin/python scripts/resolve_cuda_base_image.py --json-output artifacts/review/real_adapter_cuda_base_image_resolution.json --env-output artifacts/review/real_adapter_cuda_base_image.env --expected-status CUDA_BASE_IMAGE_RESOLVED --candidate pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime
```

### materialize_context

```bash
./.venv/bin/python scripts/prepare_real_adapter_docker_image.py --materialize-context --adapter-root /tmp/mib-real-adapter --base-model microsoft/Phi-3.5-mini-instruct --agent-id finance.router.v1 --image mib-export:test --context-output /tmp/mib-real-adapter/docker_context --json-output artifacts/review/real_adapter_docker_image_context.json
```

### build_image

```bash
docker build --pull=false --build-arg BASE_IMAGE_WITH_DIGEST="${MIB_DOCKER_BASE_IMAGE_WITH_DIGEST}" -t mib-export:test /tmp/mib-real-adapter/docker_context
```

### inspect_image

```bash
docker image inspect mib-export:test
```
