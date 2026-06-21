# Real Docker Runtime Evidence

Date: 2026-06-22
Gate: `mib-studio-real-docker-runtime-evidence`
Decision: `NOT_GO`

## Scope

This evidence run attempted the v0 RC requirement for a CUDA `lora_adapter`
Docker export using the existing M6 implementation. It did not change product
code or release sign-off status.

## Inputs

- Base image: `getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1`
- Export image produced: `mib-export-fa97e7ed5a0244a09c66b270939bcd54:latest`
- Export image digest: `sha256:814a39aa442bb67bf3f2e96b4ee50d581a11fef0823920fb920f4095683b47bb`
- Docker image manifest digest: `sha256:f2ae7e53b07f1c235a428e304dd9724972f6b5365fae7c084e2e030c6090cc5f`
- Agent id: `eval_runner_project.v1`
- Agent package id: `7cb7e97d88f340dba44dbc53f8265fed`
- Export id: `fa97e7ed5a0244a09c66b270939bcd54`

## Build And Save Result

Command:

```text
MIB_DOCKER_EXPORT_REAL_BUILD=1
MIB_DOCKER_BASE_IMAGE_WITH_DIGEST=getbeta-backend@sha256:95792b6d22c23bd9b95e91b1e53365ebaa31b12847a242fdac63e8f4434034f1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python -m pytest tests/export/test_docker_export_security.py -q
```

Observed result:

- Docker build/save completed and produced a saved image tar.
- The existing pytest assertion failed because it still inspects the artifact as
  a Docker build-context tar. In real-build mode the artifact is a Docker image
  tar, whose top-level entries are OCI/Docker image metadata and layer blobs.
- Saved image tar path:
  `/tmp/pytest-of-firewine/pytest-181/test_docker_export_worker_writ0/.mib-home/projects/035cef27b0b246bda36bdd2b1f2f54fb/exports/fa97e7ed5a0244a09c66b270939bcd54/eval_runner_project_v1-docker-context.tar`
- Saved image tar sha256:
  `29f44c72abfe03671b81a2cdc3da4c04b10a8df0b6d71365c07d87defb27fb5a`
- Saved image tar size: `287M`

## SBOM And CVE Evidence

- `evidence/cve_report.json` recorded `real_build: true`, artifact sha256
  `29f44c72abfe03671b81a2cdc3da4c04b10a8df0b6d71365c07d87defb27fb5a`, and
  `findings: []`.
- `evidence/sbom.cdx.json` was written with CycloneDX file components for the
  build context.

## Secret Scan Result

Command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./.venv/bin/python scripts/scan_export_artifact.py --artifact <saved-image-tar> --sbom <sbom> --cve-report <cve> --require-docker-evidence
```

Observed result:

```text
AttributeError: 'list' object has no attribute 'get'
```

Root cause:

- `scan_export_artifact.py` expects `manifest.json` inside the tar to be the MIB
  export manifest object.
- A saved Docker image tar contains Docker/OCI `manifest.json` as a list.
- Therefore image-tar secret scan is not currently supported by the scanner even
  though context-level SBOM/CVE files were created.

## Container Run Result

Command shape:

```text
docker run -d --name mib-docker-evidence-fa97 \
  -p 127.0.0.1:18080:8000 \
  -v /tmp/mib-docker-evidence/model_cache:/models:ro \
  -e MIB_MODEL_CACHE_DIR=/models \
  -e MIB_RUNTIME_ALLOW_FAKE_BACKEND=1 \
  -e MIB_RUNTIME_BEARER_TOKEN=<redacted-32-char-test-token> \
  mib-export-fa97e7ed5a0244a09c66b270939bcd54:latest
```

Observed result:

- Container id: `3e1000a2d8b6d65a31c0eb14ca6a4ffe213abc6b76a16e1e817e043373904a96`
- Status: `Exited (1)`
- Read-only model mount was present: `/tmp/mib-docker-evidence/model_cache:/models:ro`
- The container exited before binding port `8000`, so HTTP transcripts for
  `/agents/{agent_id}/run` and `/v1/chat/completions` could not be collected.

Container log excerpt:

```text
ModuleNotFoundError: No module named 'agents'
```

Root cause:

- `Dockerfile.cuda` copies the export tree to `/app`.
- The runtime package lives under `/app/runtime/agents`.
- The Docker command runs `python -m uvicorn agents.run:app` from `/app` without
  adding `/app/runtime` to `PYTHONPATH` or changing `WORKDIR` to `/app/runtime`.

## Model Cache Status

The exported manifest requires the strict external cache subdir:

```text
google__gemma-2b-it@96988410cbdaeb8d5093d1ebdc5a8fb563e02bad
```

Required weight files include:

- `model-00001-of-00002.safetensors`, size `4945242264`
- `model-00002-of-00002.safetensors`, size `67121608`

Searches under `/home/firewine` and the repo did not find this cache. After the
Docker import-path bug is fixed, endpoint smoke will still require a real strict
model cache before `/healthz`, `/agents/{agent_id}/run`, and
`/v1/chat/completions` can return success.

## Blocking Issues Found

- P1: Docker runtime image exits at startup because `agents.run:app` is not
  importable from the Docker image default working directory/import path.
- P1: `scripts/scan_export_artifact.py` cannot scan a saved Docker image tar
  because Docker image tar `manifest.json` is a list, not the MIB export
  manifest object.
- P1: The local machine does not currently contain the strict external Gemma
  model cache required for success endpoint smoke.

## Next Required Gate

Open a scoped implementation gate for Docker runtime evidence remediation:

- Fix Dockerfile runtime import path.
- Add/adjust tests so real-build mode validates image tar structure separately
  from context tar structure.
- Extend export artifact scanning or add an image-tar scanner path.
- Provide or download the strict model cache, then rerun container endpoint
  smoke with read-only `MIB_MODEL_CACHE_DIR`.
